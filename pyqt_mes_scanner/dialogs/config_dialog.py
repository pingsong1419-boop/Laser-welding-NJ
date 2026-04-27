# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QWidget, QFrame, QCheckBox,
    QFileDialog, QComboBox
)
from PyQt5.QtCore import Qt


class ConfigDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = dict(config)
        self.setWindowTitle("系统配置")
        self.setFixedSize(700, 780)
        
        # 开启无边框
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        
        # 拖拽变量
        self._dragging = False
        self._drag_position = None
        
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        from PyQt5.QtWidgets import QTabWidget
        self.setStyleSheet("""
            QDialog {
                background: #0a0e1a;
            }
            QLineEdit {
                background: #131929;
                border: 1.5px solid #2196f3;
                border-radius: 6px;
                color: #ffffff;
                padding: 10px 14px;
                font-size: 14px;
                font-family: Consolas, monospace;
            }
            QLineEdit:focus {
                border-color: #00e5ff;
                background: #161f33;
            }
            QLabel {
                color: #90caf9;
                font-size: 13px;
                font-weight: 600;
            }
            QCheckBox {
                color: #e0e6ed;
                font-size: 14px;
                font-weight: 600;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid rgba(100,181,246,0.3);
                background: #0d1117;
            }
            QCheckBox::indicator:checked {
                background: #1565c0;
                border-color: #42a5f5;
            }
            QComboBox {
                background: #0d1117;
                border: 1px solid rgba(100,181,246,0.2);
                border-radius: 6px;
                color: #e0e6ed;
                padding: 6px 12px;
                font-size: 14px;
            }
            QComboBox:focus {
                border-color: #42a5f5;
            }
            QComboBox QAbstractItemView {
                background: #0a0e1a;
                color: #e0e6ed;
                selection-background-color: #1565c0;
            }
            QPushButton#btn_save {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1565c0, stop:1 #0d47a1);
                border: 1px solid rgba(100,181,246,0.3);
                border-radius: 6px;
                color: #e3f2fd;
                padding: 8px 24px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton#btn_save:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976d2, stop:1 #1565c0);
            }
            QPushButton#btn_cancel {
                background: transparent;
                border: 1px solid rgba(100,181,246,0.25);
                border-radius: 6px;
                color: #78909c;
                padding: 8px 20px;
                font-size: 15px;
            }
            QPushButton#btn_cancel:hover {
                border-color: #42a5f5;
                color: #42a5f5;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -----------------------------------------------------------------
        # Header 头部
        # -----------------------------------------------------------------
        header = QHBoxLayout()
        header.setContentsMargins(24, 18, 24, 18)
        header.setSpacing(10)
        header_widget = QWidget()
        header_widget.setStyleSheet(""" # 设置头部容器的背景样式
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0d47a1, stop:1 #1565c0); # 采用深蓝到亮蓝的科技感线性渐变
            border-bottom: 1px solid rgba(100,181,246,0.2); # 底部加上淡蓝色微透分割线
        """) # 样式表定义结束
        header_widget.setLayout(header) # 把 header 对应的水平布局挂载进头部容器中

        icon = QLabel("⚙️") # 构造代表配置属性的齿轮 emoji 图标
        icon.setStyleSheet("font-size: 15px;") # 稍微调大齿轮图标字体到 20px
        title = QLabel("系统配置") # 构造标题控件
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #e3f2fd;") # 配套浅蓝白大号加粗字体
        close_btn = QPushButton("✕") # 创建右上角的关闭交叉按钮
        close_btn.setStyleSheet(""" # 清洗按钮的背景与边框
            background: none; border: none; color: #90caf9; font-size: 18px; # 赋予透明化悬浮底色及字号
            padding: 4px 8px; border-radius: 4px; # 配套相应的点击触控范围
        """) # 关闭按钮样式结束
        close_btn.setCursor(Qt.PointingHandCursor) # 移入时变为点击小手光标
        close_btn.clicked.connect(self.reject) # 绑定单击信号至窗口的 reject 退出方法
        header.addWidget(icon) # 向标题栏中压入图标
        header.addWidget(title) # 向标题栏中压入主标题
        header.addStretch() # 添加弹性空白区，自动占据中间全幅宽度
        header.addWidget(close_btn) # 在最右侧塞入关闭控制器
        layout.addWidget(header_widget) # 将完整渲染出的头部压入主容器的最上层位置

        # -----------------------------------------------------------------
        # Body 选项卡界面 (QTabWidget)
        # -----------------------------------------------------------------
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(100,181,246,0.15);
                background: #0a0e1a;
                border-radius: 8px;
                top: -1px;
                padding: 10px;
            }
            QTabBar::tab {
                background: rgba(21,101,192,0.15);
                border: 1px solid rgba(100,181,246,0.2);
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                color: #78909c;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 600;
                margin-right: 6px;
            }
            QTabBar::tab:hover {
                background: rgba(21,101,192,0.3);
                color: #90caf9;
            }
            QTabBar::tab:selected {
                background: #0a0e1a;
                border: 1px solid rgba(100,181,246,0.3);
                border-bottom: 2px solid #42a5f5;
                color: #42a5f5;
            }
        """)

        # Tab 1: 🔌 接口配置
        api_tab = QWidget()
        api_tab_layout = QVBoxLayout(api_tab)
        api_tab_layout.setContentsMargins(0, 0, 0, 0)
        
        api_scroll = QScrollArea()
        api_scroll.setWidgetResizable(True)
        api_scroll.setStyleSheet("background: transparent; border: none;")
        api_content = QWidget()
        api_layout = QVBoxLayout(api_content)
        api_layout.setSpacing(16)
        api_layout.setContentsMargins(16, 16, 16, 16)

        api_layout.addWidget(self._section_title("模块码绑定接口"))
        self.orderApiUrl = self._field(api_layout, "非首工序获取工单 API",
                                       "http://172.25.57.144:8076/api/OrderInfo/GetOtherOrderInfoByProcess")
        self.routeApiUrl = self._field(api_layout, "工步下发 API",
                                       "http://172.25.57.144:8076/api/OrderInfo/GetTechRouteListByCode")
        self.singleMaterialApiUrl = self._field(api_layout, "单物料校验 API",
                                                "http://172.25.57.144:8076/api/ProduceMessage/MaterialCheckInput")
        self.moduleCodeApiUrl = self._field(api_layout, "获取模块码 API",
                                            "http://172.25.57.144:8076/api/ProduceMessage/MaterialCheckInput")
        self.moduleBindPushUrl = self._field(api_layout, "模块码绑定模块码上传接口",
                                             "http://172.25.57.144:8034/api/ProduceMessage/PushMessageToMes")
        self.fullMaterialCheckUrl = self._field(api_layout, "全物料校验 API",
                                                "http://172.25.57.144:8076/api/ProduceMessage/FullMaterialCheck")

        api_layout.addWidget(self._section_title("模组入箱接口"))
        self.packingUploadUrl = self._field(api_layout, "模组入箱数据上传 API",
                                            "/mes-api/api/Packing/UploadPackingOrder")
        api_layout.addStretch()
        api_scroll.setWidget(api_content)
        api_tab_layout.addWidget(api_scroll)
        self.tab_widget.addTab(api_tab, "🔌 接口配置")

        # Tab 2: 📋 基础配置
        base_tab = QWidget()
        base_tab_layout = QVBoxLayout(base_tab)
        base_tab_layout.setContentsMargins(0, 0, 0, 0)
        
        base_scroll = QScrollArea()
        base_scroll.setWidgetResizable(True)
        base_scroll.setStyleSheet("background: transparent; border: none;")
        base_content = QWidget()
        base_layout = QVBoxLayout(base_content)
        base_layout.setSpacing(16)
        base_layout.setContentsMargins(16, 16, 16, 16)

        base_layout.addWidget(self._section_title("工序编码"))
        row_proc = QHBoxLayout()
        self.moduleBindProcessCode = self._field_in_layout(row_proc, "当前工序编号", stretch=1)
        base_layout.addLayout(row_proc)

        base_layout.addWidget(self._section_title("设备与租户信息"))
        row_dev1 = QHBoxLayout()
        self.tenantID = self._field_in_layout(row_dev1, "租户ID (tenantID)", stretch=1)
        self.DeviceCode = self._field_in_layout(row_dev1, "设备编码 (DeviceCode)", stretch=1)
        base_layout.addLayout(row_dev1)
        
        row_dev2 = QHBoxLayout()
        self.UserName = self._field_in_layout(row_dev2, "用户名称 (UserName)", stretch=1)
        self.UserAccount = self._field_in_layout(row_dev2, "用户账号 (UserAccount)", stretch=1)
        base_layout.addLayout(row_dev2)
        
        row_dev3 = QHBoxLayout()
        self.defaultFeatureCode = self._field_in_layout(row_dev3, "默认特征代码 (tzdm)", stretch=1)
        self.defaultSpecCode = self._field_in_layout(row_dev3, "默认规格代码 (ggdm)", stretch=1)
        base_layout.addLayout(row_dev3)

        base_layout.addWidget(self._section_title("日志配置"))
        row_log = QHBoxLayout()
        self.logSavePath = self._field_in_layout(row_log, "日志保存目录 (留空则不保存)", stretch=3)
        self.log_browse_btn = QPushButton("浏览...")
        self.log_browse_btn.setStyleSheet("""
            QPushButton {
                background: rgba(100,181,246,0.08);
                border: 1px solid rgba(100,181,246,0.2);
                border-radius: 6px;
                color: #90caf9;
                padding: 6px 14px;
                font-size: 14px;
            }
            QPushButton:hover { background: rgba(100,181,246,0.15); }
        """)
        self.log_browse_btn.setCursor(Qt.PointingHandCursor)
        self.log_browse_btn.clicked.connect(self._browse_log_path)
        row_log.addWidget(self.log_browse_btn)
        base_layout.addLayout(row_log)
        
        base_layout.addStretch()
        base_scroll.setWidget(base_content)
        base_tab_layout.addWidget(base_scroll)
        self.tab_widget.addTab(base_tab, "📋 基础配置")

        # Tab 3: 🤖 PLC 通讯
        plc_tab = QWidget()
        plc_tab_layout = QVBoxLayout(plc_tab)
        plc_tab_layout.setContentsMargins(0, 0, 0, 0)
        
        plc_scroll = QScrollArea()
        plc_scroll.setWidgetResizable(True)
        plc_scroll.setStyleSheet("background: transparent; border: none;")
        plc_content = QWidget()
        plc_layout = QVBoxLayout(plc_content)
        plc_layout.setSpacing(16)
        plc_layout.setContentsMargins(16, 16, 16, 16)

        plc_layout.addWidget(self._section_title("S7 通讯连接设置"))
        self.s7_enabled = QCheckBox("启用 S7 通讯")
        plc_layout.addWidget(self.s7_enabled)
        
        row_s7_1 = QHBoxLayout()
        self.s7_ip = self._field_in_layout(row_s7_1, "PLC IP 地址", stretch=2)
        self.s7_rack = self._field_in_layout(row_s7_1, "机架号 (Rack)", stretch=1)
        self.s7_slot = self._field_in_layout(row_s7_1, "槽号 (Slot)", stretch=1)
        plc_layout.addLayout(row_s7_1)
        
        row_s7_2 = QHBoxLayout()
        self.s7_poll = self._field_in_layout(row_s7_2, "轮询间隔 (ms)", stretch=1)
        plc_layout.addLayout(row_s7_2)

        plc_layout.addWidget(self._section_title("S7 焊接完成信号地址"))
        row_sig_1 = QHBoxLayout()
        self.sig_db = self._field_in_layout(row_sig_1, "DB块", stretch=1)
        self.sig_offset = self._field_in_layout(row_sig_1, "偏移地址", stretch=1)
        self.sig_type = QComboBox()
        self.sig_type.addItems(["Bool", "SInt", "Int", "DInt", "Real", "String"])
        row_sig_1.addWidget(QLabel("数据类型:"))
        row_sig_1.addWidget(self.sig_type, stretch=1)
        plc_layout.addLayout(row_sig_1)
        
        row_sig_2 = QHBoxLayout()
        self.sig_bit = self._field_in_layout(row_sig_2, "位号 (Bool时)", stretch=1)
        self.sig_trigger = self._field_in_layout(row_sig_2, "触发值", stretch=1)
        self.sig_reset = self._field_in_layout(row_sig_2, "复位值", stretch=1)
        plc_layout.addLayout(row_sig_2)

        plc_layout.addWidget(self._section_title("S7 国标码读取地址"))
        row_mod_1 = QHBoxLayout()
        self.mod_db = self._field_in_layout(row_mod_1, "DB块", stretch=1)
        self.mod_offset = self._field_in_layout(row_mod_1, "偏移地址", stretch=1)
        self.mod_type = QComboBox()
        self.mod_type.addItems(["Bool", "SInt", "Int", "DInt", "Real", "String"])
        row_mod_1.addWidget(QLabel("数据类型:"))
        row_mod_1.addWidget(self.mod_type, stretch=1)
        plc_layout.addLayout(row_mod_1)
        
        row_mod_2 = QHBoxLayout()
        self.mod_bit = self._field_in_layout(row_mod_2, "位号 (Bool时)", stretch=1)
        self.mod_str_len = self._field_in_layout(row_mod_2, "字符串长度 (String时)", stretch=1)
        plc_layout.addLayout(row_mod_2)

        # --- 界面已删除 箱体码请求信号配置 ---
        row_req_1 = QHBoxLayout()
        self.req_db = self._field_in_layout(row_req_1, "DB块", stretch=1)
        self.req_offset = self._field_in_layout(row_req_1, "偏移地址", stretch=1)
        self.req_type = QComboBox()
        self.req_type.addItems(["Bool", "SInt", "Int", "DInt", "Real", "String"])
        row_req_1.addWidget(QLabel("数据类型:"))
        row_req_1.addWidget(self.req_type, stretch=1)
        
        row_req_2 = QHBoxLayout()
        self.req_bit = self._field_in_layout(row_req_2, "位号 (Bool时)", stretch=1)
        self.req_trigger = self._field_in_layout(row_req_2, "触发值", stretch=1)
        self.req_reset = self._field_in_layout(row_req_2, "复位值", stretch=1)

        # --- 界面已删除 箱体码信号配置 ---
        row_box_1 = QHBoxLayout()
        self.box_db = self._field_in_layout(row_box_1, "DB块", stretch=1)
        self.box_offset = self._field_in_layout(row_box_1, "偏移地址", stretch=1)
        self.box_type = QComboBox()
        self.box_type.addItems(["Bool", "SInt", "Int", "DInt", "Real", "String"])
        row_box_1.addWidget(QLabel("数据类型:"))
        row_box_1.addWidget(self.box_type, stretch=1)
        
        row_box_2 = QHBoxLayout()
        self.box_bit = self._field_in_layout(row_box_2, "位号 (Bool时)", stretch=1)
        self.box_str_len = self._field_in_layout(row_box_2, "字符串长度 (String时)", stretch=1)
        
        plc_layout.addStretch()
        plc_scroll.setWidget(plc_content)
        plc_tab_layout.addWidget(plc_scroll)
        self.tab_widget.addTab(plc_tab, "🤖 PLC 通讯")

        layout.addWidget(self.tab_widget)

        # -----------------------------------------------------------------
        # Footer 底部
        # -----------------------------------------------------------------
        footer = QHBoxLayout()
        footer.setContentsMargins(24, 16, 24, 16)
        footer.setSpacing(12)
        footer_widget = QWidget()
        footer_widget.setStyleSheet("border-top: 1px solid rgba(100,181,246,0.1);")
        footer_widget.setLayout(footer)

        cancel = QPushButton("取消")
        cancel.setObjectName("btn_cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("保存配置")
        save.setObjectName("btn_save")
        save.clicked.connect(self._save)
        footer.addStretch()
        footer.addWidget(cancel)
        footer.addWidget(save)
        layout.addWidget(footer_widget)

    def _section_title(self, text):
        label = QLabel(text)
        label.setStyleSheet("""
            color: #42a5f5;
            font-size: 15px;
            font-weight: 700;
            border-left: 3px solid #42a5f5;
            padding-left: 8px;
            margin-top: 6px;
        """)
        return label

    def _field(self, parent_layout, label, hint, password=False):
        from PyQt5.QtWidgets import QFrame
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #0d1222;
                border: 1px solid rgba(100,181,246,0.18);
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
                color: #90caf9;
                font-weight: bold;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(10)

        l = QLabel(label)
        card_layout.addWidget(l)
        
        edit = QLineEdit()
        if password:
            edit.setEchoMode(QLineEdit.Password)
        if hint:
            edit.setPlaceholderText(hint)
        card_layout.addWidget(edit)
        
        parent_layout.addWidget(card)
        return edit

    def _field_in_layout(self, layout, label, stretch=1, password=False):
        from PyQt5.QtWidgets import QFrame
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #0d1222;
                border: 1px solid rgba(100,181,246,0.18);
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
                color: #90caf9;
                font-weight: bold;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(10)

        l = QLabel(label)
        card_layout.addWidget(l)
        
        edit = QLineEdit()
        if password:
            edit.setEchoMode(QLineEdit.Password)
        card_layout.addWidget(edit)
        
        layout.addWidget(card, stretch=stretch)
        return edit

    def _load_values(self):
        def set_text(edit, key):
            edit.setText(str(self.config.get(key, "")))
        set_text(self.orderApiUrl, "orderApiUrl")
        set_text(self.routeApiUrl, "routeApiUrl")
        set_text(self.singleMaterialApiUrl, "singleMaterialApiUrl")
        set_text(self.moduleCodeApiUrl, "moduleCodeApiUrl")
        set_text(self.moduleBindPushUrl, "moduleBindPushUrl")
        set_text(self.fullMaterialCheckUrl, "fullMaterialCheckUrl")
        set_text(self.packingUploadUrl, "packingUploadUrl")
        set_text(self.moduleBindProcessCode, "moduleBindProcessCode")
        set_text(self.tenantID, "tenantID")
        set_text(self.DeviceCode, "DeviceCode")
        set_text(self.UserName, "UserName")
        set_text(self.UserAccount, "UserAccount")
        set_text(self.defaultFeatureCode, "defaultFeatureCode")
        set_text(self.defaultSpecCode, "defaultSpecCode")
        self.logSavePath.setText(str(self.config.get("logSavePath", "")))
        s7 = self.config.get("s7Config", {}) or self.config.get("s7", {})
        self.s7_enabled.setChecked(bool(s7.get("enabled", False)))
        self.s7_ip.setText(str(s7.get("ip", "192.168.1.10")))
        self.s7_rack.setText(str(s7.get("rack", 0)))
        self.s7_slot.setText(str(s7.get("slot", 1)))
        self.s7_poll.setText(str(s7.get("pollIntervalMs", 500)))
        # 启动信号
        sig = s7.get("startSignal", {})
        self.sig_db.setText(str(sig.get("db", 1)))
        self.sig_offset.setText(str(sig.get("offset", 6)))
        self.sig_type.setCurrentText(str(sig.get("type", "Int")))
        self.sig_bit.setText(str(sig.get("bit", 0)))
        self.sig_trigger.setText(str(sig.get("triggerValue", "1")))
        self.sig_reset.setText(str(sig.get("resetValue", "0")))
        # 模块码信号
        mod = s7.get("moduleCodeSignal", {})
        self.mod_db.setText(str(mod.get("db", 2)))
        self.mod_offset.setText(str(mod.get("offset", 112)))
        self.mod_type.setCurrentText(str(mod.get("type", "String")))
        self.mod_bit.setText(str(mod.get("bit", 0)))
        self.mod_str_len.setText(str(mod.get("strLen", 24)))
        # 箱体码请求信号
        req = s7.get("packBoxRequestSignal", {})
        self.req_db.setText(str(req.get("db", 3)))
        self.req_offset.setText(str(req.get("offset", 0)))
        self.req_type.setCurrentText(str(req.get("type", "Bool")))
        self.req_bit.setText(str(req.get("bit", 0)))
        self.req_trigger.setText(str(req.get("triggerValue", "1")))
        self.req_reset.setText(str(req.get("resetValue", "0")))
        # 箱体码信号
        box = s7.get("packBoxSignal", {})
        self.box_db.setText(str(box.get("db", 3)))
        self.box_offset.setText(str(box.get("offset", 200)))
        self.box_type.setCurrentText(str(box.get("type", "String")))
        self.box_bit.setText(str(box.get("bit", 0)))
        self.box_str_len.setText(str(box.get("strLen", 24)))

    def _save(self):
        def get_text(edit, default=""):
            return edit.text().strip() or default
        self.config["orderApiUrl"] = get_text(self.orderApiUrl, "http://172.25.57.144:8076/api/OrderInfo/GetOtherOrderInfoByProcess")
        self.config["routeApiUrl"] = get_text(self.routeApiUrl, "http://172.25.57.144:8076/api/OrderInfo/GetTechRouteListByCode")
        self.config["singleMaterialApiUrl"] = get_text(self.singleMaterialApiUrl, "http://172.25.57.144:8076/api/ProduceMessage/MaterialCheckInput")
        self.config["moduleCodeApiUrl"] = get_text(self.moduleCodeApiUrl, "http://172.25.57.144:8076/api/ProduceMessage/MaterialCheckInput")
        self.config["moduleBindPushUrl"] = get_text(self.moduleBindPushUrl, "http://172.25.57.144:8034/api/ProduceMessage/PushMessageToMes")
        self.config["fullMaterialCheckUrl"] = get_text(self.fullMaterialCheckUrl, "http://172.25.57.144:8076/api/ProduceMessage/FullMaterialCheck")
        self.config["packingUploadUrl"] = get_text(self.packingUploadUrl, "/mes-api/api/Packing/UploadPackingOrder")
        self.config["moduleBindProcessCode"] = get_text(self.moduleBindProcessCode, "MODULE_BIND")
        self.config["tenantID"] = get_text(self.tenantID, "")
        self.config["DeviceCode"] = get_text(self.DeviceCode, "")
        self.config["UserName"] = get_text(self.UserName, "")
        self.config["UserAccount"] = get_text(self.UserAccount, "")
        self.config["defaultFeatureCode"] = get_text(self.defaultFeatureCode, "")
        self.config["defaultSpecCode"] = get_text(self.defaultSpecCode, "")
        self.config["logSavePath"] = get_text(self.logSavePath, "")
        self.config["s7Config"] = {
            "enabled": self.s7_enabled.isChecked(),
            "ip": get_text(self.s7_ip, "192.168.1.10"),
            "rack": int(get_text(self.s7_rack, "0") or 0),
            "slot": int(get_text(self.s7_slot, "1") or 1),
            "pollIntervalMs": int(get_text(self.s7_poll, "500") or 500),
            "startSignal": {
                "db": int(get_text(self.sig_db, "1") or 1),
                "offset": int(get_text(self.sig_offset, "6") or 6),
                "type": self.sig_type.currentText(),
                "bit": int(get_text(self.sig_bit, "0") or 0),
                "triggerValue": get_text(self.sig_trigger, "1"),
                "resetValue": get_text(self.sig_reset, "0"),
            },
            "moduleCodeSignal": {
                "db": int(get_text(self.mod_db, "2") or 2),
                "offset": int(get_text(self.mod_offset, "112") or 112),
                "type": self.mod_type.currentText(),
                "bit": int(get_text(self.mod_bit, "0") or 0),
                "strLen": int(get_text(self.mod_str_len, "24") or 24),
            },
            "packBoxRequestSignal": {
                "db": int(get_text(self.req_db, "3") or 3),
                "offset": int(get_text(self.req_offset, "0") or 0),
                "type": self.req_type.currentText(),
                "bit": int(get_text(self.req_bit, "0") or 0),
                "triggerValue": get_text(self.req_trigger, "1"),
                "resetValue": get_text(self.req_reset, "0"),
            },
            "packBoxSignal": {
                "db": int(get_text(self.box_db, "3") or 3),
                "offset": int(get_text(self.box_offset, "200") or 200),
                "type": self.box_type.currentText(),
                "bit": int(get_text(self.box_bit, "0") or 0),
                "strLen": int(get_text(self.box_str_len, "24") or 24),
            },
        }
        self.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and self._drag_position:
            self.move(event.globalPos() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        event.accept()

    def _browse_log_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择日志保存目录", self.logSavePath.text() or "")
        if path:
            self.logSavePath.setText(path)

    def get_config(self):
        return self.config
