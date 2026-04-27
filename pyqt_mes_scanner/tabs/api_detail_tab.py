# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTextEdit, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
import json


class ApiRecordCard(QFrame):
    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record = record
        self.expanded = True
        self._setup_ui()

    def _setup_ui(self):
        status = self.record.get("status", "pending")
        border_color = {
            "success": "rgba(0,200,83,0.2)",
            "error": "rgba(244,67,54,0.25)",
            "pending": "rgba(100,181,246,0.1)"
        }.get(status, "rgba(100,181,246,0.1)")

        self.setStyleSheet(f"""
            ApiRecordCard {{
                background: #0d1117;
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
        """)
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(12, 12, 12, 12)
        header.setSpacing(8)

        dot_color = {"success": "#00e676", "error": "#ff5252", "pending": "#ffab40"}.get(status, "#ffab40")
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {dot_color}; font-size: 12px;")
        header.addWidget(dot)

        title = QLabel(self.record.get("title", ""))
        title.setStyleSheet("font-size: 14px; font-weight: 600; color: #cfd8dc;")
        header.addWidget(title, stretch=1)

        time_label = QLabel(self.record.get("time", ""))
        time_label.setStyleSheet("font-size: 12px; color: #455a64;")
        header.addWidget(time_label)

        dur = self.record.get("duration")
        if dur is not None:
            dur_label = QLabel(f"{dur}ms")
            dur_label.setStyleSheet("font-size: 12px; color: #42a5f5; background: rgba(66,165,245,0.1); padding: 1px 6px; border-radius: 10px;")
            header.addWidget(dur_label)

        status_text = {"success": "成功", "error": "失败", "pending": "请求中"}.get(status, "未知")
        status_label = QLabel(status_text)
        sc = {"success": "rgba(0,200,83,0.12); color: #00e676",
              "error": "rgba(244,67,54,0.12); color: #ff5252",
              "pending": "rgba(255,171,64,0.12); color: #ffab40"}.get(status)
        status_label.setStyleSheet(f"font-size: 12px; padding: 1px 8px; border-radius: 10px; font-weight: 600; background: {sc};")
        header.addWidget(status_label)

        self.toggle_btn = QLabel("▼" if self.expanded else "▶")
        self.toggle_btn.setStyleSheet("font-size: 12px; color: #546e7a; cursor: pointer;")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.mousePressEvent = lambda e: self._toggle()
        header.addWidget(self.toggle_btn)

        header_w = QWidget()
        header_w.setLayout(header)
        header_w.setStyleSheet("background: rgba(255,255,255,0.02);")
        header_w.setCursor(Qt.PointingHandCursor)
        header_w.mousePressEvent = lambda e: self._toggle()
        layout.addWidget(header_w)

        # Body
        self.body = QWidget()
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(14, 10, 14, 14)
        body_layout.setSpacing(10)

        # URL
        url_row = QHBoxLayout()
        method = QLabel("POST")
        method.setStyleSheet("background: rgba(21,101,192,0.3); color: #64b5f6; font-size: 12px; font-weight: 700; padding: 2px 7px; border-radius: 3px;")
        url_row.addWidget(method)
        url_text = QLabel(self.record.get("url", ""))
        url_text.setStyleSheet("font-size: 13px; color: #78909c; font-family: Consolas, monospace; word-break: break-all;")
        url_text.setWordWrap(True)
        url_row.addWidget(url_text, stretch=1)
        body_layout.addLayout(url_row)

        # 请求参数
        req_title = QLabel("📤 请求参数")
        req_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #546e7a;")
        body_layout.addWidget(req_title)

        req_body = self.record.get("reqBody", {})
        req_edit = QTextEdit()
        req_edit.setPlainText(json.dumps(req_body, ensure_ascii=False, indent=2))
        req_edit.setReadOnly(True)
        req_edit.setMaximumHeight(200)
        req_edit.setStyleSheet("""
            QTextEdit {
                background: #060a10;
                border: 1px solid rgba(100,181,246,0.1);
                border-radius: 6px;
                padding: 10px;
                font-family: Consolas, monospace;
                font-size: 14px;
                color: #80cbc4;
            }
        """)
        body_layout.addWidget(req_edit)

        # 响应数据
        res_title = QLabel("📥 响应数据")
        res_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #546e7a;")
        body_layout.addWidget(res_title)

        res_body = self.record.get("resBody")
        res_edit = QTextEdit()
        if res_body is not None:
            try:
                res_edit.setPlainText(json.dumps(res_body, ensure_ascii=False, indent=2))
            except Exception:
                res_edit.setPlainText(str(res_body))
        else:
            res_edit.setPlainText("等待响应...")
        res_edit.setReadOnly(True)
        res_edit.setMaximumHeight(200)
        res_color = "#ef9a9a" if status == "error" else "#a5d6a7"
        res_edit.setStyleSheet(f"""
            QTextEdit {{
                background: #060a10;
                border: 1px solid {'rgba(244,67,54,0.15)' if status == 'error' else 'rgba(100,181,246,0.1)'};
                border-radius: 6px;
                padding: 10px;
                font-family: Consolas, monospace;
                font-size: 14px;
                color: {res_color};
            }}
        """)
        body_layout.addWidget(res_edit)

        layout.addWidget(self.body)
        self.body.setVisible(self.expanded)

    def _toggle(self):
        self.expanded = not self.expanded
        self.body.setVisible(self.expanded)
        self.toggle_btn.setText("▼" if self.expanded else "▶")


class ApiDetailTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 头部
        header = QHBoxLayout()
        header.setSpacing(8)
        icon = QLabel("🔌")
        icon.setStyleSheet("font-size: 16px;")
        title = QLabel("接口交互详情")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #90caf9;")
        header.addWidget(icon)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # 滚动区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

        self.empty_label = QLabel("暂无交互记录，请先开始操作")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #37474f; font-size: 15px; padding: 40px;")
        self.scroll_layout.addWidget(self.empty_label)

    def set_records(self, records):
        self.records = records
        # 清空
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not records:
            self.empty_label = QLabel("暂无交互记录，请先开始操作")
            self.empty_label.setAlignment(Qt.AlignCenter)
            self.empty_label.setStyleSheet("color: #37474f; font-size: 15px; padding: 40px;")
            self.scroll_layout.addWidget(self.empty_label)
            return

        for rec in records:
            card = ApiRecordCard(rec)
            self.scroll_layout.addWidget(card)

        self.scroll_layout.addStretch()
