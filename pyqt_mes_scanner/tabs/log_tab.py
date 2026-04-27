# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor


class LogEntryWidget(QWidget):
    def __init__(self, time_str, level, msg, parent=None):
        super().__init__(parent)
        color_map = {
            "success": "#69f0ae",
            "error": "#ff5252",
            "warn": "#ffab40",
            "info": "#78909c"
        }
        color = color_map.get(level, "#78909c")
        self.setStyleSheet(f"""
            LogEntryWidget {{
                background: rgba(255,255,255,0.02);
                border-radius: 4px;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: #455a64; font-size: 13px; min-width: 70px;")
        layout.addWidget(time_label)

        msg_label = QLabel(msg)
        msg_label.setStyleSheet(f"color: {color}; font-size: 13px; word-break: break-all;")
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label, stretch=1)


class LogTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logs = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setSpacing(3)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

        self.empty_label = QLabel("暂无日志")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #37474f; font-size: 14px; padding: 16px;")
        self.scroll_layout.addWidget(self.empty_label)

    def add_log(self, level, msg):
        from datetime import datetime
        time_str = datetime.now().strftime("%H:%M:%S")
        self.logs.insert(0, {"time": time_str, "level": level, "msg": msg})
        if len(self.logs) > 50:
            self.logs.pop()
        self._refresh()

    def clear_logs(self):
        self.logs = []
        self._refresh()

    def _refresh(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.logs:
            self.empty_label = QLabel("暂无日志")
            self.empty_label.setAlignment(Qt.AlignCenter)
            self.empty_label.setStyleSheet("color: #37474f; font-size: 14px; padding: 16px;")
            self.scroll_layout.addWidget(self.empty_label)
            return

        for entry in self.logs:
            w = LogEntryWidget(entry["time"], entry["level"], entry["msg"])
            self.scroll_layout.addWidget(w)

        self.scroll_layout.addStretch()
