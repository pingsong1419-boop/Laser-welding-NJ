# -*- coding: utf-8 -*-
"""
配置保存测试脚本
用法: cd pyqt_mes_scanner && python test_config.py
"""
import sys, traceback
from PyQt5.QtWidgets import QApplication, QPushButton
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtTest import QTest

app = QApplication(sys.argv)

print("[1/5] 导入 MainWindow...")
from main_window import MainWindow
w = MainWindow()
print("[2/5] 创建 MainWindow 成功")

from dialogs.config_dialog import ConfigDialog
from PyQt5.QtWidgets import QDialog

def run_test():
    print("[3/5] 打开配置对话框...")
    dlg = ConfigDialog(w.config, w)
    
    def click_save():
        print("[4/5] 点击保存按钮...")
        try:
            save_btn = dlg.findChild(QPushButton, "btn_save")
            if save_btn:
                QTest.mouseClick(save_btn, Qt.LeftButton)
            
            print(f"    对话框结果: {dlg.result()}")
            if dlg.result() == QDialog.Accepted:
                new_cfg = dlg.get_config()
                print(f"    配置键: {list(new_cfg.keys())}")
                w.config = new_cfg
                w.process_badge.setText(f"当前工序：{w.config['moduleBindProcessCode']}")
                w._add_log("info", "配置已保存")
                print("[5/5] ✅ 配置保存测试通过！")
            else:
                print("[5/5] ⚠️ 对话框未接受")
        except Exception as e:
            print(f"[5/5] ❌ 测试失败: {e}")
            traceback.print_exc()
        app.quit()
    
    QTimer.singleShot(300, click_save)
    dlg.exec_()

QTimer.singleShot(500, run_test)
app.exec_()
