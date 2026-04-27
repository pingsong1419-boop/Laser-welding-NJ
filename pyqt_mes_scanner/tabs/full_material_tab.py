# -*- coding: utf-8 -*-
"""全物料校验模块 —— 对单物料校验通过的模组码进行汇总 API 校验，成功后自动触发上传"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QColor, QBrush, QFont


from services.mes_service import MesService


class FullMaterialWorker(QThread):
    finished = pyqtSignal(bool, str, dict)
    log = pyqtSignal(str, str)
    api_record = pyqtSignal(dict)

    def __init__(self, url, payload):
        super().__init__()
        self.url = url
        self.payload = payload

    def run(self):
        res_data = {}
        try:
            import time
            from datetime import datetime
            self.log.emit("info", f"[全物料校验] POST {self.url}")
            start = time.time()
            res_data = MesService.check_full_material(self.url, self.payload)
            dur = int((time.time() - start) * 1000)
            code = res_data.get("code", 200)
            status = "success" if MesService._is_success(res_data) else "error"
            self.api_record.emit({
                "title": "全物料校验",
                "url": self.url,
                "status": status,
                "time": datetime.now().strftime("%H:%M:%S"),
                "duration": dur,
                "reqBody": self.payload,
                "resBody": res_data
            })
            if code == 200:
                self.finished.emit(True, "", res_data)
            else:
                msg = res_data.get("message", f"业务码 {code}")
                self.finished.emit(False, msg, res_data)
        except Exception as e:
            self.api_record.emit({
                "title": "全物料校验",
                "url": self.url,
                "status": "error",
                "time": datetime.now().strftime("%H:%M:%S"),
                "duration": 0,
                "reqBody": self.payload,
                "resBody": {"error": str(e)}
            })
            self.finished.emit(False, str(e), res_data)


class FullMaterialTab(QWidget):
    complete = pyqtSignal()
    log = pyqtSignal(str, str)
    api_record = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._materials = []
        self._generated = []
        self._order_info = None
        self._config = {}
        self._worker = None
        self._setup_ui()

    def set_config(self, config):
        self._config = config or {}

    def set_order_info(self, order_info):
        self._order_info = order_info

    def set_data(self, materials, generated):
        """绑定流程：单物料校验结果 + 生成模组码结果"""
        self._materials = materials or []
        self._generated = generated or []
        self._packing_mode = False
        self._refresh_module_codes()
        self._refresh_generated()
        self._start_check()

    def set_packing_data(self, module_list, pack_code=""):
        """入箱流程：入箱的模组码列表 + PACK箱体码"""
        self._packing_mode = True
        self._packing_modules = module_list or []
        self._pack_code = pack_code
        self._refresh_packing_modules()
        self._start_check()

    def reset(self):
        self._materials = []
        self._generated = []
        self._packing_modules = []
        self._pack_code = ""
        self._packing_mode = False
        self._order_info = None
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker = None
        self.status_label.setText("等待数据...")
        self.status_label.setStyleSheet("color: #78909c; font-size: 15px; font-weight: 600;")
        self.result_label.setText("")
        self.module_table.setRowCount(0)
        self.generated_text.setText("暂无")

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 标题
        title = QLabel("🔍 全物料校验")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #90caf9;")
        layout.addWidget(title)

        # 状态
        self.status_label = QLabel("等待数据...")
        self.status_label.setStyleSheet("color: #78909c; font-size: 15px; font-weight: 600;")
        layout.addWidget(self.status_label)

        # 模组码列表（从PLC/单物料校验获取）
        module_title = QLabel("📋 已校验通过的模组码")
        module_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #90caf9;")
        layout.addWidget(module_title)

        self.module_table = QTableWidget()
        self.module_table.setColumnCount(2)
        self.module_table.setHorizontalHeaderLabels(["序号", "模组码"])
        self.module_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.module_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.module_table.setColumnWidth(0, 60)
        self.module_table.verticalHeader().setVisible(False)
        self.module_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.module_table.setShowGrid(False)
        for i in range(2):
            item = self.module_table.horizontalHeaderItem(i)
            if item:
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                item.setForeground(QBrush(QColor("#90caf9")))
                item.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.module_table.setStyleSheet("""
            QTableWidget {
                background: transparent;
                border: 1px solid rgba(100,181,246,0.15);
                border-radius: 6px;
                font-size: 14px;
            }
            QTableWidget::item {
                color: #cfd8dc;
                padding: 8px 12px;
                border-bottom: 1px solid rgba(100,181,246,0.05);
            }
            QHeaderView::section {
                background: rgba(21,101,192,0.2);
                color: #90caf9;
                font-weight: 700;
                font-size: 12px;
                padding: 6px 12px;
                min-height: 28px;
                border: none;
            }
        """)
        layout.addWidget(self.module_table, stretch=1)

        # 校验结果
        result_title = QLabel("📊 全物料校验结果")
        result_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #90caf9; margin-top: 8px;")
        layout.addWidget(result_title)

        self.result_label = QLabel("尚未进行校验")
        self.result_label.setStyleSheet("color: #78909c; font-size: 13px; padding: 6px;")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        # 已生成模组绑定码
        codes_title = QLabel("🏷️ 已生成模组绑定码")
        codes_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #90caf9; margin-top: 8px;")
        layout.addWidget(codes_title)

        self.generated_text = QLabel("暂无")
        self.generated_text.setStyleSheet("color: #e0e6ed; font-size: 13px; font-family: Consolas, monospace; padding: 6px;")
        self.generated_text.setWordWrap(True)
        layout.addWidget(self.generated_text)

    def _refresh_module_codes(self):
        module_codes = [m.get("productCode", "") for m in self._materials if m.get("productCode")]
        self.module_table.setRowCount(len(module_codes))
        for i, code in enumerate(module_codes):
            idx_item = QTableWidgetItem(str(i + 1))
            idx_item.setTextAlignment(Qt.AlignCenter)
            idx_item.setForeground(QBrush(QColor("#90caf9")))
            self.module_table.setItem(i, 0, idx_item)

            code_item = QTableWidgetItem(code)
            code_item.setTextAlignment(Qt.AlignCenter)
            code_item.setForeground(QBrush(QColor("#e0e6ed")))
            code_item.setFont(QFont("Consolas", 12))
            self.module_table.setItem(i, 1, code_item)

    def _refresh_packing_modules(self):
        """入箱流程：显示入箱的模组码"""
        module_codes = [m.get("moduleCode", "") for m in self._packing_modules if m.get("moduleCode")]
        self.module_table.setRowCount(len(module_codes))
        for i, code in enumerate(module_codes):
            idx_item = QTableWidgetItem(str(i + 1))
            idx_item.setTextAlignment(Qt.AlignCenter)
            idx_item.setForeground(QBrush(QColor("#90caf9")))
            self.module_table.setItem(i, 0, idx_item)

            code_item = QTableWidgetItem(code)
            code_item.setTextAlignment(Qt.AlignCenter)
            code_item.setForeground(QBrush(QColor("#e0e6ed")))
            code_item.setFont(QFont("Consolas", 12))
            self.module_table.setItem(i, 1, code_item)

    def _refresh_generated(self):
        if self._generated:
            codes = "  ".join([r.get("moduleCode", "") for r in self._generated])
            self.generated_text.setText(codes)
        else:
            self.generated_text.setText("暂无")

    def _start_check(self):
        url = self._config.get("fullMaterialCheckUrl", "").strip()
        if not url:
            self.log.emit("info", "[全物料校验] 未配置校验接口，跳过校验直接上传")
            self.status_label.setText("未配置校验接口，跳过")
            self.status_label.setStyleSheet("color: #ffab40; font-size: 15px; font-weight: 600;")
            self.result_label.setText("未配置全物料校验接口，已跳过")
            self.complete.emit()
            return

        order = self._order_info or {}

        # 根据流程类型选择工序编码
        if self._packing_mode:
            process_code = self._config.get("packingProcessCode", "")
        else:
            process_code = self._config.get("moduleBindProcessCode", "")

        material_list = []
        if self._packing_mode:
            # 入箱流程：使用校验通过的模组码列表
            for m in self._packing_modules:
                code = m.get("moduleCode", "")
                if code:
                    material_list.append({"ProductCode": code, "ProductCount": 1})
            # 入箱流程：将PACK箱体码也加入MaterialList
            if getattr(self, '_pack_code', ''):
                material_list.append({"ProductCode": self._pack_code, "ProductCount": 1})
        else:
            # 绑定流程：使用单物料校验结果
            for m in self._materials:
                code = m.get("productCode", "")
                material_name = m.get("materialName", "")
                # 模组码物料使用生成的绑定码参与全物料校验
                if code and "模组码" in material_name:
                    for rec in self._generated:
                        if rec.get("sourceCode") == code or rec.get("materialNo") == code:
                            bind_code = rec.get("bindCode")
                            if bind_code:
                                code = bind_code
                            break
                if code:
                    material_list.append({"ProductCode": code, "ProductCount": 1})

        payload = {
            "ProduceOrderCode": order.get("orderCode", ""),
            "RouteNo": order.get("route_No", "") or order.get("routeCode", ""),
            "TechnicsProcessCode": process_code,
            "TenantID": self._config.get("tenantID", ""),
            "ProductMixCode": order.get("productMixCode") or order.get("specsCode") or order.get("specCode") or "",
            "ProductLine": None,
            "MaterialList": material_list
        }

        self.status_label.setText("正在校验...")
        self.status_label.setStyleSheet("color: #ffab40; font-size: 15px; font-weight: 600;")
        self.result_label.setText("正在发送全物料校验请求...")

        self._worker = FullMaterialWorker(url, payload)
        self._worker.log.connect(self.log.emit)
        self._worker.api_record.connect(self.api_record.emit)
        self._worker.finished.connect(self._on_check_finished)
        self._worker.start()

    def _on_check_finished(self, ok, msg, res_data):
        if ok:
            self.status_label.setText("✅ 全物料校验通过")
            self.status_label.setStyleSheet("color: #00e676; font-size: 15px; font-weight: 600;")
            self.result_label.setText(f"校验通过\n接口返回: {res_data}")
            self.result_label.setStyleSheet("color: #00e676; font-size: 13px; padding: 6px;")
            self.log.emit("success", "[全物料校验] 校验通过，自动触发上传")
            self.complete.emit()
        else:
            self.status_label.setText("❌ 全物料校验失败")
            self.status_label.setStyleSheet("color: #ff5252; font-size: 15px; font-weight: 600;")
            self.result_label.setText(f"校验失败: {msg}\n接口返回: {res_data}")
            self.result_label.setStyleSheet("color: #ff5252; font-size: 13px; padding: 6px;")
            self.log.emit("error", f"[全物料校验] 失败: {msg}")
            QMessageBox.warning(self, "全物料校验失败", f"校验未通过，请检查后重试。\n\n原因: {msg}")
