# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QWidget
)
from PyQt5.QtCore import Qt


class LoginDialog(QDialog):
    def __init__(self, admin_user="admin", admin_pass="123", parent=None):
        super().__init__(parent)
        self.admin_user = admin_user
        self.admin_pass = admin_pass
        self.authenticated = False
        self.setWindowTitle("管理权限验证")
        self.setFixedSize(400, 320)
        self._setup_ui()
        self.username_input.setText(admin_user)
        self.password_input.setFocus()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: #0a0e1a;
            }
            QLineEdit {
                background: #0d1117;
                border: 1px solid rgba(100,181,246,0.2);
                border-radius: 6px;
                color: white;
                padding: 10px 12px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border-color: #f44336;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(20, 20, 20, 20)
        header.setSpacing(12)
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b71c1c, stop:1 #d32f2f);
            border-bottom: 1px solid rgba(244,67,54,0.2);
        """)
        header_widget.setLayout(header)

        icon = QLabel("🔐")
        icon.setStyleSheet("font-size: 20px;")
        title = QLabel("管理权限验证")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: white;")
        header.addWidget(icon)
        header.addWidget(title)
        header.addStretch()
        layout.addWidget(header_widget)

        # Body
        body = QVBoxLayout()
        body.setContentsMargins(24, 24, 24, 24)
        body.setSpacing(16)

        hint = QLabel("该操作需要管理员权限，请验证身份：")
        hint.setStyleSheet("color: #90caf9; font-size: 15px;")
        body.addWidget(hint)

        user_layout = QVBoxLayout()
        user_layout.setSpacing(6)
        user_label = QLabel("账号")
        user_label.setStyleSheet("color: #546e7a; font-size: 14px; font-weight: 600;")
        user_layout.addWidget(user_label)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入管理员账号")
        self.username_input.returnPressed.connect(self._login)
        user_layout.addWidget(self.username_input)
        body.addLayout(user_layout)

        pass_layout = QVBoxLayout()
        pass_layout.setSpacing(6)
        pass_label = QLabel("密码")
        pass_label.setStyleSheet("color: #546e7a; font-size: 14px; font-weight: 600;")
        pass_layout.addWidget(pass_label)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.returnPressed.connect(self._login)
        pass_layout.addWidget(self.password_input)
        body.addLayout(pass_layout)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("""
            color: #ef5350;
            background: rgba(244,67,54,0.1);
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 14px;
        """)
        self.error_label.setVisible(False)
        body.addWidget(self.error_label)

        body.addStretch()
        layout.addLayout(body)

        # Footer
        footer = QHBoxLayout()
        footer.setContentsMargins(24, 16, 24, 16)
        footer.setSpacing(12)
        footer_widget = QWidget()
        footer_widget.setStyleSheet("background: rgba(0,0,0,0.2); border-top: 1px solid rgba(100,181,246,0.1);")
        footer_widget.setLayout(footer)

        cancel = QPushButton("取消")
        cancel.setStyleSheet("""
            background: transparent;
            border: 1px solid #455a64;
            color: #90a4ae;
            border-radius: 4px;
            padding: 8px 16px;
            cursor: pointer;
        """)
        cancel.clicked.connect(self.reject)

        confirm = QPushButton("验证并执行")
        confirm.setStyleSheet("""
            background: #d32f2f;
            border: none;
            color: white;
            font-weight: 600;
            border-radius: 4px;
            padding: 8px 20px;
            cursor: pointer;
        """)
        confirm.clicked.connect(self._login)
        confirm.setDefault(True)

        footer.addStretch()
        footer.addWidget(cancel)
        footer.addWidget(confirm)
        layout.addWidget(footer_widget)

    def _login(self):
        user = self.username_input.text().strip()
        pwd = self.password_input.text().strip()
        if user == self.admin_user and pwd == self.admin_pass:
            self.authenticated = True
            self.accept()
        else:
            self.error_label.setText("❌ 管理员用户名或密码错误")
            self.error_label.setVisible(True)

    def is_authenticated(self):
        return self.authenticated
