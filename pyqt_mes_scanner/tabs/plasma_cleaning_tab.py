# -*- coding: utf-8 -*-
"""等离子清洗监控模块 —— 实时展示 PLC 清洗参数（表格形式）"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QLineEdit,
    QScrollArea, QComboBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush
from datetime import datetime


class PlasmaCleaningTab(QWidget):
    log = pyqtSignal(str, str)
    config_changed = pyqtSignal()

    # 默认监控参数 —— 等离子清洗完成时 PLC 读取数据 (DB100)
    DEFAULT_POINTS = [
        {"name": "心跳信号", "db": 100, "offset": 0, "type": "Int", "unit": "", "bit": 0},
        {"name": "允许读取数据", "db": 100, "offset": 2, "type": "Int", "unit": "", "bit": 0},
        {"name": "喷枪1-功率", "db": 100, "offset": 4, "type": "Real", "unit": "W"},
        {"name": "喷枪1-移动速度", "db": 100, "offset": 8, "type": "Real", "unit": "mm/s"},
        {"name": "喷枪1-旋转速度", "db": 100, "offset": 12, "type": "Real", "unit": "rpm"},
        {"name": "喷枪1-电压", "db": 100, "offset": 16, "type": "Real", "unit": "V"},
        {"name": "喷枪1-电流", "db": 100, "offset": 20, "type": "Real", "unit": "A"},
        {"name": "喷枪1-气压", "db": 100, "offset": 24, "type": "Real", "unit": "Pa"},
        {"name": "喷枪2-功率", "db": 100, "offset": 28, "type": "Real", "unit": "W"},
        {"name": "喷枪2-移动速度", "db": 100, "offset": 32, "type": "Real", "unit": "mm/s"},
        {"name": "喷枪2-旋转速度", "db": 100, "offset": 36, "type": "Real", "unit": "rpm"},
        {"name": "喷枪2-电压", "db": 100, "offset": 40, "type": "Real", "unit": "V"},
        {"name": "喷枪2-电流", "db": 100, "offset": 44, "type": "Real", "unit": "A"},
        {"name": "喷枪2-气压", "db": 100, "offset": 48, "type": "Real", "unit": "Pa"},
        {"name": "喷枪3-功率", "db": 100, "offset": 52, "type": "Real", "unit": "W"},
        {"name": "喷枪3-移动速度", "db": 100, "offset": 56, "type": "Real", "unit": "mm/s"},
        {"name": "喷枪3-旋转速度", "db": 100, "offset": 60, "type": "Real", "unit": "rpm"},
        {"name": "喷枪3-电压", "db": 100, "offset": 64, "type": "Real", "unit": "V"},
        {"name": "喷枪3-电流", "db": 100, "offset": 68, "type": "Real", "unit": "A"},
        {"name": "喷枪3-气压", "db": 100, "offset": 72, "type": "Real", "unit": "Pa"},
        {"name": "模块码", "db": 100, "offset": 76, "type": "String", "unit": "", "bit": 0},
    ]

    def __init__(self, s7_service, config, parent=None):
        super().__init__(parent)
        self.s7_service = s7_service
        self.config = config or {}
        self._monitor_points = []
        self._setup_ui()
        self._load_points()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_all)
        # self._refresh_timer.start(1000)  # 改为手动点击“立即刷新”按钮触发

    def set_config(self, config):
        self.config = config or {}
        self._load_points()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(14, 14, 14, 14)

        # 状态栏
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
        sc.setSpacing(16)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("font-size: 22px; color: #ff5252;")
        sc.addWidget(self.status_dot)

        info = QVBoxLayout()
        self.status_text = QLabel("未连接")
        self.status_text.setStyleSheet("font-size: 16px; font-weight: 700; color: #e3f2fd;")
        info.addWidget(self.status_text)
        self.status_detail = QLabel("--")
        self.status_detail.setStyleSheet("font-size: 12px; color: #78909c;")
        info.addWidget(self.status_detail)
        sc.addLayout(info)
        sc.addStretch()

        self.clean_state_label = QLabel("⏹ 待机")
        self.clean_state_label.setStyleSheet("""
            font-size: 16px; font-weight: 700; color: #78909c;
            background: rgba(100,181,246,0.06);
            border-radius: 8px;
            padding: 8px 18px;
        """)
        sc.addWidget(self.clean_state_label)

        self.refresh_btn = QPushButton("🔄 立即刷新")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: rgba(100,181,246,0.08);
                border: 1px solid rgba(100,181,246,0.2);
                border-radius: 6px; color: #90caf9;
                padding: 8px 16px; font-size: 14px;
            }
            QPushButton:hover { background: rgba(100,181,246,0.15); }
        """)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._refresh_all)
        sc.addWidget(self.refresh_btn)
        layout.addWidget(status_card)

        # 数据表格
        table_card = QFrame()
        table_card.setStyleSheet("""
            QFrame {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.12);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        tc = QVBoxLayout(table_card)
        tc.setSpacing(12)

        title_row = QHBoxLayout()
        title = QLabel("🔬 参数监控")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9;")
        title_row.addWidget(title)
        title_row.addStretch()

        self.oneDtae_label = QLabel("电芯位置:")
        self.oneDtae_label.setStyleSheet("font-size: 14px; color: #e3f2fd;")
        title_row.addWidget(self.oneDtae_label)

        self.oneDtae_combo = QComboBox()
        self.oneDtae_combo.addItems([f"oneDtae[{i}]" for i in range(1, 301)])
        self.oneDtae_combo.setStyleSheet("""
            QComboBox {
                background: #1e293b;
                border: 1px solid rgba(144,202,249,0.3);
                border-radius: 4px;
                padding: 4px 12px;
                color: #f8fafc;
                font-size: 14px;
                min-width: 140px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background: #1e293b; color: #f8fafc; selection-background-color: #3b82f6; }
        """)
        self.oneDtae_combo.currentIndexChanged.connect(self._on_oneDtae_changed)
        title_row.addWidget(self.oneDtae_combo)
        tc.addLayout(title_row)

        self.data_table = QTableWidget()
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels(
            ["参数名称", "DB块", "偏移", "类型", "当前值", "单位", "更新时间"]
        )
        # 设置各列宽度，并让最后一列拉伸填充
        # 设置各列为交互缩放模式以保证列宽不失效
        for col in range(6):
            self.data_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Interactive)
        
        # 设置各列宽度，并让最后一列拉伸填充
        self.data_table.setColumnWidth(0, 260)   # 参数名称
        self.data_table.setColumnWidth(1, 100)   # DB块
        self.data_table.setColumnWidth(2, 120)   # 偏移
        self.data_table.setColumnWidth(3, 120)   # 类型
        self.data_table.setColumnWidth(4, 200)   # 当前值
        self.data_table.setColumnWidth(5, 120)   # 单位
        self.data_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        
        # 表头文本居中对齐，并显式指定适当的固定高度
        self.data_table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.data_table.horizontalHeader().setFixedHeight(100)
        self.data_table.verticalHeader().setVisible(False)
        self.data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.data_table.setShowGrid(False)
        self.data_table.setStyleSheet("""
            QTableWidget { background: transparent; border: none; font-size: 18px; font-family: 'Microsoft YaHei'; }
            QTableWidget::item { color: #e0e6ed; padding: 10px 14px; border-bottom: 1px solid rgba(100,181,246,0.08); qproperty-alignment: 'AlignCenter'; }
            QHeaderView::section { background: rgba(21,101,192,0.35); color: #ffffff; font-weight: bold; font-size: 18px; font-family: 'Microsoft YaHei'; padding: 4px 10px; border: none; border-bottom: 1px solid rgba(100,181,246,0.15); qproperty-alignment: 'AlignCenter'; }
        """)
        tc.addWidget(self.data_table)

        # 操作按钮
        btn_row = QHBoxLayout()
        self.edit_btn = QPushButton("⚙️ 编辑参数地址")
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(100,181,246,0.08);
                border: 1px solid rgba(100,181,246,0.2);
                border-radius: 6px; color: #90caf9;
                padding: 8px 16px; font-size: 14px;
            }
            QPushButton:hover { background: rgba(100,181,246,0.15); }
        """)
        self.edit_btn.setCursor(Qt.PointingHandCursor)
        self.edit_btn.clicked.connect(self._edit_points_dialog)
        btn_row.addWidget(self.edit_btn)
        btn_row.addStretch()
        tc.addLayout(btn_row)

        layout.addWidget(table_card, stretch=1)

    def _on_oneDtae_changed(self):
        """当电芯/极柱位置切换下拉框触发变更时，重新加载点位偏移"""
        self._load_points()
        if hasattr(self, "log"):
            self.log.emit("INFO", f"切换至电芯极柱组 {self.oneDtae_combo.currentText()}")

    def _load_points(self):
        """从配置加载参数点。若在 config 中有记录(哪怕删空)，则以配置为准；否则初次加载默认值。"""
        # 极柱 1-13 数据结构模板 (单组占 80 字节)
        onedtae_template = [
            {"name": "保护气流量1", "offset_shift": 0, "type": "Real", "unit": "L/min"},
            {"name": "外环实际功率1", "offset_shift": 4, "type": "Real", "unit": "W"},
            {"name": "内环实际功率1", "offset_shift": 8, "type": "Real", "unit": "W"},
            {"name": "除尘风速1", "offset_shift": 12, "type": "Real", "unit": "m/s"},
            {"name": "压头压力1", "offset_shift": 16, "type": "Real", "unit": "MPa"},
            {"name": "极柱1行号", "offset_shift": 20, "type": "Int", "unit": ""},
            {"name": "极柱1列号", "offset_shift": 22, "type": "Int", "unit": ""},
            {"name": "极柱1 X轴坐标", "offset_shift": 24, "type": "Real", "unit": "mm"},
            {"name": "极柱1 Y轴坐标", "offset_shift": 28, "type": "Real", "unit": "mm"},
            {"name": "极柱1 Z轴坐标", "offset_shift": 32, "type": "Real", "unit": "mm"},
            {"name": "极柱1 测距值", "offset_shift": 36, "type": "Real", "unit": "mm"},
            {"name": "保护气流量2", "offset_shift": 40, "type": "Real", "unit": "L/min"},
            {"name": "外环实际功率2", "offset_shift": 44, "type": "Real", "unit": "W"},
            {"name": "内环实际功率2", "offset_shift": 48, "type": "Real", "unit": "W"},
            {"name": "除尘风速2", "offset_shift": 52, "type": "Real", "unit": "m/s"},
            {"name": "压头压力2", "offset_shift": 56, "type": "Real", "unit": "MPa"},
            {"name": "极柱2行号", "offset_shift": 60, "type": "Int", "unit": ""},
            {"name": "极柱2列号", "offset_shift": 62, "type": "Int", "unit": ""},
            {"name": "极柱2 X轴坐标", "offset_shift": 64, "type": "Real", "unit": "mm"},
            {"name": "极柱2 Y轴坐标", "offset_shift": 68, "type": "Real", "unit": "mm"},
            {"name": "极柱2 Z轴坐标", "offset_shift": 72, "type": "Real", "unit": "mm"},
            {"name": "极柱2 测距值", "offset_shift": 76, "type": "Real", "unit": "mm"}
        ]

        # 1. 提取基础配置
        base_points = []
        if self.config and "plasmaMonitorPoints" in self.config:
            pts = self.config["plasmaMonitorPoints"]
            for p in pts:
                pname = str(p.get("name", ""))
                if "极柱" in pname or "保护气流量" in pname or "外环实际功率" in pname or "内环实际功率" in pname or "除尘风速" in pname or "压头压力" in pname:
                    continue
                base_points.append({
                    "name": pname,
                    "db": int(p.get("db", 100)),
                    "offset": int(p.get("offset", 0)),
                    "type": str(p.get("type", "Real")),
                    "unit": str(p.get("unit", "")),
                    "bit": int(p.get("bit", 0)),
                    "value": "-",
                    "time": "-"
                })
        else:
            base_points = [dict(p, value="-", time="-") for p in self.DEFAULT_POINTS]

        # 2. 动态拼装选中的 oneDtae[X] 点
        current_index = 0
        if hasattr(self, 'oneDtae_combo'):
            current_index = self.oneDtae_combo.currentIndex()
        
        # 5620 是 oneDtae[1] 的起始偏移，每个结构体占用 80 字节
        oneDtae_base = 5620 + current_index * 80
        
        for t in onedtae_template:
            base_points.append({
                "name": t["name"],
                "db": 8160,
                "offset": oneDtae_base + t["offset_shift"],
                "type": t["type"],
                "unit": t["unit"],
                "bit": 0,
                "value": "-",
                "time": "-"
            })

        self._monitor_points = base_points
        self._refresh_table()

    def _save_points(self):
        """保存参数点到配置"""
        if self.config is None:
            return
        clean = []
        for p in self._monitor_points:
            clean.append({
                "name": p["name"],
                "db": p["db"],
                "offset": p["offset"],
                "type": p["type"],
                "unit": p.get("unit", ""),
                "bit": p.get("bit", 0),
            })
        self.config["plasmaMonitorPoints"] = clean
        self.config_changed.emit()

    def _refresh_table(self):
        self.data_table.setRowCount(len(self._monitor_points))
        for i, p in enumerate(self._monitor_points):
            def create_centered_item(text):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                return item
            
            self.data_table.setItem(i, 0, create_centered_item(p["name"]))
            self.data_table.setItem(i, 1, create_centered_item(str(p["db"])))
            offset_text = f"{p['offset']}.{p.get('bit', 0)}" if p["type"] == "Bool" else str(p["offset"])
            self.data_table.setItem(i, 2, create_centered_item(offset_text))
            self.data_table.setItem(i, 3, create_centered_item(p["type"]))
            
            val_item = QTableWidgetItem(str(p.get("value", "-")))
            val_item.setTextAlignment(Qt.AlignCenter)
            val_item.setFont(QFont("Consolas", 18, QFont.Bold))
            if p["name"] == "清洗状态":
                if p.get("value") is True:
                    val_item.setForeground(QBrush(QColor("#00e676")))
                elif p.get("value") is False:
                    val_item.setForeground(QBrush(QColor("#ff5252")))
                else:
                    val_item.setForeground(QBrush(QColor("#42a5f5")))
            else:
                val_item.setForeground(QBrush(QColor("#42a5f5")))
            self.data_table.setItem(i, 4, val_item)
            self.data_table.setItem(i, 5, create_centered_item(p.get("unit", "")))
            self.data_table.setItem(i, 6, create_centered_item(p.get("time", "-")))

    def _refresh_all(self):
        svc = self.s7_service
        s7_cfg = self.config.get("s7Config", {}) if self.config else {}
        enabled = s7_cfg.get("enabled", False)

        if svc is not None and getattr(svc, "connected", False) and enabled:
            self.status_dot.setStyleSheet("font-size: 22px; color: #00e676;")
            self.status_text.setText("PLC 已连接")
            self.status_detail.setText(
                f"IP: {s7_cfg.get('ip', '--')}  |  Rack: {s7_cfg.get('rack', 0)}  |  Slot: {s7_cfg.get('slot', 1)}"
            )
        else:
            self.status_dot.setStyleSheet("font-size: 22px; color: #ff5252;")
            self.status_text.setText("未连接" if not enabled else "连接断开")
            self.status_detail.setText("S7 通讯未启用或连接失败" if not enabled else "请检查 PLC 网络")

        if svc is None or not getattr(svc, "connected", False):
            return

        cleaning_active = False
        for p in self._monitor_points:
            try:
                val = svc.read_value(
                    p["db"], p["offset"], p["type"],
                    bit=p.get("bit", 0), str_len=254
                )
                if val is None:
                    p["value"] = "读取失败"
                else:
                    p["value"] = val
                    if p["name"] == "清洗状态" and val is True:
                        cleaning_active = True
                p["time"] = datetime.now().strftime("%H:%M:%S")
            except Exception as e:
                p["value"] = "错误"
                p["time"] = datetime.now().strftime("%H:%M:%S")

        self._refresh_table()

        # 更新清洗状态标签
        if cleaning_active:
            self.clean_state_label.setText("▶ 清洗中")
            self.clean_state_label.setStyleSheet("""
                font-size: 16px; font-weight: 700; color: #00e676;
                background: rgba(0,230,118,0.08);
                border: 1px solid rgba(0,230,118,0.2);
                border-radius: 8px; padding: 8px 18px;
            """)
        else:
            self.clean_state_label.setText("⏹ 待机")
            self.clean_state_label.setStyleSheet("""
                font-size: 16px; font-weight: 700; color: #78909c;
                background: rgba(100,181,246,0.06);
                border-radius: 8px; padding: 8px 18px;
            """)

    def _edit_points_dialog(self):
        """增强版对话框：支持动态 新增、删除 和 修改 各清洗参数项"""
        dlg = QWidget(self, Qt.Dialog)
        dlg.setWindowTitle("管理等离子清洗监控参数")
        dlg.resize(1000, 600)
        dlg.setStyleSheet("""
            QWidget { background: #0a0e1a; color: #e0e6ed; }
            QLineEdit { 
                background: #131929; 
                border: 1px solid rgba(100,181,246,0.2); 
                border-radius: 6px; 
                color: #e0e6ed; 
                padding: 6px 10px; 
                font-size: 14px;
            }
            QComboBox {
                background: #131929;
                border: 1px solid rgba(100,181,246,0.2);
                border-radius: 6px;
                color: #e0e6ed;
                padding: 6px;
                font-size: 14px;
            }
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1565c0, stop:1 #0d47a1); 
                border: none; border-radius: 6px; color: #e3f2fd; 
                padding: 10px 20px; font-size: 14px; font-weight: 600; 
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976d2, stop:1 #1565c0); 
            }
            QPushButton#btn_delete {
                background: rgba(244,67,54,0.15);
                border: 1px solid rgba(244,67,54,0.3);
                color: #ef9a9a;
            }
            QPushButton#btn_delete:hover {
                background: rgba(244,67,54,0.3);
            }
        """)
        
        main_layout = QVBoxLayout(dlg)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # 头部标签
        header = QHBoxLayout()
        header.setSpacing(8)
        lbls = ["参数名称", "DB块", "字节偏移", "位号", "数据类型", "单位", "操作"]
        widths = [260, 80, 100, 60, 100, 80, 80]
        for l, w in zip(lbls, widths):
            title = QLabel(l)
            title.setStyleSheet("color: #42a5f5; font-weight: 700; font-size: 14px;")
            title.setFixedWidth(w)
            header.addWidget(title)
        header.addStretch()
        main_layout.addLayout(header)

        # 滚动内容区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid rgba(100,181,246,0.1); border-radius: 8px; background: transparent; }")
        
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("QWidget { background: #0a0e1a; }")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.addStretch() # 底部留空

        rows_data = []

        def add_row_ui(p_data):
            row = QHBoxLayout()
            row.setSpacing(8)

            name_in = QLineEdit(str(p_data.get("name", "")))
            name_in.setFixedWidth(260)
            name_in.setPlaceholderText("心跳信号")

            db_in = QLineEdit(str(p_data.get("db", 100)))
            db_in.setFixedWidth(80)
            db_in.setPlaceholderText("100")

            off_in = QLineEdit(str(p_data.get("offset", 0)))
            off_in.setFixedWidth(100)
            off_in.setPlaceholderText("0")

            bit_in = QLineEdit(str(p_data.get("bit", 0)))
            bit_in.setFixedWidth(60)
            bit_in.setPlaceholderText("0-7")

            type_combo = QComboBox()
            type_combo.addItems(["Bool", "SInt", "Int", "DInt", "Real", "String"])
            type_combo.setFixedWidth(100)
            type_combo.setCurrentText(p_data.get("type", "Real"))

            unit_in = QLineEdit(str(p_data.get("unit", "")))
            unit_in.setFixedWidth(80)
            unit_in.setPlaceholderText("W")

            del_btn = QPushButton("🗑️ 移除")
            del_btn.setObjectName("btn_delete")
            del_btn.setFixedWidth(80)
            del_btn.setCursor(Qt.PointingHandCursor)

            row.addWidget(name_in)
            row.addWidget(db_in)
            row.addWidget(off_in)
            row.addWidget(bit_in)
            row.addWidget(type_combo)
            row.addWidget(unit_in)
            row.addWidget(del_btn)
            row.addStretch()

            # 插到最下面 stretch 的上方
            scroll_layout.insertLayout(scroll_layout.count() - 1, row)

            current_row_info = {
                "name": name_in,
                "db": db_in,
                "offset": off_in,
                "bit": bit_in,
                "type": type_combo,
                "unit": unit_in,
                "layout": row
            }
            rows_data.append(current_row_info)

            def do_remove():
                if current_row_info in rows_data:
                    rows_data.remove(current_row_info)
                name_in.deleteLater()
                db_in.deleteLater()
                off_in.deleteLater()
                bit_in.deleteLater()
                type_combo.deleteLater()
                unit_in.deleteLater()
                del_btn.deleteLater()

            del_btn.clicked.connect(do_remove)

        # 挂载已有参数
        for p in self._monitor_points:
            add_row_ui(p)

        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        action_bar = QHBoxLayout()
        add_btn = QPushButton("➕ 新增监控参数")
        add_btn.setStyleSheet("""
            QPushButton {
                background: rgba(100,181,246,0.12);
                border: 1px solid rgba(100,181,246,0.3);
                color: #90caf9;
            }
            QPushButton:hover { background: rgba(100,181,246,0.25); }
        """)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(lambda: add_row_ui({"name": "新建参数", "db": 100, "offset": 0, "type": "Real", "unit": "", "bit": 0}))
        
        save_btn = QPushButton("💾 保存并应用参数配置")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(dlg.close)

        action_bar.addWidget(add_btn)
        action_bar.addStretch()
        action_bar.addWidget(save_btn)
        main_layout.addLayout(action_bar)

        dlg.show()
        from PyQt5.QtCore import QEventLoop
        loop = QEventLoop()
        save_btn.clicked.connect(loop.quit)
        loop.exec_()

        updated_points = []
        for rd in rows_data:
            try:
                name_str = rd["name"].text().strip()
                if not name_str:
                    continue
                updated_points.append({
                    "name": name_str,
                    "db": int(rd["db"].text().strip() or 100),
                    "offset": int(rd["offset"].text().strip() or 0),
                    "type": rd["type"].currentText(),
                    "unit": rd["unit"].text().strip(),
                    "bit": int(rd["bit"].text().strip() or 0)
                })
            except Exception:
                continue

        self._monitor_points = updated_points
        self._save_points()
        self._refresh_table()
        self.log.emit("info", "[等离子清洗] 参数地址已更新")
