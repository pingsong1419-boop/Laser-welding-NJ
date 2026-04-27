# -*- coding: utf-8 -*-
"""PLC 读写调试助手模块 —— 极简一键式寄存器控制界面"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox, QComboBox, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from datetime import datetime

class PlcMonitorTab(QWidget):
    log = pyqtSignal(str, str)
    config_changed = pyqtSignal()

    def __init__(self, s7_service, config, parent=None):
        super().__init__(parent)
        self.s7_service = s7_service
        self.config = config or {}
        self._setup_ui()
        
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._check_status)
        self._refresh_timer.start(1000)

    def set_config(self, config):
        self.config = config or {}

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # 1. 顶部状态栏
        status_card = QFrame()
        status_card.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        sc = QHBoxLayout(status_card)
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("font-size: 22px; color: #ff5252;")
        sc.addWidget(self.status_dot)

        info = QVBoxLayout()
        self.status_text = QLabel("未连接")
        self.status_text.setStyleSheet("font-size: 16px; font-weight: 700; color: #e3f2fd;")
        info.addWidget(self.status_text)
        self.status_detail = QLabel("--")
        self.status_detail.setStyleSheet("font-size: 13px; color: #78909c;")
        info.addWidget(self.status_detail)
        sc.addLayout(info)
        sc.addStretch()
        layout.addWidget(status_card)

        # 2. 读写大区域并排
        rw_layout = QHBoxLayout()
        rw_layout.setSpacing(16)

        # ==================== A. 读取操作面板 ====================
        read_card = QFrame()
        read_card.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 20px;
            }
            QLabel { color: #90caf9; font-size: 15px; font-weight: 600; }
            QLineEdit {
                background: #0d1117;
                border: 1px solid rgba(100, 181, 246, 0.4);
                border-radius: 6px;
                color: #e3f2fd;
                padding: 8px 12px;
                font-size: 15px;
            }
            QLineEdit:focus { border-color: #42a5f5; }
            QComboBox {
                background: #0d1117;
                border: 1px solid rgba(100, 181, 246, 0.4);
                border-radius: 6px;
                color: #e3f2fd;
                padding: 8px;
                font-size: 14px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1565c0, stop:1 #0d47a1);
                border-radius: 6px; color: #e3f2fd; padding: 12px; font-size: 15px; font-weight: 700;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976d2, stop:1 #1565c0); }
        """)
        rc_layout = QVBoxLayout(read_card)
        rc_layout.setSpacing(12)

        rt_lbl = QLabel("🔍 PLC 数据读取")
        rt_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #42a5f5;")
        rc_layout.addWidget(rt_lbl)

        # 输入格栅
        r_grid = QGridLayout()
        r_grid.setSpacing(10)

        r_grid.addWidget(QLabel("DB块 (DB):"), 0, 0)
        self.r_db = QLineEdit(); self.r_db.setText("1")
        r_grid.addWidget(self.r_db, 0, 1)

        r_grid.addWidget(QLabel("偏移量 (Offset):"), 1, 0)
        self.r_offset = QLineEdit(); self.r_offset.setText("0")
        r_grid.addWidget(self.r_offset, 1, 1)

        r_grid.addWidget(QLabel("数据类型:"), 2, 0)
        self.r_type = QComboBox()
        self.r_type.addItems(["Bool", "SInt", "Int", "DInt", "Real", "String"])
        r_grid.addWidget(self.r_type, 2, 1)

        r_grid.addWidget(QLabel("位号 (Bool必填 0-7):"), 3, 0)
        self.r_bit = QLineEdit(); self.r_bit.setText("0")
        r_grid.addWidget(self.r_bit, 3, 1)

        r_grid.addWidget(QLabel("字符串长度 (String专用):"), 4, 0)
        self.r_str_len = QLineEdit(); self.r_str_len.setText("24")
        r_grid.addWidget(self.r_str_len, 4, 1)

        rc_layout.addLayout(r_grid)

        # 触发动作
        self.read_btn = QPushButton("立即读取")
        self.read_btn.setCursor(Qt.PointingHandCursor)
        self.read_btn.clicked.connect(self._exec_read)
        rc_layout.addWidget(self.read_btn)

        # 显示框
        rc_layout.addSpacing(10)
        rc_layout.addWidget(QLabel("读取值结果:"))
        self.r_result = QLineEdit()
        self.r_result.setReadOnly(True)
        self.r_result.setStyleSheet("color: #00e676; font-size: 20px; font-weight: 700; background: rgba(0,0,0,0.3);")
        rc_layout.addWidget(self.r_result)

        rc_layout.addStretch()
        rw_layout.addWidget(read_card, stretch=1)


        # ==================== B. 写入操作面板 ====================
        write_card = QFrame()
        write_card.setStyleSheet(read_card.styleSheet()) # 复用样式
        wc_layout = QVBoxLayout(write_card)
        wc_layout.setSpacing(12)

        wt_lbl = QLabel("✏️ PLC 数据写入")
        wt_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #ffca28;")
        wc_layout.addWidget(wt_lbl)

        # 输入格栅
        w_grid = QGridLayout()
        w_grid.setSpacing(10)

        w_grid.addWidget(QLabel("DB块 (DB):"), 0, 0)
        self.w_db = QLineEdit(); self.w_db.setText("1")
        w_grid.addWidget(self.w_db, 0, 1)

        w_grid.addWidget(QLabel("偏移量 (Offset):"), 1, 0)
        self.w_offset = QLineEdit(); self.w_offset.setText("0")
        w_grid.addWidget(self.w_offset, 1, 1)

        w_grid.addWidget(QLabel("数据类型:"), 2, 0)
        self.w_type = QComboBox()
        self.w_type.addItems(["Bool", "SInt", "Int", "DInt", "Real", "String"])
        w_grid.addWidget(self.w_type, 2, 1)

        w_grid.addWidget(QLabel("位号 (Bool必填 0-7):"), 3, 0)
        self.w_bit = QLineEdit(); self.w_bit.setText("0")
        w_grid.addWidget(self.w_bit, 3, 1)

        w_grid.addWidget(QLabel("字符串长度 (String专用):"), 4, 0)
        self.w_str_len = QLineEdit(); self.w_str_len.setText("24")
        w_grid.addWidget(self.w_str_len, 4, 1)

        wc_layout.addLayout(w_grid)

        # 写入值
        wc_layout.addSpacing(10)
        wc_layout.addWidget(QLabel("目标写入值:"))
        self.w_val = QLineEdit()
        self.w_val.setPlaceholderText("请输入目标写入内容")
        wc_layout.addWidget(self.w_val)

        # 触发动作
        self.write_btn = QPushButton("立即写入")
        self.write_btn.setCursor(Qt.PointingHandCursor)
        self.write_btn.clicked.connect(self._exec_write)
        wc_layout.addWidget(self.write_btn)

        wc_layout.addStretch()
        rw_layout.addWidget(write_card, stretch=1)

        layout.addLayout(rw_layout, stretch=1)

    def _check_status(self):
        """同步全局连接灯状态"""
        if self.s7_service is not None and getattr(self.s7_service, "connected", False):
            self.status_dot.setStyleSheet("font-size: 22px; color: #00e676;") # 绿色
            self.status_text.setText("已连接")
            ip = getattr(self.s7_service, "_ip", "Unknown")
            self.status_detail.setText(f"通讯线路畅通 | PLC IP: {ip}")
        else:
            self.status_dot.setStyleSheet("font-size: 22px; color: #ff5252;") # 红色
            self.status_text.setText("未连接")
            self.status_detail.setText("检测到底层通讯脱机，软件将自动发起重连握手...")

    def _exec_read(self):
        if self.s7_service is None or not getattr(self.s7_service, "connected", False):
            QMessageBox.warning(self, "错误", "PLC 处于离线状态，无法读取！")
            return

        try:
            db = int(self.r_db.text().strip() or 1)
            offset = int(self.r_offset.text().strip() or 0)
            bit = int(self.r_bit.text().strip() or 0)
            str_len = int(self.r_str_len.text().strip() or 24)
            dtype = self.r_type.currentText()
        except Exception as e:
            QMessageBox.warning(self, "格式错误", f"输入项含有非数字参数，请检查: {e}")
            return

        try:
            val = self.s7_service.read_value(db, offset, dtype, bit=bit, str_len=str_len)
            if val is not None:
                self.r_result.setText(str(val))
                self.log.emit("info", f"[PLC读写助手] 读取成功: DB{db}.DBX{offset}.{bit}({dtype}) = {val}")
            else:
                self.r_result.setText("读取超时")
                self.log.emit("error", f"[PLC读写助手] 读取失败 (None): DB{db}.DBX{offset}.{bit}({dtype})")
        except Exception as ex:
            self.r_result.setText("报错")
            QMessageBox.warning(self, "读取报错", f"底层数据包解析异常: {ex}")

    def _exec_write(self):
        if self.s7_service is None or not getattr(self.s7_service, "connected", False):
            QMessageBox.warning(self, "错误", "PLC 处于离线状态，无法写入！")
            return

        try:
            db = int(self.w_db.text().strip() or 1)
            offset = int(self.w_offset.text().strip() or 0)
            bit = int(self.w_bit.text().strip() or 0)
            str_len = int(self.w_str_len.text().strip() or 24)
            dtype = self.w_type.currentText()
            raw_val = self.w_val.text().strip()
        except Exception as e:
            QMessageBox.warning(self, "格式错误", f"输入项含有非数字参数，请检查: {e}")
            return

        if not raw_val:
            QMessageBox.warning(self, "提示", "写入值不能为空！")
            return

        # 数据类型转化
        try:
            if dtype == "Bool":
                target_val = raw_val.lower() in ("true", "1", "yes", "on")
            elif dtype in ("Int", "DInt", "SInt"):
                target_val = int(raw_val)
            elif dtype == "Real":
                target_val = float(raw_val)
            else:
                target_val = str(raw_val)
        except ValueError:
            QMessageBox.warning(self, "类型不匹配", f"无法将 '{raw_val}' 强制转换为预期的 {dtype}")
            return

        try:
            ok = self.s7_service.write_value(db, offset, dtype, target_val, bit=bit, str_len=str_len)
            if ok:
                QMessageBox.information(self, "写入成功", f"指令已成功注入 PLC！\nDB{db}.DBX{offset}.{bit}({dtype}) = {target_val}")
                self.log.emit("info", f"[PLC读写助手] 写入成功: DB{db}.DBX{offset}.{bit}({dtype}) <- {target_val}")
            else:
                QMessageBox.warning(self, "写入失败", "底层信号拒签，请检查偏移位置是否在PLC合规区间内！")
        except Exception as ex:
            QMessageBox.warning(self, "写入报错", f"底层发包失败: {ex}")
