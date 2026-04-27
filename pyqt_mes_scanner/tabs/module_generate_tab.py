# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QScrollArea,
    QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QColor, QBrush, QFont
from datetime import datetime
import requests


class ModuleCodeWorker(QThread):
    """异步生成模组码工作线程"""
    finished = pyqtSignal(list)  # list of {"sourceCode": ..., "bindCode": ...}
    error = pyqtSignal(str)
    api_record = pyqtSignal(dict)
    progress = pyqtSignal(int, str)

    def __init__(self, url, payloads):
        super().__init__()
        self.url = url
        self.payloads = payloads

    def run(self):
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        results = []
        for idx, payload in enumerate(self.payloads):
            src = payload.pop("_source_code", "")
            mno = payload.pop("_material_no", "")
            try:
                resp = requests.post(self.url, json=payload, headers=headers, timeout=30)
                data = resp.json()
                if data.get("code") != 200:
                    self.api_record.emit({
                        "title": f"生成模组码 [{idx+1}/{len(self.payloads)}]",
                        "url": self.url,
                        "status": "error",
                        "time": f"{resp.elapsed.total_seconds()*1000:.0f}ms",
                        "reqBody": payload,
                        "resBody": data
                    })
                    self.error.emit(f"第 {idx+1} 个模组码生成失败: {data.get('message', '未知错误')}")
                    return
                code = self._extract_code(data)
                if not code:
                    self.api_record.emit({
                        "title": f"生成模组码 [{idx+1}/{len(self.payloads)}]",
                        "url": self.url,
                        "status": "error",
                        "time": f"{resp.elapsed.total_seconds()*1000:.0f}ms",
                        "reqBody": payload,
                        "resBody": data
                    })
                    self.error.emit(f"第 {idx+1} 个模组码生成失败: 响应中未找到模组码")
                    return
                results.append({"sourceCode": src, "bindCode": code, "materialNo": mno})
                self.progress.emit(idx + 1, code)
                self.api_record.emit({
                    "title": f"生成模组码 [{idx+1}/{len(self.payloads)}]",
                    "url": self.url,
                    "status": "success",
                    "time": f"{resp.elapsed.total_seconds()*1000:.0f}ms",
                    "reqBody": payload,
                    "resBody": data
                })
            except Exception as e:
                self.api_record.emit({
                    "title": f"生成模组码 [{idx+1}/{len(self.payloads)}]",
                    "url": self.url,
                    "status": "error",
                    "time": "-",
                    "reqBody": payload,
                    "resBody": {"error": str(e)}
                })
                self.error.emit(f"网络异常: {str(e)}")
                return
        self.finished.emit(results)

    def _extract_code(self, data):
        """从响应中提取生成的模组码，兼容多种格式"""
        if not isinstance(data, dict):
            return str(data) if data else None
        # 优先查找常见字段（排除 code 业务状态码）
        for key in ("moduleCode", "barCode", "barcode", "sn", "serialNo", "bindCode", "result"):
            val = data.get(key)
            if val and not isinstance(val, bool):
                return str(val)
        # 查找 datas / data 字段
        d = data.get("datas") or data.get("data")
        if isinstance(d, str):
            return d
        if isinstance(d, list) and len(d) > 0:
            first = d[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                for key in ("moduleCode", "barCode", "barcode", "sn", "serialNo", "bindCode", "result"):
                    val = first.get(key)
                    if val and not isinstance(val, bool):
                        return str(val)
                return str(first)
        if isinstance(d, dict):
            for key in ("moduleCode", "barCode", "barcode", "sn", "serialNo", "bindCode", "result"):
                val = d.get(key)
                if val and not isinstance(val, bool):
                    return str(val)
            return str(d)
        return None


class ModuleGenerateTab(QWidget):
    log = pyqtSignal(str, str)
    api_record = pyqtSignal(dict)
    generated = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.module_codes = []
        self.generated_codes = []
        self.material_list = []  # 完整的物料列表（含materialName）
        self.bind_code_map = {}  # materialNo -> bindCode
        self.order_info = None
        self.config = {}
        self.worker = None
        self._setup_ui()

    def set_order_info(self, order_info):
        self.order_info = order_info

    def set_config(self, config):
        self.config = config or {}

    def set_material_list(self, materials):
        self.material_list = materials or []

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部操作栏
        action_bar = QHBoxLayout()
        action_bar.setContentsMargins(12, 12, 12, 12)
        action_bar.setSpacing(12)

        self.status_label = QLabel("等待单物料校验完成...")
        self.status_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #78909c;")
        action_bar.addWidget(self.status_label)
        action_bar.addStretch()

        self.generate_btn = QPushButton("🏷️ 生成模组码")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1565c0, stop:1 #0d47a1);
                border: none; border-radius: 6px; color: #e3f2fd;
                padding: 8px 18px; font-size: 14px; font-weight: 600;
            }
            QPushButton:hover:!disabled { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976d2, stop:1 #1565c0); }
            QPushButton:disabled { opacity: 0.4; }
        """)
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self._handle_generate)
        action_bar.addWidget(self.generate_btn)

        action_widget = QWidget()
        action_widget.setLayout(action_bar)
        action_widget.setStyleSheet("background: rgba(13,71,161,0.15); border-bottom: 1px solid rgba(100,181,246,0.1);")
        layout.addWidget(action_widget)

        # 内容区
        content = QVBoxLayout()
        content.setContentsMargins(12, 12, 12, 12)
        content.setSpacing(12)

        # 来源模块码
        source_card = self._create_card("📋 已校验模块码（来源）")
        self.source_table = QTableWidget()
        self.source_table.setColumnCount(3)
        self.source_table.setHorizontalHeaderLabels(["序号", "模块码", "校验状态"])
        self.source_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.source_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.source_table.setColumnWidth(0, 70)
        self.source_table.verticalHeader().setVisible(False)
        self.source_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.source_table.setShowGrid(False)
        for i in range(3):
            item = self.source_table.horizontalHeaderItem(i)
            if item:
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                item.setForeground(QBrush(QColor("#90caf9")))
                item.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.source_table.setStyleSheet("""
            QTableWidget { background: transparent; border: none; font-size: 14px; }
            QTableWidget::item { color: #cfd8dc; padding: 8px 12px; border-bottom: 1px solid rgba(100,181,246,0.05); }
            QHeaderView::section { background: rgba(21,101,192,0.2); color: #90caf9; font-weight: 700; font-size: 12px; padding: 6px 12px; min-height: 28px; border: none; border-bottom: 1px solid rgba(100,181,246,0.1); }
        """)
        source_card.layout().addWidget(self.source_table)
        content.addWidget(source_card)

        # 生成结果
        result_card = self._create_card("🏷️ 生成结果（模组绑定码）")
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(3)
        self.result_table.setHorizontalHeaderLabels(["序号", "来源模块码", "生成的绑定码"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.result_table.setColumnWidth(0, 70)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.setShowGrid(False)
        for i in range(3):
            item = self.result_table.horizontalHeaderItem(i)
            if item:
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                item.setForeground(QBrush(QColor("#90caf9")))
                item.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.result_table.setStyleSheet("""
            QTableWidget { background: transparent; border: none; font-size: 14px; }
            QTableWidget::item { color: #cfd8dc; padding: 8px 12px; border-bottom: 1px solid rgba(100,181,246,0.05); }
            QHeaderView::section { background: rgba(21,101,192,0.2); color: #90caf9; font-weight: 700; font-size: 12px; padding: 6px 12px; min-height: 28px; border: none; border-bottom: 1px solid rgba(100,181,246,0.1); }
        """)
        result_card.layout().addWidget(self.result_table)
        content.addWidget(result_card)

        content.addStretch()
        layout.addLayout(content, stretch=1)

    def _create_card(self, title):
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
        tl = QLabel(title)
        tl.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9; letter-spacing: 0.5px;")
        layout.addWidget(tl)
        return card

    def set_module_codes(self, codes):
        """接收第3步校验通过的模块码列表"""
        self.module_codes = codes
        self.generated_codes = []
        self._refresh_source_table()
        if codes:
            self.status_label.setText(f"已就绪，共 {len(codes)} 个模块码待生成绑定码")
            self.status_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #42a5f5;")
            self.generate_btn.setEnabled(True)
        else:
            self.status_label.setText("等待单物料校验完成...")
            self.status_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #78909c;")
            self.generate_btn.setEnabled(False)
        self.result_table.setRowCount(0)

    def _refresh_source_table(self):
        self.source_table.setRowCount(len(self.module_codes))
        for i, code in enumerate(self.module_codes):
            item = QTableWidgetItem(str(i + 1))
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QBrush(QColor("#90caf9")))
            self.source_table.setItem(i, 0, item)

            item = QTableWidgetItem(code)
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QBrush(QColor("#64b5f6")))
            item.setFont(QFont("Consolas", 11))
            self.source_table.setItem(i, 1, item)

            item = QTableWidgetItem("校验通过")
            item.setForeground(QBrush(QColor("#00e676")))
            item.setTextAlignment(Qt.AlignCenter)
            self.source_table.setItem(i, 2, item)

    def _handle_generate(self):
        if not self.module_codes:
            return

        url = self.config.get("moduleCodeApiUrl", "").strip()
        if not url:
            self._show_error("未配置生成模块码接口地址，请在系统配置中设置")
            return

        if not self.order_info:
            self._show_error("缺少工单信息，无法生成模块码")
            return

        # 获取动态字段
        xmh = (
            self.order_info.get("projectCode")
            or self.order_info.get("xmh")
            or self.order_info.get("projectNo")
            or self.order_info.get("project_Number")
            or ""
        )
        ggdm = (
            self.order_info.get("specsCode")
            or self.order_info.get("specCode")
            or self.order_info.get("ggdm")
            or self.order_info.get("specification")
            or self.order_info.get("productMixCode")
            or self.config.get("defaultSpecCode", "")
        )
        tzdm = (
            self.order_info.get("productProperty")
            or self.order_info.get("tzdm")
            or self.order_info.get("productMixCode")
            or self.order_info.get("specsCode")
            or self.order_info.get("featureCode")
            or self.config.get("defaultFeatureCode", "")
        )
        self.log.emit("info", f"[生成模组码] 字段取值: xmh={xmh}, ggdm={ggdm}, tzdm={tzdm}, order_info_keys={list(self.order_info.keys()) if self.order_info else 'None'}")

        bmtime = datetime.now().strftime("%Y-%m-%d")

        self.generate_btn.setEnabled(False)
        self.status_label.setText("正在生成模组绑定码...")
        self.status_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #ffab40;")
        self.log.emit("info", "[生成模组码] 开始生成模组绑定码...")

        # 只筛选物料名称中包含"模组码"的物料来申请绑定码
        module_tasks = [m for m in self.material_list if "模组码" in m.get("materialName", "")]
        if not module_tasks:
            self._show_error("未找到物料名称中包含'模组码'的物料，无法生成绑定码")
            return

        payloads = []
        for task in module_tasks:
            src = task.get("productCode", "")
            mno = task.get("materialNo", "")
            payload = {
                "csname": "合肥",
                "bmtime": bmtime,
                "xmh": xmh,
                "cplx": "M",
                "cplxname": "模组",
                "ggdm": ggdm,
                "dysl": "1",
                "dcbsl": "1",
                "useR_NO": self.config.get("DeviceCode", "device001"),
                "useR_NAME": self.config.get("UserName", "设备001"),
                "dclx": "磷酸铁锂电池",
                "scgc": "南京国轩公司",
                "sccx": "三期PACK三线",
                "tzdm": tzdm,
                "mzjx": "0",
                "_source_code": src,
                "_material_no": mno
            }
            payloads.append(payload)

        self.worker = ModuleCodeWorker(url, payloads)
        self.worker.finished.connect(self._on_generate_finished)
        self.worker.error.connect(self._on_generate_error)
        self.worker.api_record.connect(self._on_generate_api_record)
        self.worker.progress.connect(self._on_generate_progress)
        self.worker.start()

    def _on_generate_progress(self, idx, code):
        self.status_label.setText(f"正在生成... 已完成 {idx} 个")
        self.log.emit("info", f"[生成模组码] 第 {idx} 个绑定码: {code}")

    def _on_generate_finished(self, results):
        # 建立物料编号 -> 绑定码的映射
        self.bind_code_map = {}
        for rec in results:
            mno = rec.get("materialNo", "")
            if mno:
                self.bind_code_map[mno] = rec["bindCode"]
        self.generated_codes = results
        self._refresh_result_table()
        self.status_label.setText(f"生成完成，共 {len(self.generated_codes)} 个绑定码")
        self.status_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #00e676;")
        self.log.emit("success", f"[生成模组码] 生成完成，共 {len(self.generated_codes)} 个绑定码")
        self.generated.emit(self.generated_codes)
        self.worker = None

    def _on_generate_error(self, msg):
        self._show_error(msg)
        self.worker = None

    def _on_generate_api_record(self, rec):
        self.api_record.emit(rec)

    def _show_error(self, msg):
        self.status_label.setText(f"生成失败: {msg}")
        self.status_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #ff5252;")
        self.log.emit("error", f"[生成模组码] {msg}")
        self.generate_btn.setEnabled(True)

    def _refresh_result_table(self):
        # 显示所有来源模块码，但只给包含"模组码"的物料填入绑定码
        self.result_table.setRowCount(len(self.module_codes))
        for i, src in enumerate(self.module_codes):
            item = QTableWidgetItem(str(i + 1))
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QBrush(QColor("#90caf9")))
            self.result_table.setItem(i, 0, item)

            item = QTableWidgetItem(src)
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QBrush(QColor("#64b5f6")))
            item.setFont(QFont("Consolas", 11))
            self.result_table.setItem(i, 1, item)

            # 查找该来源模块码对应的物料，如果是模组码则显示绑定码
            bind_code = ""
            for m in self.material_list:
                if m.get("productCode") == src and "模组码" in m.get("materialName", ""):
                    mno = m.get("materialNo", "")
                    bind_code = self.bind_code_map.get(mno, "")
                    break
            item = QTableWidgetItem(bind_code)
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QBrush(QColor("#00e676")))
            item.setFont(QFont("Consolas", 11, QFont.Bold))
            self.result_table.setItem(i, 2, item)

    def reset(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(1000)
        self.module_codes = []
        self.generated_codes = []
        self.material_list = []
        self.bind_code_map = {}
        self.source_table.setRowCount(0)
        self.result_table.setRowCount(0)
        self.generate_btn.setEnabled(False)
        self.status_label.setText("等待单物料校验完成...")
        self.status_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #78909c;")
