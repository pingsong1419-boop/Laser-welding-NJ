# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QColor, QBrush, QFont


from services.mes_service import MesService


class SingleCheckWorker(QThread):
    finished = pyqtSignal(bool, str, dict, object)
    log = pyqtSignal(str, str)
    api_record = pyqtSignal(dict)

    def __init__(self, url, payload, target, code):
        super().__init__()
        self.url = url
        self.payload = payload
        self.target = target
        self.code = code

    def run(self):
        try:
            self.log.emit("info", f"[单物料校验] POST {self.url}")
            res_data = MesService.check_single_material(self.url, self.payload)
            self.api_record.emit({
                "title": "单物料校验",
                "url": self.url,
                "status": "success" if MesService._is_success(res_data) else "error",
                "reqBody": self.payload,
                "resBody": res_data
            })
            if MesService._is_success(res_data):
                self.finished.emit(True, "", res_data, self.target)
            else:
                err_msg = res_data.get("message", f"业务码 {res_data.get('code')}")
                self.finished.emit(False, err_msg, res_data, self.target)
        except Exception as e:
            self.api_record.emit({
                "title": "单物料校验",
                "url": self.url,
                "status": "error",
                "reqBody": self.payload,
                "resBody": {"error": str(e)}
            })
            self.finished.emit(False, str(e), {}, self.target)


