# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFrame, QStackedWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QPoint
from PyQt5.QtGui import QColor, QBrush, QFont
from datetime import datetime
import json
import requests

from tabs.api_detail_tab import ApiDetailTab
from tabs.log_tab import LogTab
from tabs.api_worker import WorkerThread
from tabs.full_material_tab import FullMaterialTab


class PackingMaterialWorker(QThread):
    """模组入箱工序 - 单物料校验异步工作线程"""
    finished = pyqtSignal(dict, str)  # response_data, scanned_code
    error = pyqtSignal(str, str)  # error_msg, scanned_code
    api_record = pyqtSignal(dict)

    def __init__(self, url, payload, code):
        super().__init__()
        self.url = url
        self.payload = payload
        self.code = code

    def run(self):
        try:
            import time
            from datetime import datetime
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            start = time.time()
            resp = requests.post(self.url, json=self.payload, headers=headers, timeout=30)
            dur = int((time.time() - start) * 1000)
            data = resp.json()
            status = "success" if data.get("code") == 200 else "error"
            self.api_record.emit({
                "title": "单物料校验",
                "status": status,
                "time": datetime.now().strftime("%H:%M:%S"),
                "duration": dur,
                "url": self.url,
                "reqBody": self.payload,
                "resBody": data
            })
            self.finished.emit(data, self.code)
        except Exception as e:
            self.error.emit(str(e), self.code)


