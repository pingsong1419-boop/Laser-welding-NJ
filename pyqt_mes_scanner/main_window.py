# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QStackedWidget, QFrame, QSizePolicy,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QListWidget, QListWidgetItem, QComboBox, QFormLayout,
    QInputDialog
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QFont

from styles import MAIN_STYLE
from tabs.route_table_tab import RouteTableTab
from tabs.material_scanner_tab import MaterialScannerTab
from tabs.module_generate_tab import ModuleGenerateTab
from tabs.full_material_tab import FullMaterialTab
from services.mes_service import MesService
from tabs.module_packing_tab import ModulePackingTab
from tabs.api_detail_tab import ApiDetailTab
from tabs.log_tab import LogTab
from tabs.plc_monitor_tab import PlcMonitorTab
from tabs.plasma_cleaning_tab import PlasmaCleaningTab
from tabs.api_worker import WorkerThread
from dialogs.config_dialog import ConfigDialog
from dialogs.login_dialog import LoginDialog
from services.s7_service import S7Service



class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(35)
        self.setObjectName("custom_title_bar")
        self.setStyleSheet("""
            QWidget#custom_title_bar {
                background-color: #0d1b2a;
                border-bottom: 1px solid rgba(100, 181, 246, 0.1);
            }
            QLabel {
                color: #90caf9;
                font-size: 14px;
                font-weight: bold;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)

        # 软件图标和标题
        self.icon_label = QLabel()
        self.icon_label.setText("⚡")
        self.icon_label.setStyleSheet("font-size: 16px; margin-right: 5px; color: #42a5f5;")
        layout.addWidget(self.icon_label)

        self.title_label = QLabel("MES 工序执行系统")
        layout.addWidget(self.title_label)

        layout.addStretch()

        # 最小化、最大化、关闭
        btn_style = """
            QPushButton {
                background: transparent;
                color: #8a9ba8;
                border: none;
                font-size: 16px;
                font-weight: bold;
                width: 45px;
                height: 35px;
            }
            QPushButton:hover {
                background-color: #1a2a3a;
                color: #e3f2fd;
            }
        """

        self.min_btn = QPushButton("—")
        self.min_btn.setStyleSheet(btn_style)
        self.min_btn.setCursor(Qt.PointingHandCursor)
        self.min_btn.clicked.connect(self._minimize_window)
        layout.addWidget(self.min_btn)

        self.max_btn = QPushButton("⬜")
        self.max_btn.setStyleSheet(btn_style)
        self.max_btn.setCursor(Qt.PointingHandCursor)
        self.max_btn.clicked.connect(self._toggle_maximize)
        layout.addWidget(self.max_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8a9ba8;
                border: none;
                font-size: 16px;
                font-weight: bold;
                width: 45px;
                height: 35px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
                color: white;
            }
        """)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self._close_window)
        layout.addWidget(self.close_btn)

        self._dragging = False
        self._drag_position = None

    def _minimize_window(self):
        if self.parent:
            self.parent.showMinimized()

    def _toggle_maximize(self):
        if self.parent:
            if self.parent.isMaximized():
                self.parent.showNormal()
                self.max_btn.setText("⬜")
            else:
                self.parent.showMaximized()
                self.max_btn.setText("❐")

    def _close_window(self):
        if self.parent:
            self.parent.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            if self.parent:
                self._drag_position = event.globalPos() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and self._drag_position:
            if self.parent:
                self.parent.move(event.globalPos() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        event.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MES 工序执行系统")
        self.setMinimumSize(1400, 900)
        self.resize(1500, 950)

        # 配置
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        self.config = self._load_config()

        # 状态
        self.product_code = ""
        self.order_info = None
        self.route_steps = []
        self.test_result = "IDLE"
        self.result_message = ""
        self.api_records = []
        self.material_verification_success = False
        self.verified_materials = []
        self._generated_records = []
        self._pending_bind_upload_data = None  # 绑定数据暂存，等入箱完成后一起上传
        self.process_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.current_flow_step = 0
        self.current_mode = "binding"  # 'binding' | 'packing' | 'plasma'
        self._s7_last_allow = 0  # 上一次允许请求信号值（用于边缘检测）
        self._s7_last_pack_request = False  # 上一次箱体码请求信号值（用于Bool边缘检测）
        self._s7_reconnect_fail_count = 0  # 连续重连失败计数

        # S7 服务（在 _setup_ui 之前初始化，因为 UI 中可能引用）
        self.s7_service = S7Service()
        self.s7_timer = QTimer(self)
        self.s7_timer.timeout.connect(self._poll_s7_start_signal)
        self.s7_reconnect_timer = QTimer(self)
        self.s7_reconnect_timer.timeout.connect(self._try_s7_reconnect)

        # UI 状态刷新定时器（刷新 Topbar 的 PLC 连接状态）
        self.ui_status_timer = QTimer(self)
        self.ui_status_timer.timeout.connect(self._sync_top_plc_status)
        self.ui_status_timer.start(1000)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint | Qt.WindowMinimizeButtonHint)
        self._setup_ui()
        self.setStyleSheet(MAIN_STYLE)

        self._init_s7_service()

    def _sync_top_plc_status(self):
        """实时同步顶栏的 PLC 连接状态"""
        try:
            s7_cfg = self.config.get("s7Config", {})
            enabled = s7_cfg.get("enabled", False)
            ip = s7_cfg.get("ip", "192.168.1.10")
            
            if not enabled:
                self.plc_top_dot.setStyleSheet("color: #78909c; font-size: 16px;")
                self.plc_top_txt.setText("PLC 禁用")
                self.plc_top_txt.setStyleSheet("color: #78909c; font-size: 14px; font-weight: 600;")
            elif getattr(self.s7_service, "connected", False):
                self.plc_top_dot.setStyleSheet("color: #00e676; font-size: 16px;")
                self.plc_top_txt.setText(f"PLC 已连接 ({ip})")
                self.plc_top_txt.setStyleSheet("color: #00e676; font-size: 14px; font-weight: 600;")
            else:
                self.plc_top_dot.setStyleSheet("color: #ff5252; font-size: 16px;")
                self.plc_top_txt.setText(f"PLC 断开 ({ip})")
                self.plc_top_txt.setStyleSheet("color: #ef9a9a; font-size: 14px; font-weight: 600;")
        except Exception:
            pass

    # =====================================================================
    #  S7 通讯
    # =====================================================================
    def _init_s7_service(self):
        """根据配置初始化 S7 连接和轮询"""
        s7_cfg = self.config.get("s7Config", {})
        if not s7_cfg.get("enabled", False):
            if self.s7_timer.isActive():
                self.s7_timer.stop()
            if self.s7_reconnect_timer.isActive():
                self.s7_reconnect_timer.stop()
            self.s7_service.disconnect()
            self._add_log("info", "[S7] 通讯已禁用")
            return
        ip = s7_cfg.get("ip", "192.168.1.10")
        rack = int(s7_cfg.get("rack", 0))
        slot = int(s7_cfg.get("slot", 1))
        ok, msg = self.s7_service.connect(ip, rack, slot)
        if ok:
            self._s7_reconnect_fail_count = 0
            if self.s7_reconnect_timer.isActive():
                self.s7_reconnect_timer.stop()
            poll_ms = int(s7_cfg.get("pollIntervalMs", 500))
            self.s7_timer.start(poll_ms)
            self._add_log("info", f"[S7] 已连接 PLC {ip}, 轮询间隔 {poll_ms}ms")
        else:
            self._add_log("error", f"[S7] 连接失败: {msg}, 将自动重连")
            self._start_s7_reconnect_timer()

    def _start_s7_reconnect_timer(self):
        """启动自动重连定时器（固定 5 秒间隔）"""
        if not self.s7_reconnect_timer.isActive():
            self.s7_reconnect_timer.start(5000)

    def _try_s7_reconnect(self):
        """尝试重新连接 PLC"""
        s7_cfg = self.config.get("s7Config", {})
        if not s7_cfg.get("enabled", False):
            if self.s7_reconnect_timer.isActive():
                self.s7_reconnect_timer.stop()
            return
        ip = s7_cfg.get("ip", "192.168.1.10")
        rack = int(s7_cfg.get("rack", 0))
        slot = int(s7_cfg.get("slot", 1))
        try:
            ok, msg = self.s7_service.connect(ip, rack, slot)
            if ok:
                self._s7_reconnect_fail_count = 0
                self.s7_reconnect_timer.stop()
                poll_ms = int(s7_cfg.get("pollIntervalMs", 500))
                self.s7_timer.start(poll_ms)
                self._add_log("info", f"[S7] 自动重连成功: PLC {ip}")
            else:
                self._s7_reconnect_fail_count += 1
                # 每失败 6 次（约 30 秒）才记录一次日志，避免刷屏
                if self._s7_reconnect_fail_count % 6 == 1:
                    self._add_log("error", f"[S7] 自动重连失败 ({self._s7_reconnect_fail_count}次): {msg}")
        except Exception as e:
            self._s7_reconnect_fail_count += 1
            if self._s7_reconnect_fail_count % 6 == 1:
                self._add_log("error", f"[S7] 自动重连异常 ({self._s7_reconnect_fail_count}次): {e}")

    @staticmethod
    def _parse_trigger_value(val_str, data_type):
        """将配置中的字符串值转换为对应 PLC 类型"""
        data_type = data_type.lower()
        if data_type == "bool":
            return val_str.strip().lower() in ("true", "1", "yes", "on")
        elif data_type in ("sint", "int", "dint"):
            return int(val_str)
        elif data_type == "real":
            return float(val_str)
        else:
            return str(val_str)

    def _reset_s7_signal(self, db, offset, data_type, value, bit):
        try:
            self.s7_service.write_value(db, offset, data_type, value, bit=bit, str_len=254)
            self._add_log("info", f"[S7] 焊接完成信号已延迟 500ms 复位为 {value} (DB{db}.{offset})")
        except Exception as e:
            self._add_log("error", f"[S7] 延迟复位焊接完成信号失败: {e}")

    def _poll_s7_start_signal(self):
        """轮询 PLC 允许请求信号，根据当前模式读取模块码或箱体码"""
        if not self.s7_service.connected:
            self._start_s7_reconnect_timer()
            return

        s7_cfg = self.config.get("s7Config", {})
        sig = s7_cfg.get("startSignal", {})
        mod = s7_cfg.get("moduleCodeSignal", {})
        box = s7_cfg.get("packBoxSignal", {})

        sig_db = int(sig.get("db", 1))
        sig_offset = int(sig.get("offset", 6))
        sig_type = sig.get("type", "Int")
        sig_bit = int(sig.get("bit", 0))
        trigger_value = sig.get("triggerValue", "1")
        reset_value = sig.get("resetValue", "0")

        try:
            trigger_val = self._parse_trigger_value(trigger_value, sig_type)
            reset_val = self._parse_trigger_value(reset_value, sig_type)
        except Exception as e:
            self._add_log("error", f"[S7] 触发值/复位值格式错误 ({sig_type}): {e}")
            return

        try:
            allow = self.s7_service.read_value(sig_db, sig_offset, sig_type, bit=sig_bit, str_len=254)
            allow_str = str(allow) if allow is not None else ""
            trigger_str = str(trigger_val)

            # ================================================================
            # 统一 PLC 触发事件处理 (startSignal)
            # ================================================================
            last_str = str(self._s7_last_allow)
            if last_str != trigger_str and allow_str == trigger_str:
                self._add_log("info", f"[S7] 检测到焊接完成信号 DB{sig_db}.{sig_offset} = {allow}")

                if self.current_mode == "packing":
                    # 入箱模式：兼容原有启动信号读取箱体码（备用）
                    box_db = int(box.get("db", 3))
                    box_offset = int(box.get("offset", 200))
                    box_type = box.get("type", "String")
                    box_bit = int(box.get("bit", 0))
                    box_str_len = int(box.get("strLen", 24))

                    box_code = self.s7_service.read_value(box_db, box_offset, box_type, bit=box_bit, str_len=box_str_len)
                    if box_code is None:
                        self._add_log("error", f"[S7] 读取箱体码失败 DB{box_db}.{box_offset}")
                        self._s7_last_allow = allow
                        return

                    box_code = str(box_code).strip()
                    if not box_code:
                        self._add_log("warning", "[S7] 读取到空箱体码，跳过流程")
                        self._s7_last_allow = allow
                        return

                    self._add_log("info", f"[S7] 读取箱体码: {box_code}")

                    # 延迟 500ms 复位启动信号
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(500, lambda: self._reset_s7_signal(sig_db, sig_offset, sig_type, reset_val, sig_bit))
                    allow = reset_val

                    # 仅在文本框触发入箱流程回填
                    self.packing_tab.set_pack_code(box_code)
                else:
                    # 绑定模式（默认）：读取国标码
                    mod_db = int(mod.get("db", 2))
                    mod_offset = int(mod.get("offset", 112))
                    mod_type = mod.get("type", "String")
                    mod_bit = int(mod.get("bit", 0))
                    mod_str_len = int(mod.get("strLen", 24))

                    module_code = self.s7_service.read_value(mod_db, mod_offset, mod_type, bit=mod_bit, str_len=mod_str_len)
                    if module_code is None:
                        self._add_log("error", f"[S7] 读取国标码失败 DB{mod_db}.{mod_offset}")
                        self._s7_last_allow = allow
                        return

                    module_code = str(module_code).strip()
                    if not module_code:
                        self._add_log("warning", "[S7] 读取到空国标码，跳过流程")
                        self._s7_last_allow = allow
                        return

                    self._add_log("info", f"[S7] 读取国标码: {module_code}")

                    # 延迟 500ms 复位启动信号
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(500, lambda: self._reset_s7_signal(sig_db, sig_offset, sig_type, reset_val, sig_bit))
                    allow = reset_val

                    # 直接回填文本框，不强制切屏
                    self.scan_input.setText(module_code)
                    from PyQt5.QtWidgets import QApplication
                    QApplication.processEvents()

                    # 延迟 1S 去进行非首工序获取工单交互
                    QTimer.singleShot(1000, self._handle_scan)

            self._s7_last_allow = allow
        except Exception as e:
            self._add_log("error", f"[S7] PLC 信号处理异常: {e}")

    # =====================================================================
    #  UI 组装
    # =====================================================================
    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("app_root")
        central.setStyleSheet("background: #0a0e1a;")
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ========== 自定义标题栏 ==========
        self.title_bar = CustomTitleBar(self)
        root_layout.addWidget(self.title_bar)

        # ========== Header ==========
        header = QWidget()
        header.setObjectName("app_header")
        header.setFixedHeight(52)
        header.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0d1b2a, stop:1 #112240);
                border-bottom: 1px solid rgba(100,181,246,0.2);
            }
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)
        h_layout.setSpacing(16)

        # Brand
        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand_icon = QLabel("MES")
        brand_icon.setObjectName("brand_icon")
        brand_icon.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1565c0, stop:1 #0d47a1);
            border-radius: 8px; color: #e3f2fd; font-size: 13px; font-weight: 800;
            min-width: 34px; max-width: 34px; min-height: 34px; max-height: 34px;
            qproperty-alignment: AlignCenter;
        """)
        brand.addWidget(brand_icon)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        bt = QLabel("MES 工序执行系统")
        bt.setObjectName("brand_title")
        bt.setStyleSheet("color: #e3f2fd; font-size: 17px; font-weight: 700;")
        bs = QLabel("MES Process Execution System v1.0")
        bs.setObjectName("brand_sub")
        bs.setStyleSheet("color: #546e7a; font-size: 12px;")
        brand_text.addWidget(bt)
        brand_text.addWidget(bs)
        brand.addLayout(brand_text)
        h_layout.addLayout(brand)

        h_layout.addStretch()
        self.process_badge = QLabel(f"当前工序：{self.config['moduleBindProcessCode']}")
        self.process_badge.setObjectName("process_badge")
        self.process_badge.setStyleSheet("""
            background: rgba(21,101,192,0.2);
            border: 1px solid rgba(100,181,246,0.2);
            border-radius: 16px;
            padding: 4px 16px;
            color: #42a5f5;
            font-weight: 600;
            font-size: 14px;
        """)
        h_layout.addWidget(self.process_badge)

        # 实时 PLC 状态组件
        self.plc_top_frame = QFrame()
        self.plc_top_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        pt_layout = QHBoxLayout(self.plc_top_frame)
        pt_layout.setContentsMargins(10, 0, 10, 0)
        pt_layout.setSpacing(6)

        self.plc_top_dot = QLabel("●")
        self.plc_top_dot.setStyleSheet("color: #ff5252; font-size: 16px;")
        self.plc_top_txt = QLabel("PLC 离线")
        self.plc_top_txt.setStyleSheet("color: #ef9a9a; font-size: 14px; font-weight: 600;")
        pt_layout.addWidget(self.plc_top_dot)
        pt_layout.addWidget(self.plc_top_txt)

        h_layout.addWidget(self.plc_top_frame)
        h_layout.addStretch()

        config_btn = QPushButton("⚙️ 配置")
        config_btn.setObjectName("icon_btn")
        config_btn.setCursor(Qt.PointingHandCursor)
        config_btn.clicked.connect(self._open_config)
        h_layout.addWidget(config_btn)

        root_layout.addWidget(header)

        # ========== Main ==========
        main = QHBoxLayout()
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(12)

        # ---- 左侧固定面板（导航 + 内容栈）----
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)
        left_widget = QWidget()
        left_widget.setFixedWidth(360)
        left_widget.setLayout(left_panel)
        left_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # 导航卡片
        nav_card = self._create_nav_card()
        left_panel.addWidget(nav_card)

        # 左侧内容栈
        self.left_stack = QStackedWidget()
        self.left_stack.addWidget(self._create_binding_left())   # page 0
        self.left_stack.addWidget(self._create_plasma_left())    # page 1
        self.left_stack.addWidget(self._create_packing_left())   # page 2
        self.left_stack.addWidget(self._create_plc_monitor_left()) # page 3
        left_panel.addWidget(self.left_stack, stretch=1)

        main.addWidget(left_widget)

        # 共享记录组件
        self.api_tab = ApiDetailTab()
        self.log_tab = LogTab()

        # ---- 右侧内容栈 ----
        self.right_stack = QStackedWidget()
        self.right_stack.addWidget(self._create_binding_right())  # page 0
        self.plasma_tab = PlasmaCleaningTab(self.s7_service, self.config)
        self.plasma_tab.log.connect(self._add_log)
        self.plasma_tab.config_changed.connect(self._save_config)
        self.right_stack.addWidget(self.plasma_tab)  # page 1
        self.packing_tab = ModulePackingTab(parent=self)
        self.packing_tab.log.connect(self._add_log)
        self.packing_tab.api_record.connect(self._add_api_record_dict)
        self.packing_tab.completed.connect(self._on_packing_completed)
        self.packing_tab.upload_ready.connect(self._on_packing_upload_ready)
        self.packing_tab.set_config(self.config)
        self.right_stack.addWidget(self.packing_tab)  # page 2
        
        self.plc_monitor_tab = PlcMonitorTab(self.s7_service, self.config)
        self.plc_monitor_tab.log.connect(self._add_log)
        self.right_stack.addWidget(self.plc_monitor_tab) # page 3
        main.addWidget(self.right_stack, stretch=1)

        root_layout.addLayout(main, stretch=1)

        # 默认显示模块码绑定
        self._switch_mode("binding")
        self._refresh_recipe_combo()

    # =====================================================================
    #  导航栏
    # =====================================================================
    def _create_nav_card(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        tl = QLabel("📂 工序导航")
        tl.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9; letter-spacing: 0.5px;")
        layout.addWidget(tl)

        self.nav_binding_btn = QPushButton("🔗 模块码绑定")
        self.nav_binding_btn.setCursor(Qt.PointingHandCursor)
        self.nav_binding_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1565c0, stop:1 #0d47a1);
                border: none; border-radius: 8px; color: #e3f2fd;
                min-height: 48px; padding: 6px 14px; 
                font-size: 15px; font-weight: 700;
                font-family: "Microsoft YaHei", "微软雅黑";
                text-align: left;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976d2, stop:1 #1565c0); }
        """)
        self.nav_binding_btn.clicked.connect(lambda: self._switch_mode("binding"))
        layout.addWidget(self.nav_binding_btn)

        self.nav_plasma_btn = QPushButton("🔬 激光数据采集")
        self.nav_plasma_btn.setCursor(Qt.PointingHandCursor)
        self.nav_plasma_btn.setStyleSheet("""
            QPushButton {
                background: rgba(100,181,246,0.08);
                border: 1px solid rgba(100,181,246,0.2);
                border-radius: 8px; color: #90caf9;
                min-height: 48px; padding: 6px 14px; 
                font-size: 15px; font-weight: 700;
                font-family: "Microsoft YaHei", "微软雅黑";
                text-align: left;
            }
            QPushButton:hover { background: rgba(100,181,246,0.15); border-color: #42a5f5; color: #e3f2fd; }
        """)
        self.nav_plasma_btn.clicked.connect(lambda: self._switch_mode("plasma"))
        layout.addWidget(self.nav_plasma_btn)

        self.nav_packing_btn = QPushButton("📦 模组入箱工序")
        self.nav_packing_btn.setCursor(Qt.PointingHandCursor)
        self.nav_packing_btn.setStyleSheet("""
            QPushButton {
                background: rgba(100,181,246,0.08);
                border: 1px solid rgba(100,181,246,0.2);
                border-radius: 8px; color: #90caf9;
                min-height: 48px; padding: 6px 14px; 
                font-size: 15px; font-weight: 700;
                font-family: "Microsoft YaHei", "微软雅黑";
                text-align: left;
            }
            QPushButton:hover { background: rgba(100,181,246,0.15); border-color: #42a5f5; color: #e3f2fd; }
        """)
        self.nav_packing_btn.clicked.connect(lambda: self._switch_mode("packing"))
        layout.addWidget(self.nav_packing_btn)


        
        self.nav_plc_btn = QPushButton("📺 PLC 读写监控")
        self.nav_plc_btn.setCursor(Qt.PointingHandCursor)
        self.nav_plc_btn.setStyleSheet("""
            QPushButton {
                background: rgba(100,181,246,0.08);
                border: 1px solid rgba(100,181,246,0.2);
                border-radius: 8px; color: #90caf9;
                min-height: 48px; padding: 6px 14px; 
                font-size: 15px; font-weight: 700;
                font-family: "Microsoft YaHei", "微软雅黑";
                text-align: left;
            }
            QPushButton:hover { background: rgba(100,181,246,0.15); border-color: #42a5f5; color: #e3f2fd; }
        """)
        self.nav_plc_btn.clicked.connect(lambda: self._switch_mode("plc_monitor"))
        layout.addWidget(self.nav_plc_btn)

        layout.addStretch()
        return card

    def _switch_mode(self, mode):
        self.current_mode = mode

        def _active_style():
            return """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1565c0, stop:1 #0d47a1);
                    border: none; border-radius: 8px; color: #e3f2fd;
                    min-height: 48px; padding: 6px 14px; 
                    font-size: 15px; font-weight: 700;
                    font-family: "Microsoft YaHei", "微软雅黑";
                    text-align: left;
                }
                QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976d2, stop:1 #1565c0); }
            """

        def _inactive_style():
            return """
                QPushButton {
                    background: rgba(100,181,246,0.08);
                    border: 1px solid rgba(100,181,246,0.2);
                    border-radius: 8px; color: #90caf9;
                    min-height: 48px; padding: 6px 14px; 
                    font-size: 15px; font-weight: 700;
                    font-family: "Microsoft YaHei", "微软雅黑";
                    text-align: left;
                }
                QPushButton:hover { background: rgba(100,181,246,0.15); border-color: #42a5f5; color: #e3f2fd; }
            """

        if mode == "binding":
            self.left_stack.setCurrentIndex(0)
            self.right_stack.setCurrentIndex(0)
            self.nav_binding_btn.setStyleSheet(_active_style())
            self.nav_packing_btn.setStyleSheet(_inactive_style())
            self.nav_plasma_btn.setStyleSheet(_inactive_style())
            if hasattr(self, "nav_plc_btn"): self.nav_plc_btn.setStyleSheet(_inactive_style())
            self.process_badge.setText(f"当前工序：{self.config['moduleBindProcessCode']}")
        elif mode == "plasma":
            self.left_stack.setCurrentIndex(1)
            self.right_stack.setCurrentIndex(1)
            self.nav_binding_btn.setStyleSheet(_inactive_style())
            self.nav_packing_btn.setStyleSheet(_inactive_style())
            self.nav_plasma_btn.setStyleSheet(_active_style())
            if hasattr(self, "nav_plc_btn"): self.nav_plc_btn.setStyleSheet(_inactive_style())
            self.process_badge.setText("当前工序：激光数据采集")
        elif mode == "packing":
            self.left_stack.setCurrentIndex(2)
            self.right_stack.setCurrentIndex(2)
            self.nav_binding_btn.setStyleSheet(_inactive_style())
            self.nav_packing_btn.setStyleSheet(_active_style())
            self.nav_plasma_btn.setStyleSheet(_inactive_style())
            if hasattr(self, "nav_plc_btn"): self.nav_plc_btn.setStyleSheet(_inactive_style())
            self.process_badge.setText(f"当前工序：{self.config['packingProcessCode']}")
            self.packing_tab.set_generated_modules(self._generated_records)
            if not self.packing_tab.pack_info:
                self.packing_tab.pack_input.setEnabled(True)
        elif mode == "plc_monitor":
            self.left_stack.setCurrentIndex(3)
            self.right_stack.setCurrentIndex(3)
            self.nav_binding_btn.setStyleSheet(_inactive_style())
            self.nav_packing_btn.setStyleSheet(_inactive_style())
            self.nav_plasma_btn.setStyleSheet(_inactive_style())
            if hasattr(self, "nav_plc_btn"): self.nav_plc_btn.setStyleSheet(_active_style())
            self.process_badge.setText("当前功能：PLC 读写助手")

    def _create_plc_monitor_left(self):
        """PLC 读写监控左侧面板提示说明"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        info = QFrame()
        info.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 16px;
            }
        """)
        il = QVBoxLayout(info)
        t = QLabel("📺 PLC 读写助手")
        t.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9;")
        d = QLabel("在这里您可以添加、删除并监视特定的 PLC 点位地址。\\n\\n输入偏移量与数据类型后，可直接向 PLC 下发指令，用于现场调试与信号模拟。")
        d.setStyleSheet("color: #b0bec5; font-size: 13px; line-height: 1.5;")
        d.setWordWrap(True)
        il.addWidget(t)
        il.addSpacing(10)
        il.addWidget(d)
        il.addStretch()

        layout.addWidget(info)
        layout.addStretch()
        return widget

    # =====================================================================
    #  模块码绑定 — 左侧面板（精简提示）
    # =====================================================================
    def _create_binding_left(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        info = QFrame()
        info.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        il = QVBoxLayout(info)
        il.setSpacing(8)
        tl = QLabel("🔗 模块码绑定")
        tl.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9;")
        il.addWidget(tl)
        dl = QLabel("请在右侧【扫描查询】标签页\n扫描产品条码开始流程。")
        dl.setStyleSheet("font-size: 13px; color: #78909c;")
        dl.setWordWrap(True)
        il.addWidget(dl)
        layout.addWidget(info)

        step_card = QFrame()
        step_card.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        sl = QVBoxLayout(step_card)
        sl.setSpacing(6)
        st = QLabel("工序步骤")
        st.setStyleSheet("font-size: 14px; font-weight: 700; color: #90caf9;")
        sl.addWidget(st)
        for step_text in ["① 获取工单", "② 工步下发", "③ 单物料校验", "④ 生成模块码", "⑤ 全物料校验", "⑥ 数据上传"]:
            lbl = QLabel(step_text)
            lbl.setStyleSheet("font-size: 13px; color: #78909c; padding: 2px 0;")
            sl.addWidget(lbl)
        layout.addWidget(step_card)
        return widget

    # =====================================================================
    #  模块码绑定 — 右侧面板（标签页）
    # =====================================================================
    def _create_binding_right(self):
        widget = QWidget()
        widget.setObjectName("right_panel")
        widget.setStyleSheet("""
            QWidget {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
            }
        """)
        right_layout = QVBoxLayout(widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Tab Bar
        tab_bar = QHBoxLayout()
        tab_bar.setContentsMargins(10, 8, 10, 0)
        tab_bar.setSpacing(2)
        tab_bar.setAlignment(Qt.AlignLeft)
        self.tabs = [
            ("① 获取工单", "order"),
            ("② 工步下发", "route"),
            ("③ 单物料校验", "material"),
            ("④ 生成模块码", "generate"),
            ("⑤ 全物料校验", "full_material"),
            ("⑥ 数据上传", "upload"),
            ("🔌 PLC监控", "plc"),
            ("📋 记录", "log"),
        ]
        self.tab_buttons = {}
        for text, key in self.tabs:
            btn = QPushButton(text)
            btn.setObjectName("tab_btn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(lambda checked, k=key: self._switch_tab(k))
            self.tab_buttons[key] = btn
            tab_bar.addWidget(btn)
        tab_bar.addStretch()
        right_layout.addLayout(tab_bar)

        # Tab Content
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent; border: none;")

        # page 0: 获取工单（扫描输入 + 工单信息）
        order_page = self._create_order_page()
        self.stack.addWidget(order_page)

        self.route_tab = RouteTableTab()
        self.stack.addWidget(self.route_tab)

        self.material_tab = MaterialScannerTab()
        self.material_tab.log.connect(self._add_log)
        self.material_tab.api_record.connect(self._add_api_record_dict)
        self.material_tab.complete.connect(self._on_material_complete)
        self.stack.addWidget(self.material_tab)

        self.generate_tab = ModuleGenerateTab()
        self.generate_tab.log.connect(self._add_log)
        self.generate_tab.api_record.connect(self._add_api_record_dict)
        self.generate_tab.generated.connect(self._on_module_generated)
        self.stack.addWidget(self.generate_tab)

        # page 4: 全物料校验
        self.full_material_tab = FullMaterialTab()
        self.full_material_tab.log.connect(self._add_log)
        self.full_material_tab.api_record.connect(self._add_api_record_dict)
        self.full_material_tab.complete.connect(self._on_full_material_complete)
        self.stack.addWidget(self.full_material_tab)

        # page 5: 数据上传（总体状态 + 上传结果）
        upload_page = self._create_upload_page()
        self.stack.addWidget(upload_page)

        # page 5: PLC 监控
        self.plc_tab = PlcMonitorTab(self.s7_service, self.config)
        self.plc_tab.log.connect(self._add_log)
        self.plc_tab.config_changed.connect(self._save_config)
        self.stack.addWidget(self.plc_tab)

        # page 6: 记录（接口交互 + 操作日志）
        log_page = self._create_log_page()
        self.stack.addWidget(log_page)

        right_layout.addWidget(self.stack)
        return widget

    def _create_order_page(self):
        """创建右侧的【扫描查询】标签页，包含扫描输入、工单信息、总体状态"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # 扫描卡片
        scan_card = self._create_card("产品条码", step="1")
        scan_layout = scan_card.layout()
        scan_layout.setSpacing(8)

        input_wrap = QHBoxLayout()
        input_wrap.setSpacing(8)
        input_wrap.setContentsMargins(4, 4, 4, 4)
        input_wrap_widget = QWidget()
        input_wrap_widget.setStyleSheet("""
            QWidget {
                background: #0d1117;
                border: 2px solid rgba(100,181,246,0.25);
                border-radius: 8px;
            }
        """)
        input_wrap_widget.setLayout(input_wrap)
        input_icon = QLabel("📡")
        input_icon.setStyleSheet("font-size: 18px;")
        input_wrap.addWidget(input_icon)
        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText("等待 PLC 自动获取条码...")
        self.scan_input.setReadOnly(True)
        self.scan_input.setStyleSheet("""
            QLineEdit {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.3);
                border-radius: 6px;
                color: #e0e6ed;
                font-size: 16px;
                font-family: Consolas, monospace;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border: 1px solid #42a5f5;
                background: #1a2332;
            }
        """)
        input_wrap.addWidget(self.scan_input, stretch=1)
        scan_layout.addWidget(input_wrap_widget)

        hint = QLabel("条码由 PLC 自动写入，无需手动操作")
        hint.setStyleSheet("color: #37474f; font-size: 13px; margin: 2px 0 0 0;")
        scan_layout.addWidget(hint)

        layout.addWidget(scan_card)

        # 工单结果/错误显示区域（独立卡片，可拉伸）
        self.order_result_widget = QWidget()
        self.order_result_widget.setStyleSheet("""
            QWidget {
                background: rgba(21,101,192,0.08);
                border: 1px solid rgba(100,181,246,0.15);
                border-radius: 8px;
            }
        """)
        orw_layout = QVBoxLayout(self.order_result_widget)
        orw_layout.setSpacing(6)
        orw_layout.setContentsMargins(10, 10, 10, 10)
        self.order_result_widget.setVisible(False)
        layout.addWidget(self.order_result_widget, stretch=1)

        layout.addStretch()
        return page

    # =====================================================================
    #  模组入箱 — 左侧面板（简洁提示）
    # =====================================================================
    def _create_upload_page(self):
        """创建数据上传标签页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # 总体流程状态卡片
        self.result_card = self._create_card("总体流程状态", step="")
        result_layout = self.result_card.layout()
        result_layout.setSpacing(10)

        self.result_display = QWidget()
        self.result_display.setObjectName("result_display_idle")
        self.result_display.setStyleSheet("""
            QWidget {
                background: rgba(21,101,192,0.05);
                border: 1px solid rgba(100,181,246,0.1);
                border-radius: 8px;
                padding: 16px;
            }
        """)
        rd_layout = QHBoxLayout(self.result_display)
        rd_layout.setSpacing(10)
        rd_layout.setAlignment(Qt.AlignCenter)
        self.result_icon = QLabel("⏳")
        self.result_icon.setStyleSheet("font-size: 30px;")
        rd_layout.addWidget(self.result_icon)
        self.result_text = QLabel("待执行")
        self.result_text.setObjectName("result_text")
        self.result_text.setStyleSheet("font-size: 30px; font-weight: 800; letter-spacing: 1px; color: #e0e6ed;")
        rd_layout.addWidget(self.result_text)
        self.result_msg = QLabel("")
        self.result_msg.setObjectName("result_msg")
        self.result_msg.setStyleSheet("color: #78909c; font-size: 14px;")
        rd_layout.addWidget(self.result_msg)
        result_layout.addWidget(self.result_display)

        self.reset_btn = QPushButton("🔄 复位状态 / 准备下一件")
        self.reset_btn.setObjectName("btn_reset")
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.clicked.connect(self._reset_result)
        self.reset_btn.setVisible(False)
        result_layout.addWidget(self.reset_btn)
        layout.addWidget(self.result_card)

        # 上传记录卡片
        self.upload_record_card = self._create_card("上传记录", step="")
        ur_layout = self.upload_record_card.layout()
        self.upload_record_empty = QLabel("暂无上传记录")
        self.upload_record_empty.setAlignment(Qt.AlignCenter)
        self.upload_record_empty.setStyleSheet("color: #37474f; font-size: 14px; padding: 20px;")
        ur_layout.addWidget(self.upload_record_empty)
        self.upload_record_content = QWidget()
        self.upload_record_content_layout = QVBoxLayout(self.upload_record_content)
        self.upload_record_content_layout.setSpacing(6)
        self.upload_record_content.setVisible(False)
        ur_layout.addWidget(self.upload_record_content)
        layout.addWidget(self.upload_record_card)

        layout.addStretch()
        return page

    def _create_log_page(self):
        """创建记录标签页（接口交互 + 操作日志上下排列）"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        # 上半部分：接口交互
        api_widget = QWidget()
        api_widget.setStyleSheet("background: #131929; border: 1px solid rgba(100,181,246,0.12); border-radius: 10px;")
        api_layout = QVBoxLayout(api_widget)
        api_layout.setContentsMargins(10, 10, 10, 10)
        api_header = QLabel("🔌 接口交互")
        api_header.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9;")
        api_layout.addWidget(api_header)

        api_layout.addWidget(self.api_tab)
        layout.addWidget(api_widget, stretch=1)

        # 下半部分：操作日志
        log_widget = QWidget()
        log_widget.setStyleSheet("background: #131929; border: 1px solid rgba(100,181,246,0.12); border-radius: 10px;")
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_header = QLabel("📄 操作日志")
        log_header.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9;")
        log_layout.addWidget(log_header)

        log_layout.addWidget(self.log_tab)
        layout.addWidget(log_widget, stretch=1)

        return page

    def _create_packing_left(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        info = QFrame()
        info.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        il = QVBoxLayout(info)
        il.setSpacing(8)
        tl = QLabel("📦 模组入箱工序")
        tl.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9;")
        il.addWidget(tl)
        dl = QLabel("请在右侧界面扫描PACK箱条码，\nMES将自动下发模组清单。")
        dl.setStyleSheet("font-size: 13px; color: #78909c;")
        dl.setWordWrap(True)
        il.addWidget(dl)
        layout.addWidget(info)

        step_card = QFrame()
        step_card.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        sl = QVBoxLayout(step_card)
        sl.setSpacing(6)
        st = QLabel("工序步骤")
        st.setStyleSheet("font-size: 14px; font-weight: 700; color: #90caf9;")
        sl.addWidget(st)
        for step_text in ["① 扫描PACK箱", "② 入箱预校验", "③ 人工复判", "④ 上传入箱顺序"]:
            lbl = QLabel(step_text)
            lbl.setStyleSheet("font-size: 13px; color: #78909c; padding: 2px 0;")
            sl.addWidget(lbl)
        layout.addWidget(step_card)
        return widget

    # =====================================================================
    #  等离子清洗 — 左侧面板
    # =====================================================================
    def _create_plasma_left(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        info = QFrame()
        info.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        il = QVBoxLayout(info)
        il.setSpacing(8)
        tl = QLabel("🔬 激光数据采集")
        tl.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9;")
        il.addWidget(tl)
        dl = QLabel("请在右侧界面查看激光数据采集实时参数。\n参数通过 PLC 自动读取并展示。")
        dl.setStyleSheet("font-size: 13px; color: #78909c;")
        dl.setWordWrap(True)
        il.addWidget(dl)
        layout.addWidget(info)

        step_card = QFrame()
        step_card.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        sl = QVBoxLayout(step_card)
        sl.setSpacing(6)
        st = QLabel("监控参数")
        st.setStyleSheet("font-size: 14px; font-weight: 700; color: #90caf9;")
        sl.addWidget(st)
        for step_text in ["① 清洗状态", "② 清洗功率", "③ 清洗速率", "④ 腔体温度", "⑤ 气体流量"]:
            lbl = QLabel(step_text)
            lbl.setStyleSheet("font-size: 13px; color: #78909c; padding: 2px 0;")
            sl.addWidget(lbl)
        layout.addWidget(step_card)
        return widget

    # =====================================================================
    #  公共辅助
    # =====================================================================
    def _create_card(self, title, step=None):
        card = QFrame()
        card.setObjectName("card_widget")
        card.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        if step:
            badge = QLabel(step)
            badge.setObjectName("step_badge")
            badge.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1565c0, stop:1 #0d47a1);
                border-radius: 10px; color: white; font-size: 13px; font-weight: 700;
                min-width: 20px; max-width: 20px; min-height: 20px; max-height: 20px;
                qproperty-alignment: AlignCenter;
            """)
            title_layout.addWidget(badge)
        tl = QLabel(title)
        tl.setObjectName("card_title")
        tl.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9; letter-spacing: 0.5px;")
        title_layout.addWidget(tl)
        title_layout.addStretch()
        card_layout.addLayout(title_layout)
        return card

    def _switch_tab(self, key):
        index_map = {"order": 0, "route": 1, "material": 2, "generate": 3, "full_material": 4, "upload": 5, "plc": 6, "log": 7}
        self.stack.setCurrentIndex(index_map[key])
        for k, btn in self.tab_buttons.items():
            active = (k == key)
            btn.setChecked(active)
            if active:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #131929;
                        border: 1px solid rgba(100,181,246,0.15);
                        border-bottom: none;
                        border-radius: 6px 6px 0 0;
                        color: #42a5f5;
                        font-size: 14px;
                        font-weight: 600;
                        padding: 7px 16px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: 1px solid transparent;
                        border-bottom: none;
                        border-radius: 6px 6px 0 0;
                        color: #546e7a;
                        font-size: 14px;
                        font-weight: 500;
                        padding: 7px 16px;
                    }
                    QPushButton:hover {
                        color: #90caf9;
                        background: rgba(100,181,246,0.05);
                    }
                """)

    # =====================================================================
    #  业务逻辑 — 模块码绑定
    # =====================================================================
    def _handle_scan(self):
        code = self.scan_input.text().strip()
        if not code:
            self._add_log("warn", "产品条码为空，请输入后提交")
            self.scan_input.setFocus()
            return

        if getattr(self, "_is_scanning", False):
            self._add_log("warn", "当前已有正在进行的扫描校验任务，本次请求拦截。")
            return
        self._is_scanning = True

        self._reset_all()
        self.product_code = code
        self._add_log("info", f"开始查询工单: {code}")

        # 构造请求参数（绑定流程使用 moduleBindProcessCode）
        payload = {
            "technicsProcessCode": self.config.get("moduleBindProcessCode", ""),
            "productCode": code
        }
        url = self.config.get("orderApiUrl", "")
        route_url = self.config.get("routeApiUrl", "")
        work_seq_no = self.config.get("moduleBindProcessCode", "")

        self._add_log("info", f"[获取工单] POST {url}")
        self._add_log("info", f"[获取工单] 参数: {json.dumps(payload, ensure_ascii=False)}")

        # 禁用输入，防止重复提交
        self.scan_input.setEnabled(False)

        # 启动工作线程
        self.worker = WorkerThread(url, payload, route_url, work_seq_no, skip_implicit_route=True)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.error.connect(self._on_worker_error)
        self.worker.api_record.connect(self._add_api_record_dict)
        self.worker.start()

    def _on_worker_finished(self, order_data, route_data, order_info):
        self.scan_input.setEnabled(True)

        # 处理多个工单的情况：直接弹出选择器，不再按配方过滤
        if route_data is None and isinstance(order_info, list):
            if len(order_info) == 1:
                # 只有一个工单，直接用
                selected_order = order_info[0]
                route_url = self.config.get("routeApiUrl", "")
                work_seq_no = self.config.get("moduleBindProcessCode", "")
                self.worker = WorkerThread("", {}, route_url, work_seq_no, order_info=selected_order)
                self.worker.finished.connect(self._on_worker_finished)
                self.worker.error.connect(self._on_worker_error)
                self.worker.api_record.connect(self._add_api_record_dict)
                self.worker.start()
                return
            self._show_order_selector(order_info, order_data)
            self._is_scanning = False
            return

        url = self.config.get("orderApiUrl", "")
        route_url = self.config.get("routeApiUrl", "")
        payload = {
            "technicsProcessCode": self.config.get("moduleBindProcessCode", ""),
            "productCode": self.product_code
        }

        # 直接使用工作线程解析好的 order_info
        self.order_info = order_info

        # 解析获取工单响应
        self._add_log("success", f"[获取工单] 成功: {self.order_info.get('orderCode', '-')}")

        # 构造工步下发的请求参数用于记录
        route_code = self.order_info.get("routeCode") or self.order_info.get("route_No", "")
        route_payload = {
            "routeCode": route_code,
            "workSeqNo": self.config.get("moduleBindProcessCode", "")
        }

        # 获取工单成功，先显示工单信息
        self._update_info_card()

        # 切换到工步下发标签页
        self._switch_tab("route")

        # 判断工步下发是否成功（优先检查 code 字段）
        route_code_val = route_data.get("code", 200)
        if route_code_val != 200:
            err_msg = route_data.get("message", f"业务码 {route_code_val}")
            self._add_log("error", f"[工步下发] 失败: {err_msg}")
            self.route_tab.show_error("工步下发失败", err_msg)
            self._is_scanning = False
            return

        seq_list = None
        if "data" in route_data and isinstance(route_data["data"], dict):
            seq_list = route_data["data"].get("workSeqList")
        if seq_list is None:
            seq_list = route_data.get("datas", [])
        if seq_list is None:
            seq_list = route_data.get("data", [])

        if not (isinstance(seq_list, list) and len(seq_list) > 0):
            self._add_log("warn", "[工步下发] 响应中未找到工步数据")
            self.route_tab.show_error("工步下发失败", "响应中未找到工步数据")
            self._is_scanning = False
            return

        self.route_steps = seq_list
        self._add_log("success", f"[工步下发] 成功，获取到 {len(self.route_steps)} 条工步")

        self.route_tab.set_data(self.route_steps)
        self.material_tab.set_order_info(self.order_info)
        self.material_tab.set_config(self.config)
        self.material_tab.set_product_code(self.product_code)
        self.material_tab.set_steps(self.route_steps)
        self._add_log("info", f"流程进入工步下发，共 {len(self.route_steps)} 条工步")

        # 自动切换到单物料校验（第3步）
        self._switch_tab("material")
        self._is_scanning = False

    def _on_worker_error(self, error_str):
        self.scan_input.setEnabled(True)
        self._is_scanning = False

        title, message = error_str.split("|", 1)
        self._add_log("error", f"{title}: {message}")
        self._show_order_error(title, message)

    def _show_order_selector(self, orders, order_data):
        """当获取到多个工单时，弹出选择对话框让用户根据 specsCode 选择"""
        dialog = QDialog(self)
        dialog.setWindowTitle("请选择产品规格")
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet("""
            QDialog {
                background: #0a0e1a;
                border: 1px solid rgba(100,181,246,0.2);
                border-radius: 10px;
            }
            QLabel {
                color: #90caf9;
                font-size: 15px;
                font-weight: 600;
            }
            QListWidget {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.15);
                border-radius: 8px;
                color: #e0e6ed;
                font-size: 15px;
                padding: 8px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-bottom: 1px solid rgba(100,181,246,0.06);
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background: rgba(21,101,192,0.3);
                color: #42a5f5;
            }
            QListWidget::item:hover {
                background: rgba(21,101,192,0.15);
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1565c0, stop:1 #0d47a1);
                border: none;
                border-radius: 6px;
                color: #e3f2fd;
                padding: 8px 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976d2, stop:1 #1565c0);
            }
            QPushButton:disabled {
                background: #37474f;
                color: #78909c;
            }
        """)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        hint = QLabel("查询到多个工单，请选择对应的产品规格：")
        layout.addWidget(hint)

        list_widget = QListWidget()
        for idx, order in enumerate(orders):
            specs = order.get("specsCode", "-")
            order_code = order.get("orderCode", "-")
            item_text = f"规格: {specs}  |  工单: {order_code}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, order)
            list_widget.addItem(item)
        layout.addWidget(list_widget)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        confirm_btn = QPushButton("确定")
        confirm_btn.setEnabled(False)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

        def on_item_clicked():
            confirm_btn.setEnabled(True)

        list_widget.itemClicked.connect(on_item_clicked)

        def on_confirm():
            selected = list_widget.currentItem()
            if not selected:
                return
            selected_order = selected.data(Qt.UserRole)
            dialog.accept()

            # 记录选择
            self._add_log("info", f"[获取工单] 用户选择规格: {selected_order.get('specsCode', '-')}，工单: {selected_order.get('orderCode', '-')}")

            # 使用选择的工单执行工步下发
            route_url = self.config.get("routeApiUrl", "")
            work_seq_no = self.config.get("moduleBindProcessCode", "")
            self.worker = WorkerThread("", {}, route_url, work_seq_no, order_info=selected_order)
            self.worker.finished.connect(self._on_worker_finished)
            self.worker.error.connect(self._on_worker_error)
            self.worker.api_record.connect(self._add_api_record_dict)
            self.worker.start()

        confirm_btn.clicked.connect(on_confirm)
        dialog.exec_()

    # def _fallback_order_data(self, code):
    #     """演示数据回退（网络不可用或接口返回失败时使用）"""
    #     self.order_info = {
    #         "orderCode": f"WO-{code[-8:]}",
    #         "route_No": f"RT-{code[:4]}-2024",
    #         "productMixCode": "MIX-A001",
    #         "productLine": "LINE-01",
    #         "customer": "宁德时代",
    #         "productName": "磷酸铁锂电池模组",
    #     }
    #     self._fallback_route_data()

    #def _fallback_route_data(self):
        """工步演示数据回退"""
        # self.route_steps = [
        #     {
        #         "workseqNo": "WS001",
        #         "workseqName": "电芯来料检查",
        #         "workStepList": [
        #             {
        #                 "workstepNo": "WS001-01",
        #                 "workstepName": "外观检查",
        #                 "workstepType": 2,
        #                 "workStepParamList": [
        #                     {"paramName": "电压", "minQualityValue": 3.2, "maxQualityValue": 3.4, "standardValue": 3.3, "paramUnit": "V"},
        #                     {"paramName": "内阻", "minQualityValue": 0.5, "maxQualityValue": 1.2, "standardValue": 0.8, "paramUnit": "mΩ"},
        #                 ],
        #                 "workStepMaterialList": [
        #                     {"material_No": "CELL", "material_Name": "280Ah磷酸铁锂电芯", "material_number": 16, "noLength": 20, "retrospect_Type": 1, "isCheckLength": 1, "material_id": "M001"},
        #                 ]
        #             },
        #             {"workstepNo": "WS001-02", "workstepName": "模块码绑定", "workstepType": 0}
        #         ]
        #     },
        #     {
        #         "workseqNo": "WS002",
        #         "workseqName": "模组组装",
        #         "workStepList": [
        #             {
        #                 "workstepNo": "WS002-01",
        #                 "workstepName": "端板装配",
        #                 "workstepType": 3,
        #                 "workStepMaterialList": [
        #                     {"material_No": "END-PLATE", "material_Name": "铝合金端板", "material_number": 2, "noLength": 15, "retrospect_Type": 2, "isCheckLength": 0, "material_id": "M002"},
        #                     {"material_No": "BUSBAR", "material_Name": "铜排连接片", "material_number": 17, "noLength": 18, "retrospect_Type": 1, "isCheckLength": 1, "material_id": "M003"},
        #                 ]
        #             },
        #             {
        #                 "workstepNo": "WS002-02",
        #                 "workstepName": "螺栓拧紧",
        #                 "workstepType": 1,
        #                 "workStepLineList": [{"pSetNo": "PSET-01", "torqueSettingCount": 16}],
        #                 "workStepParamList": [
        #                     {"paramName": "扭矩", "minQualityValue": 8.0, "maxQualityValue": 12.0, "standardValue": 10.0, "paramUnit": "N·m"},
        #                     {"paramName": "角度", "minQualityValue": 0, "maxQualityValue": 720, "standardValue": 180, "paramUnit": "°"},
        #                 ]
        #             },
        #             {
        #                 "workstepNo": "WS002-03",
        #                 "workstepName": "电压检测",
        #                 "workstepType": 2,
        #                 "workStepParamList": [
        #                     {"paramName": "总电压", "minQualityValue": 50.0, "maxQualityValue": 55.0, "standardValue": 52.8, "paramUnit": "V"},
        #                 ]
        #             }
        #         ]
        #     },
        #     {
        #         "workseqNo": "WS003",
        #         "workseqName": "涂胶密封",
        #         "workStepList": [
        #             {
        #                 "workstepNo": "WS003-01",
        #                 "workstepName": "结构胶涂覆",
        #                 "workstepType": 4,
        #                 "workStepParamList": [
        #                     {"paramName": "胶量", "minQualityValue": 15, "maxQualityValue": 25, "standardValue": 20, "paramUnit": "g"},
        #                 ]
        #             }
        #         ]
        #     }
        # ]#

    def _show_order_error(self, title, message):
        """在获取工单卡片中显示错误信息（红色醒目）"""
        layout = self.order_result_widget.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        err_title = QLabel(f"❌ {title}")
        err_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ff5252;")
        layout.addWidget(err_title)

        err_msg = QLabel(message)
        err_msg.setStyleSheet("font-size: 14px; color: #ff8a80; padding: 4px 0;")
        err_msg.setWordWrap(True)
        layout.addWidget(err_msg)

        self.order_result_widget.setStyleSheet("""
            QWidget {
                background: rgba(244,67,54,0.08);
                border: 1px solid rgba(255,82,82,0.3);
                border-radius: 8px;
                margin-top: 4px;
            }
        """)
        self.order_result_widget.setVisible(True)

    def _update_info_card(self):
        """在获取工单卡片中显示工单信息"""
        self.order_result_widget.setStyleSheet("""
            QWidget {
                background: rgba(21,101,192,0.08);
                border: 1px solid rgba(100,181,246,0.15);
                border-radius: 8px;
                margin-top: 4px;
            }
        """)
        layout = self.order_result_widget.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        def fmt(val):
            if val is None:
                return "-"
            return str(val) if str(val).strip() else "-"

        # 标题
        title = QLabel("📋 查询结果")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #90caf9; margin-bottom: 6px;")
        layout.addWidget(title)

        # 字段一行一行展示
        field_map = [
            ("工单号", "orderCode", True),
            ("工艺路线编码", "route_No", False),
            ("产品条码", None, False),
        ]

        icons = ["📋", "🔧", "🏷️"]
        for i, (label, key, highlight) in enumerate(field_map):
            if key is None:
                value = self.product_code
            else:
                value = fmt(self.order_info.get(key))

            card = QWidget()
            card.setStyleSheet("""
                QWidget {
                    background: #0d1117;
                    border: 1px solid rgba(100,181,246,0.2);
                    border-radius: 8px;
                }
            """)
            card_layout = QHBoxLayout(card)
            card_layout.setSpacing(10)
            card_layout.setContentsMargins(10, 8, 10, 8)

            icon_lbl = QLabel(icons[i])
            icon_lbl.setStyleSheet("font-size: 16px;")
            card_layout.addWidget(icon_lbl)

            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)
            text_layout.setAlignment(Qt.AlignVCenter)

            name_lbl = QLabel(label)
            name_lbl.setStyleSheet("color: #78909c; font-size: 12px;")

            val_lbl = QLabel(value)
            if highlight:
                val_lbl.setStyleSheet("color: #42a5f5; font-weight: 700; font-size: 14px; font-family: Consolas, monospace;")
            else:
                val_lbl.setStyleSheet("color: #e0e6ed; font-size: 14px; font-family: Consolas, monospace;")

            text_layout.addWidget(name_lbl)
            text_layout.addWidget(val_lbl)
            card_layout.addLayout(text_layout, stretch=1)
            layout.addWidget(card)

        self.order_result_widget.setVisible(True)

    def _on_material_complete(self, materials):
        self._add_log("info", f"[生成模块码] 接收到 {len(materials)} 个校验通过的条码: {[m.get('productCode') for m in materials]}")
        self.material_verification_success = True
        self.verified_materials = materials
        self.test_result = "IDLE"
        self.result_message = "单物料校验通过，请生成模块码"
        self._update_result_display()
        self._add_log("success", "✅ 单物料校验通过！")

        module_codes = [m["productCode"] for m in materials]
        self.generate_tab.set_order_info(self.order_info)
        self.generate_tab.set_config(self.config)
        self.generate_tab.set_module_codes(module_codes)
        self.generate_tab.set_material_list(materials)

        # 自动切换到生成模块码
        self._switch_tab("generate")

    def _on_module_generated(self, generated_records):
        self._generated_records = generated_records
        self._add_log("info", "[全物料校验] 模块码已生成，进入全物料校验环节")
        self.full_material_tab.set_config(self.config)
        self.full_material_tab.set_order_info(self.order_info)
        self.full_material_tab.set_data(self.verified_materials, generated_records)
        self._switch_tab("full_material")

    def _on_packing_completed(self, module_list, order_info):
        """模组入箱单物料校验完成（全物料校验已内置于 ModulePackingTab，此处仅保留兼容）"""
        self._add_log("info", "[模组入箱] 单物料校验完成，由内部页面继续全物料校验")

    def _on_full_material_complete(self):
        """绑定流程的全物料校验完成回调 —— 数据暂存，自动进入入箱流程"""
        self._pending_bind_upload_data = {
            "order_info": self.order_info,
            "product_code": self.product_code,
            "generated_records": self._generated_records,
            "verified_materials": self.verified_materials,
            "process_start_time": self.process_start_time,
            "bind_push_url": self.config.get("moduleBindPushUrl", "").strip(),
        }
        self._add_log("info", "[绑定流程] 全物料校验通过，绑定数据已暂存，自动进入入箱流程")
        self.test_result = "OK"
        self.result_message = "绑定流程已完成，已自动切换至入箱流程。"
        self._update_result_display()
        self._add_log("success", "✅ 绑定流程已完成，自动进入入箱流程")
        # 自动切换到入箱模式
        self._switch_mode("packing")

    def _on_packing_upload_ready(self, packing_data):
        """入箱流程完成后的统一上传回调
        packing_data: dict 包含 pack_code, module_list, order_info 等入箱数据
        """
        self._add_log("info", "[统一上传] 入箱流程完成，开始执行模块绑定+入箱位置信息上传...")

        # ------------------------------------------------------------------
        # 1. 模块绑定模组数据上传
        # ------------------------------------------------------------------
        if self._pending_bind_upload_data:
            bind_data = self._pending_bind_upload_data
            bind_url = bind_data["bind_push_url"]
            if bind_url:
                bind_payload = {
                    "produceOrderCode": bind_data["order_info"].get("orderCode", ""),
                    "routeNo": bind_data["order_info"].get("route_No", ""),
                    "technicsProcessCode": self.config.get("moduleBindProcessCode", ""),
                    "productCode": bind_data["product_code"],
                    "moduleCount": len(bind_data["generated_records"]),
                    "bindRecords": bind_data["generated_records"],
                    "startTime": bind_data["process_start_time"],
                    "endTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                res_data = MesService.upload_module_bind(bind_url, bind_payload)
                self._add_api_record(
                    "模块绑定模组数据上传", bind_url,
                    "success" if MesService._is_success(res_data) else "error",
                    bind_payload, res_data
                )
                if MesService._is_success(res_data):
                    self._add_log("success", "[模块绑定模组数据上传] 上传成功")
                else:
                    self._add_log("error", f"[模块绑定模组数据上传] 失败: {res_data.get('message', '未知错误')}")
            else:
                self._add_log("warn", "[模块绑定模组数据上传] 未配置上传接口 URL，跳过")
        else:
            self._add_log("warn", "[模块绑定模组数据上传] 未发现暂存的绑定数据，可能未执行绑定流程")

        # ------------------------------------------------------------------
        # 2. 模组入箱位置信息上传
        # ------------------------------------------------------------------
        packing_url = self.config.get("packingPushUrl", "").strip()
        if packing_url:
            packing_payload = {
                "produceOrderCode": packing_data.get("order_info", {}).get("orderCode", ""),
                "routeNo": packing_data.get("order_info", {}).get("route_No", ""),
                "technicsProcessCode": self.config.get("packingProcessCode", ""),
                "packCode": packing_data.get("pack_code", ""),
                "moduleList": packing_data.get("module_list", []),
                "uploadTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            pack_res = MesService.upload_pack_box(packing_url, packing_payload)
            self._add_api_record(
                "模组入箱位置信息上传", packing_url,
                "success" if MesService._is_success(pack_res) else "error",
                packing_payload, pack_res
            )
            if MesService._is_success(pack_res):
                self._add_log("success", "[模组入箱位置信息上传] 上传成功")
            else:
                self._add_log("error", f"[模组入箱位置信息上传] 失败: {pack_res.get('message', '未知错误')}")
        else:
            self._add_log("warn", "[模组入箱位置信息上传] 未配置上传接口 URL，跳过")

        # 清空暂存数据
        self._pending_bind_upload_data = None
        self._add_log("info", "[统一上传] 所有上传任务执行完毕，流程结束")

    def _update_result_display(self):
        if self.test_result == "OK":
            self.result_display.setObjectName("result_display_ok")
            self.result_display.setStyleSheet("""
                QWidget {
                    background: rgba(0,230,118,0.08);
                    border: 1px solid rgba(0,230,118,0.3);
                    border-radius: 8px;
                    padding: 16px;
                }
            """)
            self.result_icon.setText("✅")
            self.result_text.setText("OK")
            self.result_text.setStyleSheet("font-size: 30px; font-weight: 800; color: #00e676;")
        elif self.test_result == "NG":
            self.result_display.setObjectName("result_display_ng")
            self.result_display.setStyleSheet("""
                QWidget {
                    background: rgba(255,82,82,0.08);
                    border: 1px solid rgba(255,82,82,0.3);
                    border-radius: 8px;
                    padding: 16px;
                }
            """)
            self.result_icon.setText("❌")
            self.result_text.setText("NG")
            self.result_text.setStyleSheet("font-size: 30px; font-weight: 800; color: #ff5252;")
        else:
            self.result_display.setObjectName("result_display_idle")
            self.result_display.setStyleSheet("""
                QWidget {
                    background: rgba(21,101,192,0.05);
                    border: 1px solid rgba(100,181,246,0.1);
                    border-radius: 8px;
                    padding: 16px;
                }
            """)
            self.result_icon.setText("⏳")
            self.result_text.setText("待执行")
            self.result_text.setStyleSheet("font-size: 30px; font-weight: 800; color: #e0e6ed;")

        self.result_msg.setText(self.result_message)
        self.reset_btn.setVisible(bool(self.product_code.strip()))

    def _reset_result(self):
        if self.product_code.strip() and not (self.test_result == "OK" and "已完成" in self.result_message):
            dlg = LoginDialog("admin", "123", self)
            if dlg.exec_() != QDialog.Accepted or not dlg.is_authenticated():
                return
            self._add_log("warn", f"管理员 [{dlg.username_input.text()}] 授权：执行强制复位")

        self._execute_reset()

    def _execute_reset(self):
        self.product_code = ""
        self.scan_input.clear()
        self.order_info = None
        self.route_steps = []
        self.material_verification_success = False
        self.test_result = "IDLE"
        self.result_message = ""
        self.verified_materials = []
        self._generated_records = []
        self._pending_bind_upload_data = None
        self.api_records = []
        self.process_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.order_result_widget.setVisible(False)
        self.route_tab.set_data([])
        self.material_tab.reset()
        self.generate_tab.reset()
        self.full_material_tab.reset()
        self.api_tab.set_records([])
        self.reset_btn.setVisible(False)
        self._update_result_display()
        self._add_log("info", "----------------------------------------")
        self._add_log("info", "✅ 系统已全面复位，请开始新任务")
        self.scan_input.setFocus()
        self._switch_tab("order")

    def _reset_all(self):
        self.order_info = None
        self.route_steps = []
        self.material_verification_success = False
        self.test_result = "IDLE"
        self.result_message = ""
        self.verified_materials = []
        self.api_records = []
        self.order_result_widget.setVisible(False)
        self.route_tab.set_data([])
        self.material_tab.reset()
        self.generate_tab.reset()
        self.full_material_tab.reset()
        self.api_tab.set_records([])
        self._update_result_display()

    # =====================================================================
    #  公共方法
    # =====================================================================
    def _add_log(self, level, msg):
        self.log_tab.add_log(level, msg)
        self._persist_log(level, msg)

    def _add_api_record(self, title, url, status, req_body, res_body=None):
        rec = {
            "title": title,
            "url": url,
            "status": status,
            "time": datetime.now().strftime("%H:%M:%S"),
            "reqBody": req_body,
            "resBody": res_body,
            "duration": 120,
            "expanded": True,
        }
        self.api_records.insert(0, rec)
        self.api_tab.set_records(self.api_records)
        self._persist_api_record(rec)

    def _add_api_record_dict(self, rec_dict):
        rec_dict.setdefault("time", datetime.now().strftime("%H:%M:%S"))
        rec_dict.setdefault("duration", 120)
        rec_dict.setdefault("expanded", True)
        self.api_records.insert(0, rec_dict)
        self.api_tab.set_records(self.api_records)
        self._persist_api_record(rec_dict)

    def _persist_log(self, level, msg):
        """将操作日志持久化到本地文件"""
        path = self.config.get("logSavePath", "").strip()
        if not path:
            return
        try:
            os.makedirs(path, exist_ok=True)
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = os.path.join(path, f"操作日志_{date_str}.txt")
            with open(filename, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level.upper()}] {msg}\n")
        except Exception:
            pass

    def _persist_api_record(self, rec):
        """将接口交互记录持久化到本地文件"""
        path = self.config.get("logSavePath", "").strip()
        if not path:
            return
        try:
            os.makedirs(path, exist_ok=True)
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = os.path.join(path, f"接口交互_{date_str}.txt")
            with open(filename, "a", encoding="utf-8") as f:
                f.write(f"{'='*60}\n")
                f.write(f"时间: {rec.get('time', '-')}\n")
                f.write(f"接口: {rec.get('title', '-')}\n")
                f.write(f"URL: {rec.get('url', '-')}\n")
                f.write(f"状态: {rec.get('status', '-')}\n")
                f.write(f"耗时: {rec.get('duration', '-')}ms\n")
                req = rec.get('reqBody', '')
                if req:
                    f.write(f"请求:\n{req}\n")
                res = rec.get('resBody', '')
                if res:
                    f.write(f"响应:\n{res}\n")
                f.write(f"{'='*60}\n\n")
        except Exception:
            pass

    # =====================================================================
    #  配方管理（仅模块码绑定模块）
    # =====================================================================
    def _refresh_recipe_combo(self):
        """刷新配方下拉框"""
        if not hasattr(self, 'recipe_combo'):
            return
        self.recipe_combo.clear()
        recipes = self.config.get("recipes", [])
        current = self.config.get("currentRecipe", "")
        if not recipes:
            self.recipe_combo.addItem("暂无配方，请先创建")
            self.recipe_combo.setEnabled(False)
            return
        self.recipe_combo.setEnabled(True)
        self.recipe_combo.addItem("-- 请选择配方 --", "")
        for r in recipes:
            name = r.get("name", "未命名")
            specs = r.get("specsCode", "")
            display = f"{name} ({specs})"
            self.recipe_combo.addItem(display, specs)
        # 恢复上次选中的配方
        if current:
            idx = self.recipe_combo.findData(current)
            if idx >= 0:
                self.recipe_combo.setCurrentIndex(idx)

    def _on_recipe_changed(self, index):
        """配方切换时保存当前选择"""
        if not hasattr(self, 'recipe_combo'):
            return
        specs = self.recipe_combo.itemData(index)
        if specs is not None:
            self.config["currentRecipe"] = specs
            self._save_config()

    def _open_recipe_manager(self):
        """打开配方管理对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("配方管理")
        dialog.setMinimumSize(500, 400)
        dialog.setStyleSheet("""
            QDialog {
                background: #0a0e1a;
                border: 1px solid rgba(100,181,246,0.2);
                border-radius: 10px;
            }
            QLabel {
                color: #90caf9;
                font-size: 15px;
                font-weight: 600;
            }
            QTableWidget {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.15);
                border-radius: 8px;
                color: #e0e6ed;
                font-size: 14px;
                gridline-color: rgba(100,181,246,0.06);
            }
            QTableWidget::item {
                padding: 8px 10px;
                border-bottom: 1px solid rgba(100,181,246,0.06);
            }
            QTableWidget::item:selected {
                background: rgba(21,101,192,0.3);
                color: #42a5f5;
            }
            QHeaderView::section {
                background: rgba(21,101,192,0.2);
                color: #78909c;
                font-weight: 600;
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid rgba(100,181,246,0.1);
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1565c0, stop:1 #0d47a1);
                border: none;
                border-radius: 6px;
                color: #e3f2fd;
                padding: 7px 16px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976d2, stop:1 #1565c0);
            }
            QPushButton#btn_secondary {
                background: rgba(100,181,246,0.08);
                border: 1px solid rgba(100,181,246,0.2);
                color: #90caf9;
            }
            QPushButton#btn_secondary:hover {
                background: rgba(100,181,246,0.15);
            }
            QPushButton#btn_danger {
                background: rgba(244,67,54,0.1);
                border: 1px solid rgba(244,67,54,0.2);
                color: #ef9a9a;
            }
            QPushButton#btn_danger:hover {
                background: rgba(244,67,54,0.2);
            }
        """)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        hint = QLabel("📋 配方列表（每个配方对应一个产品规格 specsCode）")
        layout.addWidget(hint)

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["配方名称", "规格代码 (specsCode)", "备注"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(table)

        def refresh_table():
            recipes = self.config.get("recipes", [])
            table.setRowCount(len(recipes))
            for i, r in enumerate(recipes):
                table.setItem(i, 0, QTableWidgetItem(r.get("name", "")))
                table.setItem(i, 1, QTableWidgetItem(r.get("specsCode", "")))
                table.setItem(i, 2, QTableWidgetItem(r.get("note", "")))

        refresh_table()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        add_btn = QPushButton("➕ 新增")
        add_btn.setObjectName("btn_secondary")
        btn_layout.addWidget(add_btn)

        edit_btn = QPushButton("✏️ 编辑")
        edit_btn.setObjectName("btn_secondary")
        btn_layout.addWidget(edit_btn)

        del_btn = QPushButton("🗑️ 删除")
        del_btn.setObjectName("btn_danger")
        btn_layout.addWidget(del_btn)

        layout.addLayout(btn_layout)

        def get_selected_row():
            items = table.selectedItems()
            if not items:
                return -1
            return items[0].row()

        def on_add():
            name, ok1 = QInputDialog.getText(dialog, "新增配方", "配方名称:")
            if not ok1 or not name.strip():
                return
            specs, ok2 = QInputDialog.getText(dialog, "新增配方", "规格代码 (specsCode):")
            if not ok2 or not specs.strip():
                return
            note, ok3 = QInputDialog.getText(dialog, "新增配方", "备注（可选）:")
            recipes = self.config.setdefault("recipes", [])
            recipes.append({
                "name": name.strip(),
                "specsCode": specs.strip(),
                "note": note.strip() if ok3 else ""
            })
            self._save_config()
            refresh_table()
            self._refresh_recipe_combo()

        def on_edit():
            row = get_selected_row()
            if row < 0:
                QMessageBox.warning(dialog, "提示", "请先选择一行")
                return
            recipes = self.config.get("recipes", [])
            r = recipes[row]
            name, ok1 = QInputDialog.getText(dialog, "编辑配方", "配方名称:", text=r.get("name", ""))
            if not ok1:
                return
            specs, ok2 = QInputDialog.getText(dialog, "编辑配方", "规格代码 (specsCode):", text=r.get("specsCode", ""))
            if not ok2:
                return
            note, ok3 = QInputDialog.getText(dialog, "编辑配方", "备注（可选）:", text=r.get("note", ""))
            recipes[row] = {
                "name": name.strip(),
                "specsCode": specs.strip(),
                "note": note.strip() if ok3 else ""
            }
            self._save_config()
            refresh_table()
            self._refresh_recipe_combo()

        def on_delete():
            row = get_selected_row()
            if row < 0:
                QMessageBox.warning(dialog, "提示", "请先选择一行")
                return
            recipes = self.config.get("recipes", [])
            if QMessageBox.question(dialog, "确认删除", f"确定删除配方 \"{recipes[row].get('name', '')}\" 吗？") == QMessageBox.Yes:
                del recipes[row]
                self._save_config()
                refresh_table()
                self._refresh_recipe_combo()

        add_btn.clicked.connect(on_add)
        edit_btn.clicked.connect(on_edit)
        del_btn.clicked.connect(on_delete)

        dialog.exec_()
        self._refresh_recipe_combo()

    def _load_config(self):
        """从配置文件加载，不存在则返回默认值"""
        defaults = {
            "orderApiUrl": "http://172.25.57.144:8076/api/OrderInfo/GetOtherOrderInfoByProcess",
            "routeApiUrl": "http://172.25.57.144:8076/api/OrderInfo/GetTechRouteListByCode",
            "singleMaterialApiUrl": "http://172.25.57.144:8076/api/ProduceMessage/MaterialCheckInput",
            "moduleCodeApiUrl": "http://172.25.57.144:8076/api/ProduceMessage/MaterialCheckInput",
            "moduleBindPushUrl": "http://172.25.57.144:8034/api/ProduceMessage/PushMessageToMes",
            "fullMaterialCheckUrl": "http://172.25.57.144:8076/api/ProduceMessage/FullMaterialCheck",
            "packingUploadUrl": "/mes-api/api/Packing/UploadPackingOrder",
            "moduleBindProcessCode": "MODULE_BIND",
            "packingProcessCode": "PACK_MODULE",
            "tenantID": "",
            "DeviceCode": "",
            "UserName": "",
            "UserAccount": "",
            "technicsProcessCode": "",
            "recipes": [],
            "currentRecipe": "",
            "logSavePath": "",
            "s7Config": {
                "enabled": False,
                "ip": "192.168.1.10",
                "rack": 0,
                "slot": 1,
                "pollIntervalMs": 500
            }
        }
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # 合并：文件中的值覆盖默认值，确保新字段也有默认值
                for k, v in defaults.items():
                    loaded.setdefault(k, v)
                return loaded
        except Exception as e:
            print(f"加载配置失败: {e}")
        return defaults

    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def _open_config(self):
        dlg = ConfigDialog(self.config, self)
        if dlg.exec_() == QDialog.Accepted:
            self.config = dlg.get_config()
            self._save_config()
            if self.current_mode == "binding":
                self.process_badge.setText(f"当前工序：{self.config['moduleBindProcessCode']}")
            else:
                self.process_badge.setText(f"当前工序：{self.config['packingProcessCode']}")
            self._add_log("info", "配置已保存")
            self._init_s7_service()