class MaterialScannerTab(QWidget):
    complete = pyqtSignal(list)
    single_complete = pyqtSignal(dict)
    log = pyqtSignal(str, str)
    api_record = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task_list = []
        self.order_info = None
        self.product_code = ""
        self.config = {}
        self._setup_ui()

    def set_order_info(self, order_info):
        self.order_info = order_info

    def set_product_code(self, code):
        self.product_code = str(code or "").strip().upper()

    def set_config(self, config):
        self.config = config or {}

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部操作栏
        action_bar = QHBoxLayout()
        action_bar.setContentsMargins(12, 12, 12, 12)
        action_bar.setSpacing(12)
        action_bar.setAlignment(Qt.AlignLeft)

        input_wrap = QHBoxLayout()
        input_wrap.setSpacing(0)
        input_wrap.setContentsMargins(4, 4, 4, 4)
        icon = QLabel("扫描")
        icon.setStyleSheet("color: #78909c; margin: 0 8px; font-size: 14px;")
        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText("请使用扫描枪扫描物料条码以验证组件...")
        self.scan_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #e3f2fd;
                font-size: 16px;
                padding: 4px;
            }
        """)
        self.scan_input.returnPressed.connect(self._handle_scan)
        self.submit_btn = QPushButton("验证")
        self.submit_btn.setStyleSheet("""
            QPushButton {
                background: #1976d2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 14px;
                font-weight: 600;
            }
            QPushButton:hover { background: #1565c0; }
            QPushButton:disabled { background: #37474f; color: #78909c; }
        """)
        self.submit_btn.clicked.connect(self._handle_scan)

        input_container = QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background: #0d1117;
                border: 1px solid rgba(100,181,246,0.3);
                border-radius: 6px;
            }
        """)
        ic_layout = QHBoxLayout(input_container)
        ic_layout.setContentsMargins(4, 2, 4, 2)
        ic_layout.setSpacing(0)
        ic_layout.addWidget(icon)
        ic_layout.addWidget(self.scan_input)
        ic_layout.addWidget(self.submit_btn)

        action_bar.addWidget(input_container, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        action_bar.addWidget(self.status_label)

        action_widget = QWidget()
        action_widget.setLayout(action_bar)
        action_widget.setStyleSheet("background: rgba(13,71,161,0.15); border-bottom: 1px solid rgba(100,181,246,0.1);")
        layout.addWidget(action_widget)

        # 空状态
        self.empty_label = QLabel("当前工步无模组绑定信息，无需校验。")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #546e7a; font-size: 15px; padding: 40px;")
        layout.addWidget(self.empty_label)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "序号", "物料编号", "物料名称", "需求数", "条码长度", "追溯类型", "已校验数", "状态", "已匹配模块码"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.Stretch)
        self.table.horizontalHeader().setMinimumSectionSize(100)
        # 固定宽度列初始值（适应14px字体）
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 100)
        self.table.setColumnWidth(6, 100)
        self.table.setColumnWidth(7, 100)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setShowGrid(False)
        for i in range(9):
            item = self.table.horizontalHeaderItem(i)
            if item:
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                item.setForeground(QBrush(QColor("#90caf9")))
                item.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.table.setStyleSheet("""
            QTableWidget {
                background: transparent;
                border: none;
                font-size: 14px;
            }
            QTableWidget::item {
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
                border-bottom: 1px solid rgba(100,181,246,0.1);
            }
        """)
        layout.addWidget(self.table)
        self.table.setVisible(False)

    def set_steps(self, steps):
        self.task_list = []
        uid = 0
        for si, seq in enumerate(steps):
            ws_list = seq.get("workStepList", []) or []
            for ws in ws_list:
                mats = ws.get("workStepMaterialList", []) or []
                for mat in mats:
                    req_num = int(mat.get("material_number") or 0)
                    mno = str(mat.get("material_No") or "").strip()
                    if not mno or req_num <= 0:
                        continue
                    # 根据需求数展开为多个独立任务
                    for idx in range(req_num):
                        self.task_list.append({
                            "uid": f"mat-{uid}-{idx}",
                            "seq_idx": si + 1,
                            "material_No": mno,
                            "material_Name": str(mat.get("material_Name", "")),
                            "material_number": 1,
                            "noLength": int(mat.get("noLength") or 0),
                            "retrospect_Type": mat.get("retrospect_Type"),
                            "scannedBarcode": "",
                            "status": "pending"
                        })
                    uid += 1

        # 模组码无需手动扫描校验，本地自动标记为已完成
        for t in self.task_list:
            mno = t["material_No"].upper()
            material_Name = t["material_Name"]
            if "模组码" in material_Name:
                t["status"] = "completed"
                t["scannedBarcode"] = t["material_No"]
                t["isModuleCode"] = True

        self._refresh_table()
        
        # 自动为国标码发起一次真实的线上单物料校验 API 请求，使其产生日志
        if getattr(self, "product_code", ""):
            self._auto_check_national_code(self.product_code)

        if self.task_list:
            self.scan_input.setFocus()

    def _auto_check_national_code(self, code):
        if not code:
            return
            
        target = None
        for t in self.task_list:
            if t["status"] == "completed":
                continue
            if "国标码" in t["material_Name"]:
                target = t
                break
                
        if not target:
            return

        url = self.config.get("singleMaterialApiUrl", "")
        payload = {
            "produceOrderCode": self.order_info.get("orderCode", "") if self.order_info else "",
            "routeNo": self.order_info.get("routeCode", "") or self.order_info.get("route_No", "") if self.order_info else "",
            "technicsProcessCode": self.config.get("technicsProcessCode", ""),
            "materialCode": code,
            "tenantID": self.config.get("tenantID", "")
        }

        self.scan_input.setEnabled(False)
        self.submit_btn.setEnabled(False)

        self.check_worker = SingleCheckWorker(url, payload, target, code)
        self.check_worker.log.connect(self.log.emit)
        self.check_worker.api_record.connect(self.api_record.emit)
        self.check_worker.finished.connect(self._on_scan_finished)
        self.check_worker.start()

    def _refresh_table(self):
        if not self.task_list:
            self.empty_label.setVisible(True)
            self.table.setVisible(False)
            self.status_label.setText("")
            return

        self.empty_label.setVisible(False)
        self.table.setVisible(True)
        completed = sum(1 for t in self.task_list if t["status"] == "completed")
        total = len(self.task_list)

        if completed >= total:
            self.status_label.setText("全部验证通过")
            self.status_label.setStyleSheet("color: #00e676; font-size: 15px; font-weight: 600;")
            self.scan_input.setEnabled(False)
            self.submit_btn.setEnabled(False)
        else:
            self.status_label.setText(f"等待验证 ({completed}/{total})")
            self.status_label.setStyleSheet("color: #ffab40; font-size: 15px; font-weight: 600;")
            self.scan_input.setEnabled(True)
            self.submit_btn.setEnabled(True)

        self.table.clearContents()
        self.table.setRowCount(len(self.task_list))
        for i, task in enumerate(self.task_list):
            # 序号
            item = QTableWidgetItem(str(i + 1))
            item.setTextAlignment(Qt.AlignCenter)
            if task["status"] == "completed":
                item.setBackground(QBrush(QColor("#00e676")))
                item.setData(Qt.ForegroundRole, QColor("#000000"))
            else:
                item.setData(Qt.ForegroundRole, QColor("#90caf9"))
            self.table.setItem(i, 0, item)

            # 物料编号
            item = QTableWidgetItem(task["material_No"])
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.ForegroundRole, QColor("#64b5f6"))
            item.setFont(QFont("Consolas", 11))
            self.table.setItem(i, 1, item)

            # 物料名称
            name = task["material_Name"]
            item = QTableWidgetItem(name)
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.ForegroundRole, QColor("#e0e6ed"))
            item.setToolTip(name)
            self.table.setItem(i, 2, item)

            # 需求数
            item = QTableWidgetItem(str(task["material_number"]))
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.ForegroundRole, QColor("#90caf9"))
            item.setFont(QFont("Consolas", 11, QFont.Bold))
            self.table.setItem(i, 3, item)

            # 条码长度
            nl = task["noLength"]
            item = QTableWidgetItem(str(nl) if nl > 0 else "-")
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.ForegroundRole, QColor("#cfd8dc"))
            self.table.setItem(i, 4, item)

            # 追溯类型
            item = QTableWidgetItem(str(task["retrospect_Type"] or "-"))
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.ForegroundRole, QColor("#cfd8dc"))
            self.table.setItem(i, 5, item)

            # 已扫数量
            sc = 1 if task["status"] == "completed" else 0
            item = QTableWidgetItem(str(sc))
            item.setTextAlignment(Qt.AlignCenter)
            item.setFont(QFont("Consolas", 12, QFont.Bold))
            if task["status"] == "completed":
                item.setData(Qt.ForegroundRole, QColor("#00e676"))
            else:
                item.setData(Qt.ForegroundRole, QColor("#78909c"))
            self.table.setItem(i, 6, item)

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
            self.table.setItem(i, 7, item)

            # 已匹配条码
            item = QTableWidgetItem(task.get("scannedBarcode", ""))
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.ForegroundRole, QColor("#80cbc4"))
            item.setFont(QFont("Consolas", 10))
            self.table.setItem(i, 8, item)

        self.table.viewport().update()

        # 根据最长物料名称计算列2宽度
        max_len = 6
        font_metrics = self.table.fontMetrics()
        for task in self.task_list:
            text_width = font_metrics.horizontalAdvance(task["material_Name"])
            max_len = max(max_len, text_width)
        self.table.setColumnWidth(2, max_len + 40)

    def _handle_scan(self):
        code = self.scan_input.text().strip().upper()
        if not code:
            return

        # 检查重复（跳过模组码，一个条码只能做一次校验）
        for t in self.task_list:
            if t.get("isModuleCode"):
                continue
            if t["scannedBarcode"] == code:
                self.log.emit("warn", f"条码重复，已清空当前条码: {code}")
                self.scan_input.clear()
                return

        # 前端匹配候选物料
        candidates = []
        for t in self.task_list:
            if t["status"] == "completed":
                continue
            prefix = t["material_No"].upper()
            if not prefix or not code.startswith(prefix):
                continue
            if t["noLength"] > 0 and len(code) < t["noLength"]:
                continue
            candidates.append(t)

        candidates.sort(key=lambda x: len(x["material_No"]), reverse=True)
        target = candidates[0] if candidates else None

        if not target:
            self.log.emit("error", f"无匹配物料或该物料已扫完: {code}")
            self._show_alert("❌ 校验失败", f"条码 [{code}]\n无匹配物料或该物料已扫完")
            self.scan_input.clear()
            return

        url = self.config.get("singleMaterialApiUrl", "")
        payload = {
            "produceOrderCode": self.order_info.get("orderCode", "") if self.order_info else "",
            "routeNo": self.order_info.get("routeCode", "") or self.order_info.get("route_No", "") if self.order_info else "",
            "technicsProcessCode": self.config.get("technicsProcessCode", ""),
            "materialCode": code,
            "tenantID": self.config.get("tenantID", "")
        }

        self.scan_input.setEnabled(False)
        self.submit_btn.setEnabled(False)

        self.check_worker = SingleCheckWorker(url, payload, target, code)
        self.check_worker.log.connect(self.log.emit)
        self.check_worker.api_record.connect(self.api_record.emit)
        self.check_worker.finished.connect(self._on_scan_finished)
        self.check_worker.start()

    def _on_scan_finished(self, success, err_msg, res_data, target):
        self.scan_input.setEnabled(True)
        self.submit_btn.setEnabled(True)
        code = self.check_worker.code

        if not success:
            self.log.emit("error", f"[单物料校验] 失败: {err_msg}")
            self._show_alert("❌ 单物料校验失败", f"条码: {code}\n{err_msg}")
            self.scan_input.clear()
            self.scan_input.setFocus()
            return

        self.log.emit("success", f"[单物料校验] 通过: {target['material_Name']}")
        target["scannedBarcode"] = code
        target["status"] = "completed"
        self.log.emit("success", f"物料扫描匹配成功: {target['material_Name']} ({code})")

        self.single_complete.emit({"productCode": code, "productCount": 1})
        self.scan_input.clear()
        self.scan_input.setFocus()

        self._refresh_table()

        if all(t["status"] == "completed" for t in self.task_list):
            self.log.emit("success", "所有物料校验已全部通过")
            payload_all = []
            for t in self.task_list:
                if t["scannedBarcode"]:
                    payload_all.append({"productCode": t["scannedBarcode"], "productCount": 1, "materialNo": t["material_No"], "materialName": t["material_Name"]})
            self.complete.emit(payload_all)



    def _show_alert(self, title, message):
        """深色风格弹窗，与主界面保持一致"""
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setMinimumWidth(360)
        dlg.setStyleSheet("""
            QDialog {
                background: #0a0e1a;
                border: 1px solid rgba(100,181,246,0.2);
                border-radius: 10px;
            }
            QLabel {
                color: #e0e6ed;
                font-size: 15px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1565c0, stop:1 #0d47a1);
                border: none;
                border-radius: 6px;
                color: #e3f2fd;
                padding: 8px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976d2, stop:1 #1565c0);
            }
        """)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        msg = QLabel(message)
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #ff8a80; font-size: 15px; padding: 8px 0;")
        layout.addWidget(msg)

        btn = QPushButton("确定")
        btn.clicked.connect(dlg.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

        dlg.exec_()

    def reset(self):
        self.task_list = []
        self.scan_input.clear()
        self.scan_input.setEnabled(True)
        self.submit_btn.setEnabled(True)
        self._refresh_table()
