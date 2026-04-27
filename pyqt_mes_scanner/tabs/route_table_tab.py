# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush, QFont


class RouteTableTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("route_table_tab")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 头部
        header = QHBoxLayout()
        header.setSpacing(8)
        icon = QLabel("📋")
        icon.setStyleSheet("font-size: 16px;")
        title = QLabel("工步工序列表")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #90caf9;")
        self.count_badge = QLabel("")
        self.count_badge.setStyleSheet(
            "background: rgba(66,165,245,0.12); color: #42a5f5; padding: 2px 12px;"
            "border-radius: 20px; font-size: 13px;"
        )
        header.addWidget(icon)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.count_badge)
        layout.addLayout(header)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            "序号", "工步编码", "工步名称"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        for i in range(3):
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
                color: #cfd8dc;
                padding: 6px 10px;
                border-bottom: 1px solid rgba(100,181,246,0.05);
            }
            QTableWidget::item:selected {
                background: rgba(66,165,245,0.1);
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

        # 错误显示区域
        self.error_widget = QWidget()
        self.error_widget.setStyleSheet("""
            QWidget {
                background: rgba(244,67,54,0.08);
                border: 1px solid rgba(255,82,82,0.3);
                border-radius: 8px;
                margin: 8px 0;
            }
        """)
        err_layout = QVBoxLayout(self.error_widget)
        err_layout.setSpacing(6)
        err_layout.setContentsMargins(12, 12, 12, 12)
        self.error_title = QLabel("")
        self.error_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ff5252;")
        err_layout.addWidget(self.error_title)
        self.error_msg = QLabel("")
        self.error_msg.setStyleSheet("font-size: 14px; color: #ff8a80;")
        self.error_msg.setWordWrap(True)
        err_layout.addWidget(self.error_msg)
        self.error_widget.setVisible(False)
        layout.addWidget(self.error_widget)

        # 空状态
        self.empty_label = QLabel("暂无工步数据")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #37474f; font-size: 15px; padding: 40px;")
        self.empty_label.setVisible(True)
        self.table.setVisible(False)
        layout.addWidget(self.empty_label)

    def show_error(self, title, message):
        self.error_title.setText(f"❌ {title}")
        self.error_msg.setText(message)
        self.error_widget.setVisible(True)
        self.empty_label.setVisible(False)
        self.table.setVisible(False)
        self.count_badge.setText("")

    def clear_error(self):
        self.error_widget.setVisible(False)

    def set_data(self, steps):
        self.clear_error()
        self.table.setRowCount(0)
        if not steps:
            self.empty_label.setVisible(True)
            self.table.setVisible(False)
            self.count_badge.setText("")
            return

        self.empty_label.setVisible(False)
        self.table.setVisible(True)

        # 扁平化工步数据：只解析收到的报文，不做字段转换
        rows = []
        total_sub = 0
        for si, seq in enumerate(steps):
            ws_list = seq.get("workStepList", []) or []
            if not ws_list:
                rows.append({"seq_idx": si, "ws": seq})
            else:
                for wi, ws in enumerate(ws_list):
                    total_sub += 1
                    rows.append({"seq_idx": si, "ws_idx": wi, "ws": ws})

        self.count_badge.setText(f"{len(steps)} 工步 / {total_sub} 子步骤")
        self.table.setRowCount(len(rows))

        for i, row in enumerate(rows):
            ws = row["ws"]
            # 序号（纯行号）
            item = QTableWidgetItem(str(i + 1))
            item.setTextAlignment(Qt.AlignCenter)
            item.setFont(QFont("Consolas", 10, QFont.Bold))
            item.setForeground(QBrush(QColor("#e3f2fd")))
            self.table.setItem(i, 0, item)
            # 工步编码 (workstepNo)
            code = ws.get("workstepNo", "—")
            item = QTableWidgetItem(str(code))
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QBrush(QColor("#64b5f6")))
            item.setFont(QFont("Consolas", 11))
            self.table.setItem(i, 1, item)
            # 工步名称 (workstepName)
            name = ws.get("workstepName", "—")
            item = QTableWidgetItem(str(name))
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QBrush(QColor("#e0e6ed")))
            self.table.setItem(i, 2, item)