class ModulePackingTab(QWidget):
    log = pyqtSignal(str, str)
    api_record = pyqtSignal(dict)
    completed = pyqtSignal(list, dict)  # module_list, order_info
    upload_ready = pyqtSignal(dict)  # 入箱完成，通知主窗口执行统一上传

    def __init__(self, api_tab=None, log_tab=None, parent=None):
        super().__init__(parent)
        self.pack_code = ""
        self.pack_info = None
        self.module_list = []
        self.generated_modules = []  # 绑定流程生成的模块码
        self.pending_modules = []    # 待校验的模块码
        self.material_tasks = []     # 工步物料清单（从workStepMaterialList解析）
        self.check_index = 0         # 当前校验索引
        self.current_status = "idle"
        self.status_message = ""
        self._api_records = []
        self.config = {}
        self.order_info = None
        self.route_steps = []
        self.worker = None
        self.material_worker = None
        # 使用外部传入的或创建自己的实例
        self.api_tab = api_tab or ApiDetailTab()
        self.log_tab = log_tab or LogTab()
        # 内部信号连接：确保 packing 模式自己的记录页面也能显示
        self.log.connect(self._on_local_log)
        self.api_record.connect(self._on_local_api_record)
        self._setup_ui()

    def set_config(self, config):
        self.config = config or {}

    def set_generated_modules(self, records):
        """接收绑定流程生成的模块码记录列表（只在数据变化时记录）"""
        new_records = records or []
        new_codes = [m.get("bindCode", "") for m in new_records if m.get("bindCode")]
        old_codes = [m.get("bindCode", "") for m in self.generated_modules if m.get("bindCode")]
        if new_codes != old_codes:
            self.generated_modules = new_records
            self.log.emit("info", f"[模组入箱] 已接收 {len(new_codes)} 个生成模块码: {new_codes}")
        else:
            self.generated_modules = new_records  # 仍然更新引用，避免外部数据变更后不同步

    def _on_local_log(self, level, msg):
        self.log_tab.add_log(level, msg)

    def _on_local_api_record(self, rec_dict):
        rec_dict.setdefault("time", datetime.now().strftime("%H:%M:%S"))
        rec_dict.setdefault("duration", 120)
        rec_dict.setdefault("expanded", True)
        self._api_records.insert(0, rec_dict)
        self.api_tab.set_records(self._api_records)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部状态栏
        self.header_widget = QWidget()
        self.header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0d1b2a, stop:1 #112240);
                border-bottom: 1px solid rgba(100,181,246,0.15);
            }
        """)
        h_layout = QHBoxLayout(self.header_widget)
        h_layout.setContentsMargins(16, 12, 16, 12)
        h_layout.setSpacing(12)

        self.status_icon = QLabel("📦")
        self.status_icon.setStyleSheet("font-size: 26px;")
        h_layout.addWidget(self.status_icon)

        info_layout = QVBoxLayout()
        self.status_title = QLabel("等待扫描PACK箱")
        self.status_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #e3f2fd;")
        info_layout.addWidget(self.status_title)
        self.status_desc = QLabel("")
        self.status_desc.setStyleSheet("font-size: 13px; color: #78909c; margin-top: 2px;")
        info_layout.addWidget(self.status_desc)
        h_layout.addLayout(info_layout, stretch=1)

        self.pack_stats = QHBoxLayout()
        self.pack_stats.setSpacing(16)
        self.stat_pack = QLabel("PACK: -")
        self.stat_pack.setStyleSheet("font-size: 15px; font-weight: 700; color: #42a5f5; font-family: Consolas, monospace;")
        self.stat_count = QLabel("模组: 0")
        self.stat_count.setStyleSheet("font-size: 15px; font-weight: 700; color: #42a5f5; font-family: Consolas, monospace;")
        self.pack_stats.addWidget(self.stat_pack)
        self.pack_stats.addWidget(self.stat_count)
        h_layout.addLayout(self.pack_stats)
        layout.addWidget(self.header_widget)

        # 标签栏
        tab_bar = QHBoxLayout()
        tab_bar.setContentsMargins(10, 8, 10, 0)
        tab_bar.setSpacing(2)
        tab_bar.setAlignment(Qt.AlignLeft)

        self.tab_buttons = {}
        for text, key in [
            ("① 获取工单", "order"),
            ("② 工步下发", "route"),
            ("③ 单物料校验", "material"),
            ("④ 模组入箱顺序", "packing"),
            ("⑤ 全物料校验", "full_material"),
            ("⑥ 数据上传", "upload"),
            ("📋 记录", "log"),
        ]:
            btn = QPushButton(text)
            btn.setObjectName("tab_btn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(lambda checked, k=key: self._switch_tab(k))
            self.tab_buttons[key] = btn
            tab_bar.addWidget(btn)
        tab_bar.addStretch()
        layout.addLayout(tab_bar)

        # 内容栈
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent; border: none;")

        self.page_order = self._create_page_order()
        self.stack.addWidget(self.page_order)

        self.page_route = self._create_page_route()
        self.stack.addWidget(self.page_route)

        self.page_material = self._create_page_material()
        self.stack.addWidget(self.page_material)

        self.page_packing = self._create_page_packing()
        self.stack.addWidget(self.page_packing)

        # page 4: 全物料校验
        self.full_material_tab = FullMaterialTab()
        self.full_material_tab.log.connect(self.log.emit)
        self.full_material_tab.api_record.connect(self.api_record.emit)
        self.full_material_tab.complete.connect(self._on_full_material_done)
        self.stack.addWidget(self.full_material_tab)

        self.page_upload = self._create_page_upload()
        self.stack.addWidget(self.page_upload)

        # page 6: 记录（复用外部传入的 api_tab 和 log_tab）
        log_page = self._create_log_page()
        self.stack.addWidget(log_page)

        layout.addWidget(self.stack, stretch=1)

        self._switch_tab("order")
        self._update_header_style()
        # 确保输入框初始可用
        self.pack_input.setEnabled(True)

    # =====================================================================
    #  5个标签页
    # =====================================================================
    def _create_page_order(self):
        """① 获取工单：PACK箱扫描"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        cl = QVBoxLayout(card)
        cl.setSpacing(12)

        title = QLabel("📦 PACK箱条码（PLC自动获取）")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9;")
        cl.addWidget(title)

        input_wrap = QHBoxLayout()
        input_wrap.setSpacing(8)
        self.pack_input = QLineEdit()
        self.pack_input.setPlaceholderText("等待PLC自动获取箱体码...")
        self.pack_input.setReadOnly(True)
        input_wrap.addWidget(self.pack_input, stretch=1)
        cl.addLayout(input_wrap)

        self.pack_detail = QVBoxLayout()
        self.pack_detail.setSpacing(6)
        cl.addLayout(self.pack_detail)

        cl.addStretch()
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _create_page_route(self):
        """② 工步下发：PACK详情 + 模组统计"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        stat_card = QFrame()
        stat_card.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        sl = QVBoxLayout(stat_card)
        st = QLabel("📊 模组统计")
        st.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9;")
        sl.addWidget(st)
        self.route_stat_label = QLabel("等待获取PACK信息...")
        self.route_stat_label.setStyleSheet("color: #78909c; font-size: 14px; padding: 8px 0;")
        sl.addWidget(self.route_stat_label)
        sl.addStretch()
        layout.addWidget(stat_card)

        # 工步表格
        step_card = QFrame()
        step_card.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        stl = QVBoxLayout(step_card)
        stl.setSpacing(10)
        st_title = QLabel("📋 工步列表")
        st_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9;")
        stl.addWidget(st_title)

        self.route_step_table = QTableWidget()
        self.route_step_table.setColumnCount(3)
        self.route_step_table.setHorizontalHeaderLabels(["序号", "工步编码", "工步名称"])
        self.route_step_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.route_step_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.route_step_table.setColumnWidth(0, 70)
        self.route_step_table.verticalHeader().setVisible(False)
        self.route_step_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.route_step_table.setShowGrid(False)
        for i in range(3):
            item = self.route_step_table.horizontalHeaderItem(i)
            if item:
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                item.setForeground(QBrush(QColor("#90caf9")))
                item.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.route_step_table.setStyleSheet("""
            QTableWidget { background: transparent; border: none; font-size: 14px; }
            QTableWidget::item { color: #cfd8dc; padding: 8px 12px; border-bottom: 1px solid rgba(100,181,246,0.05); }
            QHeaderView::section { background: rgba(21,101,192,0.2); color: #90caf9; font-weight: 700; font-size: 12px; padding: 6px 12px; min-height: 28px; border: none; border-bottom: 1px solid rgba(100,181,246,0.1); }
        """)
        stl.addWidget(self.route_step_table)
        stl.addStretch()
        layout.addWidget(step_card, stretch=1)
        return page

    def _create_page_material(self):
        """③ 单物料校验：扫描模块码逐个校验"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # 扫描输入区
        scan_card = QFrame()
        scan_card.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        scl = QVBoxLayout(scan_card)
        scl.setSpacing(10)
        title = QLabel("📷 扫描模块码")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9;")
        scl.addWidget(title)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self.material_scan_input = QLineEdit()
        self.material_scan_input.setPlaceholderText("请扫描模块码...")
        self.material_scan_input.returnPressed.connect(self._handle_material_scan)
        self.material_scan_input.setStyleSheet("""
            QLineEdit {
                background: #0a0e1a; border: 1px solid rgba(100,181,246,0.2);
                border-radius: 6px; color: #e3f2fd; padding: 8px 12px;
                font-family: Consolas; font-size: 15px;
            }
            QLineEdit:focus { border-color: #42a5f5; }
        """)
        self.material_scan_btn = QPushButton("校验")
        self.material_scan_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1565c0, stop:1 #0d47a1);
                border: none; border-radius: 6px; color: #e3f2fd;
                padding: 7px 16px; font-size: 14px; font-weight: 600;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976d2, stop:1 #1565c0); }
            QPushButton:disabled { opacity: 0.4; }
        """)
        self.material_scan_btn.clicked.connect(self._handle_material_scan)
        input_row.addWidget(self.material_scan_input, stretch=1)
        input_row.addWidget(self.material_scan_btn)
        scl.addLayout(input_row)

        self.material_status_label = QLabel("请先获取工单，再进行单物料校验")
        self.material_status_label.setStyleSheet("font-size: 14px; color: #78909c;")
        scl.addWidget(self.material_status_label)
        scl.addStretch()
        layout.addWidget(scan_card)

        # 已校验列表
        list_card = QFrame()
        list_card.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        lcl = QVBoxLayout(list_card)
        lcl.setSpacing(10)
        list_header = QHBoxLayout()
        list_header.setSpacing(8)
        lt = QLabel("📋 已校验模块码")
        lt.setStyleSheet("font-size: 15px; font-weight: 600; color: #90caf9;")
        list_header.addWidget(lt)
        list_header.addStretch()
        self.list_count = QLabel("共 0 个")
        self.list_count.setStyleSheet("font-size: 13px; color: #546e7a;")
        list_header.addWidget(self.list_count)
        lcl.addLayout(list_header)

        self.material_table = QTableWidget()
        self.material_table.setColumnCount(6)
        headers = ["序号", "物料编号", "物料名称", "需求数", "状态", "已匹配条码"]
        self.material_table.setHorizontalHeaderLabels(headers)
        self.material_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.material_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.material_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.material_table.setColumnWidth(0, 60)
        self.material_table.setColumnWidth(3, 70)
        self.material_table.verticalHeader().setVisible(False)
        self.material_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.material_table.setShowGrid(False)
        # 通过代码直接设置表头项样式（绕过 QSS 不生效问题）
        for i, text in enumerate(headers):
            item = self.material_table.horizontalHeaderItem(i)
            if item:
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                item.setForeground(QBrush(QColor("#90caf9")))
                item.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.material_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background: rgba(21,101,192,0.25);
                color: #90caf9;
                font-weight: 700;
                font-size: 12px;
                padding: 6px 12px;
                min-height: 28px;
                border: none;
                border-bottom: 1px solid rgba(100,181,246,0.2);
            }
        """)
        self.material_table.setStyleSheet("""
            QTableWidget { background: transparent; border: none; font-size: 14px; }
            QTableWidget::item { padding: 8px 12px; border-bottom: 1px solid rgba(100,181,246,0.05); }
        """)
        lcl.addWidget(self.material_table)
        lcl.addStretch()
        layout.addWidget(list_card, stretch=1)
        return page

    def _create_page_packing(self):
        """④ 模组入箱顺序：单物料校验通过后直接上传"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # 入箱顺序表格
        table_card = QFrame()
        table_card.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        tbl = QVBoxLayout(table_card)
        tbl.setSpacing(10)
        ttitle = QLabel("📋 模组入箱顺序")
        ttitle.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9;")
        tbl.addWidget(ttitle)

        self.packing_table = QTableWidget()
        self.packing_table.setColumnCount(3)
        self.packing_table.setHorizontalHeaderLabels(["入箱顺序", "模块码", "状态"])
        self.packing_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.packing_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.packing_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.packing_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.packing_table.verticalHeader().setVisible(False)
        self.packing_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.packing_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.packing_table.setSelectionMode(QTableWidget.SingleSelection)
        self.packing_table.setStyleSheet("""
            QTableWidget {
                background: #0d1320;
                border: 1px solid rgba(100,181,246,0.1);
                border-radius: 6px;
                gridline-color: rgba(100,181,246,0.05);
            }
            QHeaderView::section {
                background: #0d1b2a;
                color: #90caf9;
                padding: 6px;
                border: none;
                font-weight: 600;
            }
            QTableWidget::item {
                color: #cfd8dc;
                padding: 6px;
                border-bottom: 1px solid rgba(100,181,246,0.05);
            }
            QTableWidget::item:selected {
                background: rgba(100,181,246,0.12);
            }
        """)
        tbl.addWidget(self.packing_table)
        layout.addWidget(table_card, stretch=1)
        return page

    def _create_page_upload(self):
        """⑤ 数据上传：上传结果"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        result_card = QFrame()
        result_card.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        rl = QVBoxLayout(result_card)
        rl.setSpacing(10)
        title = QLabel("📤 数据上传结果")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9;")
        rl.addWidget(title)

        self.upload_result_label = QLabel("等待执行入箱操作...")
        self.upload_result_label.setAlignment(Qt.AlignCenter)
        self.upload_result_label.setStyleSheet("color: #78909c; font-size: 14px; padding: 20px;")
        rl.addWidget(self.upload_result_label)
        rl.addStretch()
        layout.addWidget(result_card)
        layout.addStretch()
        return page

    def _create_log_page(self):
        """📋 记录：接口交互 + 操作日志"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        if self.api_tab:
            api_widget = QWidget()
            api_widget.setStyleSheet("background: #131929; border: 1px solid rgba(100,181,246,0.12); border-radius: 10px;")
            api_layout = QVBoxLayout(api_widget)
            api_layout.setContentsMargins(10, 10, 10, 10)
            api_header = QLabel("🔌 接口交互")
            api_header.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9;")
            api_layout.addWidget(api_header)
            api_layout.addWidget(self.api_tab)
            layout.addWidget(api_widget, stretch=1)

        if self.log_tab:
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

    # =====================================================================
    #  标签切换
    # =====================================================================
    def _switch_tab(self, key):
        index_map = {"order": 0, "route": 1, "material": 2, "packing": 3, "full_material": 4, "upload": 5, "log": 6}
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
    #  业务逻辑
    # =====================================================================
    def _handle_pack_scan(self):
        code = self.pack_input.text().strip()
        if not code:
            return

        url = self.config.get("orderApiUrl", "").strip()
        route_url = self.config.get("routeApiUrl", "").strip()
        process_code = self.config.get("packingProcessCode", "").strip()

        if not url or not route_url:
            self._show_order_error("未配置获取工单/工步下发接口地址，请在系统配置中设置")
            return
        if not process_code:
            self._show_order_error("未配置模组入箱工序代码(packingProcessCode)，请在系统配置中设置")
            return

        self.pack_code = code
        self.current_status = "scanning_pack"
        self.status_message = "正在获取MES参数及模组清单..."
        self.log.emit("info", f"[模组入箱] 扫描条码: {code}")
        self._update_header_style()
        self.pack_input.setEnabled(False)
        self._clear_order_error()

        payload = {
            "technicsProcessCode": process_code,
            "productCode": code
        }
        self.log.emit("info", f"[模组入箱] 获取工单 POST {url}")
        self.log.emit("info", f"[模组入箱] 参数: {json.dumps(payload, ensure_ascii=False)}")

        self.worker = WorkerThread(url, payload, route_url, process_code)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.error.connect(self._on_worker_error)
        self.worker.api_record.connect(self.api_record.emit)
        self.worker.start()

    def _on_worker_finished(self, order_data, route_data, order_info):
        self.pack_input.setEnabled(True)
        self.worker = None

        self.order_info = order_info

        # 记录 API
        self.api_record.emit({
            "title": "获取工单(模组入箱)",
            "url": self.config.get("orderApiUrl", ""),
            "status": "success",
            "time": datetime.now().strftime("%H:%M:%S"),
            "reqBody": {"technicsProcessCode": self.config.get("packingProcessCode", ""), "productCode": self.pack_code},
            "resBody": order_data
        })
        self.api_record.emit({
            "title": "工步下发(模组入箱)",
            "url": self.config.get("routeApiUrl", ""),
            "status": "success",
            "time": datetime.now().strftime("%H:%M:%S"),
            "reqBody": {"routeCode": order_info.get("routeCode") or order_info.get("route_No", ""), "workSeqNo": self.config.get("packingProcessCode", "")},
            "resBody": route_data
        })

        # 解析工单信息
        order_code = order_info.get("orderCode") or order_info.get("order_Code", "")
        route_no = order_info.get("routeCode") or order_info.get("route_No", "")
        product_name = order_info.get("productName") or order_info.get("product_Name", "")
        product_property = order_info.get("productProperty") or order_info.get("product_Property", "")

        self.pack_info = {
            "packCode": self.pack_code,
            "orderCode": order_code,
            "routeNo": route_no,
            "moduleType": product_name or "-",
            "expectedModuleCount": 0,
        }

        # 解析工步数据
        steps = []
        if isinstance(route_data, dict):
            d = route_data.get("datas") or route_data.get("data", {})
            if isinstance(d, dict):
                steps = d.get("workStepList", []) or d.get("workSeqList", [])
            elif isinstance(d, list) and len(d) > 0:
                first = d[0]
                if isinstance(first, dict):
                    steps = first.get("workStepList", []) or first.get("workSeqList", [])
        self.route_steps = steps

        # 解析工步物料清单，构建 material_tasks
        self.material_tasks = []
        uid = 0
        for step in steps:
            if not isinstance(step, dict):
                continue
            ws_list = step.get("workStepList", []) or []
            for ws in ws_list:
                mats = ws.get("workStepMaterialList", []) or []
                for mat in mats:
                    req_num = int(mat.get("material_number") or 0)
                    mno = str(mat.get("material_No") or "").strip()
                    mname = str(mat.get("material_Name", ""))
                    if not mno or req_num <= 0:
                        continue
                    is_module = "国标码" in mname
                    for idx in range(req_num):
                        self.material_tasks.append({
                            "uid": f"mat-{uid}-{idx}",
                            "material_No": mno,
                            "material_Name": mname,
                            "material_number": 1,
                            "scannedBarcode": "",
                            "status": "completed" if is_module else "pending",
                            "isModuleCode": is_module,
                        })
                    uid += 1

        # 为所有物料尝试填入生成的 bindCode（如果物料编号有对应绑定码）
        bind_code_map = {}
        for rec in self.generated_modules:
            mno = rec.get("materialNo", "")
            bcode = rec.get("bindCode", "")
            if mno and bcode:
                bind_code_map[mno] = bcode

        for task in self.material_tasks:
            mno = task["material_No"]
            if mno in bind_code_map:
                task["scannedBarcode"] = bind_code_map[mno]
            elif task.get("isModuleCode"):
                task["scannedBarcode"] = mno  # 兜底：使用物料编号

        self._refresh_material_table()

        # 初始化空的模组列表（等待物料校验时逐个添加）
        self.module_list = []

        # 如果有生成的模块码，自动开始单物料校验（生成多少个就校验多少个）
        if self.generated_modules:
            self.pending_modules = [m.get("bindCode", "").upper() for m in self.generated_modules if m.get("bindCode")]
            self.check_index = 0
            self.module_list = []
            self.current_status = "auto_checking"
            self.status_message = f"工单获取成功，开始自动校验 {len(self.pending_modules)} 个模块码"
            self.log.emit("info", f"[模组入箱] 使用生成的模块码进行自动单物料校验，共 {len(self.pending_modules)} 个: {self.pending_modules}")
            self._refresh_ui()
            self._switch_tab("material")
            self._check_next_module()
        else:
            self.current_status = "ready"
            self.status_message = f"工单获取成功: {order_code}，请进行单物料校验"
            self.log.emit("success", f"[模组入箱] 获取工单成功: {order_code}, 工艺路线: {route_no}")
            if steps:
                self.log.emit("info", f"[模组入箱] 工步下发成功，共 {len(steps)} 个工步")
            self._refresh_ui()
            self._switch_tab("route")

    def _on_worker_error(self, msg):
        self.pack_input.setEnabled(True)
        self.worker = None
        self._show_order_error(msg)
        self.log.emit("error", f"[模组入箱] {msg}")

    def _show_order_error(self, msg):
        self.current_status = "idle"
        self.status_message = ""
        self._update_header_style()
        while self.pack_detail.count():
            item = self.pack_detail.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        error_card = QFrame()
        error_card.setStyleSheet("""
            QFrame {
                background: rgba(244,67,54,0.08);
                border: 1px solid rgba(244,67,54,0.2);
                border-radius: 8px;
                padding: 12px;
            }
        """)
        el = QVBoxLayout(error_card)
        el.setSpacing(6)
        title = QLabel("❌ 获取失败")
        title.setStyleSheet("color: #f44336; font-size: 15px; font-weight: 700;")
        el.addWidget(title)
        detail = QLabel(msg)
        detail.setStyleSheet("color: #ef9a9a; font-size: 13px;")
        detail.setWordWrap(True)
        el.addWidget(detail)
        self.pack_detail.addWidget(error_card)
        self.pack_detail.addStretch()

    def _clear_order_error(self):
        while self.pack_detail.count():
            item = self.pack_detail.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _handle_material_scan(self):
        code = self.material_scan_input.text().strip().upper()
        if not code:
            return

        url = self.config.get("singleMaterialApiUrl", "").strip()
        if not url:
            self.material_status_label.setText("❌ 未配置单物料校验接口地址")
            self.material_status_label.setStyleSheet("font-size: 14px; color: #f44336;")
            return
        if not self.order_info:
            self.material_status_label.setText("❌ 请先获取工单")
            self.material_status_label.setStyleSheet("font-size: 14px; color: #f44336;")
            return

        # 白名单校验：扫描码必须在绑定流程生成的模块码列表中
        allowed_codes = [m.get("bindCode", "").upper() for m in self.generated_modules if m.get("bindCode")]
        if allowed_codes and code not in allowed_codes:
            self.material_status_label.setText(f"❌ 条码 {code} 不在已生成模块码列表中")
            self.material_status_label.setStyleSheet("font-size: 14px; color: #f44336;")
            self.log.emit("error", f"[模组入箱-物料校验] 条码 {code} 不在已生成模块码列表中，允许列表: {allowed_codes}")
            self._show_alert("校验失败", f"条码 {code} 不在允许入箱的模块码列表中")
            self.material_scan_input.clear()
            self.material_scan_input.setFocus()
            return

        # 去重检查
        for m in self.module_list:
            if m["moduleCode"] == code:
                self.material_status_label.setText(f"⚠️ 模块码 {code} 已校验过")
                self.material_status_label.setStyleSheet("font-size: 14px; color: #ffab40;")
                self.material_scan_input.clear()
                self.material_scan_input.setFocus()
                return

        self.material_scan_input.setEnabled(False)
        self.material_scan_btn.setEnabled(False)
        self.material_status_label.setText(f"正在校验 {code} ...")
        self.material_status_label.setStyleSheet("font-size: 14px; color: #ffab40;")
        self.log.emit("info", f"[模组入箱-物料校验] 扫描: {code}")

        payload = {
            "produceOrderCode": self.order_info.get("orderCode", ""),
            "routeNo": self.order_info.get("routeCode") or self.order_info.get("route_No", ""),
            "technicsProcessCode": self.config.get("packingProcessCode", ""),
            "materialCode": code,
            "tenantID": self.config.get("tenantID", "")
        }

        self.material_worker = PackingMaterialWorker(url, payload, code)
        self.material_worker.finished.connect(self._on_material_check_finished)
        self.material_worker.error.connect(self._on_material_check_error)
        self.material_worker.api_record.connect(self.api_record.emit)
        self.material_worker.start()

    def _check_next_module(self):
        """自动校验下一个模块码"""
        if self.check_index >= len(self.pending_modules):
            # 全部校验通过，进入全物料校验
            self.material_status_label.setText(f"✅ 全部 {len(self.module_list)} 个模块码校验通过")
            self.material_status_label.setStyleSheet("font-size: 14px; color: #00e676;")
            self.log.emit("success", "[模组入箱] 所有模块码自动校验通过，进入全物料校验")
            self.current_status = "full_checking"
            self.status_message = "全部模块码校验通过，进入全物料校验..."
            self._update_header_style()
            self._refresh_ui()
            # 内部触发全物料校验
            self.full_material_tab.set_config(self.config)
            self.full_material_tab.set_order_info(self.order_info)
            self.full_material_tab.set_packing_data(self.module_list, self.pack_code)
            self._switch_tab("full_material")
            return

        code = self.pending_modules[self.check_index]
        self.check_index += 1
        self.material_status_label.setText(f"⏳ 正在校验 ({self.check_index}/{len(self.pending_modules)}): {code}")
        self.material_status_label.setStyleSheet("font-size: 14px; color: #ffab40;")
        self._do_material_check(code)

    def _do_material_check(self, code):
        """执行单个模块码的单物料校验"""
        if not self.order_info:
            return
        url = self.config.get("singleMaterialApiUrl", "").strip()
        if not url:
            self.log.emit("error", "[模组入箱] 未配置单物料校验接口")
            return

        payload = {
            "produceOrderCode": self.order_info.get("orderCode", ""),
            "routeNo": self.order_info.get("routeCode") or self.order_info.get("route_No", ""),
            "technicsProcessCode": self.config.get("packingProcessCode", ""),
            "materialCode": code,
            "tenantID": self.config.get("tenantID", "")
        }

        self.log.emit("info", f"[单物料校验] POST {url}")
        self.log.emit("info", f"[单物料校验] 参数: {json.dumps(payload, ensure_ascii=False)}")

        self.material_worker = PackingMaterialWorker(url, payload, code)
        self.material_worker.finished.connect(self._on_material_check_finished)
        self.material_worker.error.connect(self._on_material_check_error)
        self.material_worker.api_record.connect(self.api_record.emit)
        self.material_worker.start()

    def _on_material_check_finished(self, data, code):
        self.material_worker = None

        # 记录 API
        self.api_record.emit({
            "title": "单物料校验(模组入箱)",
            "url": self.config.get("singleMaterialApiUrl", ""),
            "status": "success" if data.get("code") == 200 else "error",
            "time": datetime.now().strftime("%H:%M:%S"),
            "reqBody": {
                "produceOrderCode": self.order_info.get("orderCode", ""),
                "routeNo": self.order_info.get("routeCode") or self.order_info.get("route_No", ""),
                "technicsProcessCode": self.config.get("packingProcessCode", ""),
                "materialCode": code,
                "tenantID": self.config.get("tenantID", "")
            },
            "resBody": data
        })

        if data.get("code") != 200:
            msg = data.get("message", "未知错误")
            self.material_status_label.setText(f"❌ {code} 校验失败: {msg}")
            self.material_status_label.setStyleSheet("font-size: 14px; color: #f44336;")
            self.log.emit("error", f"[模组入箱-物料校验] {code} 失败: {msg}")
            # 失败也继续下一个（或者停止？根据需求，这里继续）
            self._check_next_module()
            return

        self.module_list.append({
            "moduleCode": code,
            "scanOrder": len(self.module_list) + 1,
            "scanTime": datetime.now().strftime("%H:%M:%S"),
            "logicCheckResult": "pending",
            "mesCheckResult": "pending",
            "isPacked": False
        })

        # 同步更新 material_tasks 中对应行的状态
        for task in self.material_tasks:
            if task.get("scannedBarcode", "").upper() == code or task.get("material_No", "").upper() == code:
                task["status"] = "completed"
                task["scannedBarcode"] = code
                break

        self.material_status_label.setText(f"✅ {code} 校验通过 ({self.check_index}/{len(self.pending_modules)})")
        self.material_status_label.setStyleSheet("font-size: 14px; color: #00e676;")
        self.log.emit("success", f"[模组入箱-物料校验] {code} 通过")
        self._refresh_material_table()
        self._refresh_packing_table()
        # 继续下一个
        self._check_next_module()

    def _on_material_check_error(self, msg, code):
        self.material_scan_input.setEnabled(True)
        self.material_scan_btn.setEnabled(True)
        self.material_scan_input.clear()
        self.material_scan_input.setFocus()
        self.material_worker = None
        self.material_status_label.setText(f"❌ {code} 网络异常: {msg}")
        self.material_status_label.setStyleSheet("font-size: 14px; color: #f44336;")
        self.log.emit("error", f"[模组入箱-物料校验] {code} 异常: {msg}")

    def _refresh_material_table(self):
        """展示工步物料清单（含物料编号、物料名称、需求数、状态、已匹配条码）"""
        tasks = self.material_tasks
        self.material_table.setRowCount(len(tasks))
        for i, task in enumerate(tasks):
            # 序号
            item = QTableWidgetItem(str(i + 1))
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.ForegroundRole, QColor("#90caf9"))
            self.material_table.setItem(i, 0, item)

            # 物料编号
            item = QTableWidgetItem(task["material_No"])
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.ForegroundRole, QColor("#64b5f6"))
            item.setFont(QFont("Consolas", 11))
            self.material_table.setItem(i, 1, item)

            # 物料名称
            item = QTableWidgetItem(task["material_Name"])
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.ForegroundRole, QColor("#e0e6ed"))
            item.setToolTip(task["material_Name"])
            self.material_table.setItem(i, 2, item)

            # 需求数
            item = QTableWidgetItem(str(task["material_number"]))
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.ForegroundRole, QColor("#90caf9"))
            item.setFont(QFont("Consolas", 11, QFont.Bold))
            self.material_table.setItem(i, 3, item)

            # 状态
            if task.get("isModuleCode"):
                item = QTableWidgetItem("无需校验")
                item.setData(Qt.ForegroundRole, QColor("#42a5f5"))
            elif task["status"] == "completed":
                item = QTableWidgetItem("通过")
                item.setData(Qt.ForegroundRole, QColor("#00e676"))
            else:
                item = QTableWidgetItem("待校验")
                item.setData(Qt.ForegroundRole, QColor("#ffab40"))
            item.setTextAlignment(Qt.AlignCenter)
            self.material_table.setItem(i, 4, item)

            # 已匹配条码
            item = QTableWidgetItem(task.get("scannedBarcode", ""))
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.ForegroundRole, QColor("#80cbc4"))
            item.setFont(QFont("Consolas", 10))
            self.material_table.setItem(i, 5, item)

        self.list_count.setText(f"共 <strong style='color:#42a5f5;'>{len(tasks)}</strong> 个")

    def _refresh_packing_table(self):
        """刷新模组入箱顺序表格"""
        self.packing_table.setRowCount(len(self.module_list))
        for i, m in enumerate(self.module_list):
            item = QTableWidgetItem(str(m.get("scanOrder", i + 1)))
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QBrush(QColor("#90caf9")))
            self.packing_table.setItem(i, 0, item)

            item = QTableWidgetItem(m["moduleCode"])
            item.setForeground(QBrush(QColor("#64b5f6")))
            item.setFont(QFont("Consolas", 11))
            self.packing_table.setItem(i, 1, item)

            status = "已入箱" if m.get("isPacked") else "待入箱"
            color = "#00e676" if m.get("isPacked") else "#ffab40"
            item = QTableWidgetItem(status)
            item.setForeground(QBrush(QColor(color)))
            item.setTextAlignment(Qt.AlignCenter)
            self.packing_table.setItem(i, 2, item)

    def _on_full_material_done(self):
        """全物料校验通过后的回调"""
        self.log.emit("info", "[模组入箱] 全物料校验通过，开始上传")
        self.finish_upload()

    def finish_upload(self):
        """全物料校验通过后调用，通知主窗口执行统一上传（绑定数据+入箱位置）"""
        self.current_status = "uploading"
        self.status_message = "正在准备上传数据..."
        self.log.emit("info", "[模组入箱] 入箱完成，准备通知主窗口执行统一上传")
        self._update_header_style()
        for m in self.module_list:
            m["isPacked"] = True
        self._refresh_packing_table()
        self.current_status = "completed"
        self.status_message = "入箱完成，数据已提交上传！"
        self.log.emit("success", "[模组入箱] 入箱完成，数据已提交上传！")
        self._refresh_ui()
        self._switch_tab("upload")

        # 发射信号，由主窗口统一执行两个上传接口
        packing_data = {
            "pack_code": self.pack_code,
            "module_list": self.module_list,
            "order_info": self.order_info,
        }
        self.upload_ready.emit(packing_data)

    def set_pack_code(self, code):
        """由外部（如PLC信号）设置箱体码并准备获取工单"""
        self.pack_input.setText(code)

    def _reset_all(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(1000)
        if self.material_worker and self.material_worker.isRunning():
            self.material_worker.terminate()
            self.material_worker.wait(1000)
        self.pack_code = ""
        self.pack_info = None
        self.module_list = []
        self.material_tasks = []
        self.order_info = None
        self.route_steps = []
        self.current_status = "idle"
        self.status_message = ""
        self.pack_input.clear()
        self.pack_input.setEnabled(True)
        self.material_scan_input.clear()
        self.material_scan_input.setEnabled(True)
        self.material_scan_btn.setEnabled(True)
        self.material_status_label.setText("请先获取工单，再进行单物料校验")
        self.material_status_label.setStyleSheet("font-size: 14px; color: #78909c;")
        self.material_table.setRowCount(0)
        self.packing_table.setRowCount(0)
        self.route_step_table.setRowCount(0)
        self.list_count.setText("共 0 个")
        self._clear_order_error()
        self.log.emit("info", "模组入箱流程已复位")
        self._refresh_ui()
        self._switch_tab("order")

    def _refresh_ui(self):
        self._update_header_style()

        # 更新PACK详情（获取工单页）
        while self.pack_detail.count():
            item = self.pack_detail.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.pack_info:
            self.pack_input.setEnabled(False)
            for label, key in [("工单号", "orderCode"), ("工艺路线", "routeNo"), ("模组类型", "moduleType"), ("MES下发模组", "expectedModuleCount")]:
                row = QHBoxLayout()
                row.setSpacing(8)
                l = QLabel(label)
                l.setStyleSheet("color: #546e7a; font-size: 13px;")
                v = QLabel(str(self.pack_info.get(key, "-")))
                v.setStyleSheet("color: #cfd8dc; font-size: 14px; font-family: Consolas, monospace;")
                if key == "moduleType":
                    v.setStyleSheet("color: #42a5f5; font-size: 14px; font-weight: 600;")
                row.addWidget(l)
                row.addStretch()
                row.addWidget(v)
                w = QWidget()
                w.setLayout(row)
                w.setStyleSheet("background: rgba(21,101,192,0.06); border-radius: 4px; padding: 4px 8px;")
                self.pack_detail.addWidget(w)

        # 更新模组统计
        if self.pack_info:
            self.route_stat_label.setText(f"PACK: {self.pack_code}  |  模组总数: {len(self.module_list)}  |  已入箱: {sum(1 for m in self.module_list if m['isPacked'])}")
        else:
            self.route_stat_label.setText("等待获取PACK信息...")
            self.pack_input.setEnabled(True)

        # 更新工步表格
        steps = getattr(self, "route_steps", [])
        self.route_step_table.setRowCount(len(steps))
        for i, step in enumerate(steps):
            if isinstance(step, dict):
                # 兼容多种字段命名：workstepNo/workseqNo/workSeqNo
                no = str(step.get("workstepNo") or step.get("workseqNo") or step.get("workSeqNo") or (i + 1))
                name = str(step.get("workstepName") or step.get("workseqName") or step.get("workSeqName") or "")
            else:
                no = str(i + 1)
                name = str(step)
            item = QTableWidgetItem(str(i + 1))
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.ForegroundRole, QColor("#90caf9"))
            self.route_step_table.setItem(i, 0, item)

            item = QTableWidgetItem(no)
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.ForegroundRole, QColor("#64b5f6"))
            item.setFont(QFont("Consolas", 11))
            self.route_step_table.setItem(i, 1, item)

            item = QTableWidgetItem(name)
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.ForegroundRole, QColor("#cfd8dc"))
            self.route_step_table.setItem(i, 2, item)

        # 统计
        self.stat_pack.setText(f"PACK: {self.pack_code or '-'}")
        self.stat_count.setText(f"模组: {len(self.module_list)}")

        # 单物料校验页 - 刷新表格
        self._refresh_material_table()

        # 数据上传页结果
        if self.current_status == "completed":
            self.upload_result_label.setText(f"✅ 入箱顺序上传成功！\n共 {len(self.module_list)} 个模组已入箱")
            self.upload_result_label.setStyleSheet("color: #00e676; font-size: 15px; font-weight: 600; padding: 20px;")
        elif self.current_status == "failed":
            self.upload_result_label.setText(f"❌ 入箱失败\n{self.status_message}")
            self.upload_result_label.setStyleSheet("color: #f44336; font-size: 15px; font-weight: 600; padding: 20px;")
        elif self.current_status == "uploading":
            self.upload_result_label.setText("⏳ 正在上传入箱顺序到MES...")
            self.upload_result_label.setStyleSheet("color: #ffab40; font-size: 15px; font-weight: 600; padding: 20px;")
        else:
            self.upload_result_label.setText("等待执行入箱操作...")
            self.upload_result_label.setStyleSheet("color: #78909c; font-size: 14px; padding: 20px;")

    def _update_header_style(self):
        s = self.current_status
        styles = {
            "idle": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0d1b2a, stop:1 #112240);",
            "scanning_pack": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a237e, stop:1 #283593);",
            "ready": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0d1b2a, stop:1 #112240);",

            "uploading": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a237e, stop:1 #283593);",
            "completed": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0d3328, stop:1 #1b5e20);",
            "failed": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3e0e0e, stop:1 #5c1212);",
        }
        border = {
            "completed": "rgba(0,230,118,0.2)",
            "failed": "rgba(244,67,54,0.2)",

        }.get(s, "rgba(100,181,246,0.15)")
        self.header_widget.setStyleSheet(f"""
            QWidget {{
                background: {styles.get(s, styles['idle'])};
                border-bottom: 1px solid {border};
            }}
        """)

        titles = {
            "idle": "等待扫描PACK箱",
            "scanning_pack": "正在获取MES参数...",
            "ready": "已获取模组清单，等待单物料校验",
            "uploading": "正在上传...",
            "completed": "入箱完成",
            "failed": "入箱失败",
        }
        icons = {
            "idle": "📦", "scanning_pack": "⏳", "ready": "📋",
            "uploading": "⏳",
            "completed": "✅", "failed": "❌",
        }
        self.status_title.setText(titles.get(s, "未知"))
        self.status_icon.setText(icons.get(s, "📦"))
        self.status_desc.setText(self.status_message)
