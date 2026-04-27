# -*- coding: utf-8 -*-
"""
全局 QSS 样式表 —— 复现 Vue 暗色主题
"""

MAIN_STYLE = """
/* ========== 全局 ========== */
QWidget {
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 16px;
    color: #c8d6e5;
    outline: none;
}
QMainWindow {
    background: #0a0e1a;
}
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: rgba(100, 181, 246, 0.25);
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(100, 181, 246, 0.4);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: rgba(100, 181, 246, 0.25);
    border-radius: 3px;
    min-width: 30px;
}
/* ========== 顶部标题栏 ========== */
#app_header {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0d1b2a, stop:1 #112240);
    border-bottom: 1px solid rgba(100, 181, 246, 0.2);
}
#brand_icon {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1565c0, stop:1 #0d47a1);
    border-radius: 8px;
    color: #e3f2fd;
    font-size: 15px;
    font-weight: 800;
    min-width: 38px;
    max-width: 38px;
    min-height: 38px;
    max-height: 38px;
    qproperty-alignment: AlignCenter;
}
#brand_title {
    color: #e3f2fd;
    font-size: 19px;
    font-weight: 700;
}
#brand_sub {
    color: #546e7a;
    font-size: 14px;
}
#process_badge {
    background: rgba(21, 101, 192, 0.2);
    border: 1px solid rgba(100, 181, 246, 0.2);
    border-radius: 20px;
    padding: 4px 16px;
    color: #42a5f5;
    font-weight: 600;
}
#icon_btn {
    background: rgba(21, 101, 192, 0.2);
    border: 1px solid rgba(100, 181, 246, 0.2);
    border-radius: 6px;
    color: #90caf9;
    padding: 5px 14px;
    font-size: 16px;
}
#icon_btn:hover {
    background: rgba(21, 101, 192, 0.4);
    border-color: #42a5f5;
    color: #e3f2fd;
}
/* ========== 卡片通用 ========== */
#card_widget {
    background: #131929;
    border: 1px solid rgba(100, 181, 246, 0.12);
    border-radius: 10px;
}
#card_title {
    color: #90caf9;
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
#step_badge {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1565c0, stop:1 #0d47a1);
    border-radius: 10px;
    color: white;
    font-size: 15px;
    font-weight: 700;
    min-width: 24px;
    max-width: 24px;
    min-height: 24px;
    max-height: 24px;
    qproperty-alignment: AlignCenter;
}
/* ========== 条码输入 ========== */
#scan_input_wrap {
    background: #0d1117;
    border: 2px solid rgba(100, 181, 246, 0.2);
    border-radius: 8px;
    padding: 4px 6px 4px 12px;
}
#scan_input {
    background: transparent;
    border: none;
    color: #e0e6ed;
    font-size: 18px;
    font-family: "Consolas", monospace;
    padding: 6px 0;
}
#scan_input::placeholder {
    color: #37474f;
}
#scan_btn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1565c0, stop:1 #0d47a1);
    border: none;
    border-radius: 6px;
    color: #e3f2fd;
    padding: 9px 18px;
    font-size: 16px;
    font-weight: 600;
}
#scan_btn:hover:!disabled {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1976d2, stop:1 #1565c0);
}
#scan_btn:disabled {
    background: #37474f;
    color: #78909c;
}
/* ========== 信息项 ========== */
#info_item {
    background: rgba(21, 101, 192, 0.06);
    border: 1px solid rgba(100, 181, 246, 0.08);
    border-radius: 6px;
    padding: 8px 12px;
}
#info_label {
    color: #546e7a;
    font-size: 15px;
}
#info_value {
    color: #cfd8dc;
    font-size: 16px;
    word-break: break-all;
}
#info_value_highlight {
    color: #42a5f5;
    font-weight: 700;
    font-size: 17px;
}
#info_value_mono {
    color: #64b5f6;
    font-family: "Consolas", monospace;
}
/* ========== 结果状态 ========== */
#result_display_idle {
    background: rgba(21, 101, 192, 0.05);
    border: 1px solid rgba(100, 181, 246, 0.1);
    border-radius: 8px;
    padding: 16px;
}
#result_display_ok {
    background: rgba(0, 230, 118, 0.08);
    border: 1px solid rgba(0, 230, 118, 0.3);
    border-radius: 8px;
    padding: 16px;
}
#result_display_ng {
    background: rgba(255, 82, 82, 0.08);
    border: 1px solid rgba(255, 82, 82, 0.3);
    border-radius: 8px;
    padding: 16px;
}
#result_text {
    font-size: 32px;
    font-weight: 800;
    letter-spacing: 1px;
    color: #e0e6ed;
}
#result_text_ok {
    color: #00e676;
    font-size: 32px;
    font-weight: 800;
}
#result_text_ng {
    color: #ff5252;
    font-size: 32px;
    font-weight: 800;
}
#result_msg {
    color: #78909c;
    font-size: 16px;
}
/* ========== 复位按钮 ========== */
#btn_reset {
    background: rgba(100, 181, 246, 0.08);
    border: 1px solid rgba(100, 181, 246, 0.2);
    border-radius: 6px;
    color: #90caf9;
    padding: 9px;
    font-size: 16px;
}
#btn_reset:hover {
    background: rgba(100, 181, 246, 0.15);
    border-color: #42a5f5;
}
/* ========== 标签栏 ========== */
#tab_btn {
    background: transparent;
    border: 1px solid transparent;
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    color: #546e7a;
    font-size: 16px;
    font-weight: 500;
    padding: 9px 18px;
}
#tab_btn:hover {
    color: #90caf9;
    background: rgba(100, 181, 246, 0.05);
}
#tab_btn_active {
    background: #131929;
    border: 1px solid rgba(100, 181, 246, 0.15);
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    color: #42a5f5;
    font-size: 16px;
    font-weight: 600;
    padding: 9px 18px;
}
#tab_count {
    background: rgba(66, 165, 245, 0.2);
    color: #42a5f5;
    font-size: 14px;
    padding: 1px 6px;
    border-radius: 10px;
    font-weight: 600;
}
/* ========== 右侧面板 ========== */
#right_panel {
    background: #131929;
    border: 1px solid rgba(100, 181, 246, 0.12);
    border-radius: 10px;
}
/* ========== 表格通用 ========== */
QTableWidget {
    background: transparent;
    border: none;
    gridline-color: rgba(100, 181, 246, 0.06);
    font-size: 16px;
}
QTableWidget::item {
    color: #cfd8dc;
    padding: 8px 12px;
    border-bottom: 1px solid rgba(100, 181, 246, 0.05);
}
QTableWidget::item:selected {
    background: rgba(66, 165, 245, 0.1);
    color: #e3f2fd;
}
QHeaderView::section {
    background: rgba(21, 101, 192, 0.2);
    color: #78909c;
    font-weight: 600;
    padding: 10px 14px;
    border: none;
    border-bottom: 1px solid rgba(100, 181, 246, 0.1);
}
QTableCornerButton::section {
    background: rgba(21, 101, 192, 0.2);
    border: none;
}
/* ========== 日志条目 ========== */
#log_entry_success {
    color: #69f0ae;
    font-size: 15px;
    padding: 8px 12px;
    background: rgba(255,255,255,0.02);
    border-radius: 4px;
}
#log_entry_error {
    color: #ff5252;
    font-size: 15px;
    padding: 8px 12px;
    background: rgba(255,255,255,0.02);
    border-radius: 4px;
}
#log_entry_warn {
    color: #ffab40;
    font-size: 15px;
    padding: 8px 12px;
    background: rgba(255,255,255,0.02);
    border-radius: 4px;
}
#log_entry_info {
    color: #78909c;
    font-size: 15px;
    padding: 8px 12px;
    background: rgba(255,255,255,0.02);
    border-radius: 4px;
}
#log_time {
    color: #455a64;
    font-size: 15px;
    min-width: 70px;
}
/* ========== 状态横幅 ========== */
#status_banner_success {
    background: rgba(0, 230, 118, 0.1);
    border: 1px solid rgba(0, 230, 118, 0.2);
    border-radius: 8px;
    padding: 12px 16px;
    color: #00e676;
    font-weight: 600;
    font-size: 17px;
}
#status_banner_fail {
    background: rgba(244, 67, 54, 0.1);
    border: 1px solid rgba(244, 67, 54, 0.2);
    border-radius: 8px;
    padding: 12px 16px;
    color: #f44336;
    font-weight: 600;
    font-size: 17px;
}
#status_banner_loading {
    background: rgba(255, 152, 0, 0.1);
    border: 1px solid rgba(255, 152, 0, 0.2);
    border-radius: 8px;
    padding: 12px 16px;
    color: #ff9800;
    font-weight: 600;
    font-size: 17px;
}
/* ========== 标签 ========== */
#badge_pass {
    background: rgba(0, 230, 118, 0.15);
    color: #00e676;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
}
#badge_fail {
    background: rgba(244, 67, 54, 0.15);
    color: #f44336;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
}
#badge_pending {
    background: rgba(255, 171, 64, 0.15);
    color: #ffab40;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
}
/* ========== 错误框 ========== */
#error_box {
    background: rgba(244, 67, 54, 0.08);
    border: 1px solid rgba(244, 67, 54, 0.25);
    border-radius: 6px;
    padding: 10px 14px;
    color: #ef9a9a;
    font-size: 16px;
}
/* ========== 输入框通用 ========== */
QLineEdit {
    background: #0d1117;
    border: 1px solid rgba(100, 181, 246, 0.2);
    border-radius: 6px;
    color: #e0e6ed;
    padding: 10px 14px;
    font-size: 17px;
    font-family: "Consolas", monospace;
}
QLineEdit:focus {
    border-color: #42a5f5;
}
QLineEdit::placeholder {
    color: #37474f;
}
QLineEdit:disabled {
    opacity: 0.5;
}
/* ========== 代码块 ========== */
#code_block {
    background: #060a10;
    border: 1px solid rgba(100, 181, 246, 0.1);
    border-radius: 6px;
    padding: 12px;
    font-family: "Consolas", monospace;
    font-size: 16px;
    color: #eceff1;
}
#code_block_req {
    background: #060a10;
    border: 1px solid rgba(100, 181, 246, 0.1);
    border-radius: 6px;
    padding: 12px;
    font-family: "Consolas", monospace;
    font-size: 16px;
    color: #80cbc4;
}
#code_block_res {
    background: #060a10;
    border: 1px solid rgba(100, 181, 246, 0.1);
    border-radius: 6px;
    padding: 12px;
    font-family: "Consolas", monospace;
    font-size: 16px;
    color: #a5d6a7;
}
#code_block_err {
    background: #060a10;
    border: 1px solid rgba(244, 67, 54, 0.15);
    border-radius: 6px;
    padding: 12px;
    font-family: "Consolas", monospace;
    font-size: 16px;
    color: #ef9a9a;
}
/* ========== 空状态 ========== */
#empty_hint {
    color: #37474f;
    font-size: 17px;
    padding: 16px;
}
\"\"\"

DIALOG_STYLE = \"\"\"
QDialog {
    background: #0a0e1a;
}
#modal_overlay {
    background: rgba(0, 0, 0, 0.65);
}
#modal_panel {
    background: #1a1f2e;
    border: 1px solid rgba(100, 181, 246, 0.25);
    border-radius: 12px;
}
#modal_header {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0d47a1, stop:1 #1565c0);
    border-bottom: 1px solid rgba(100, 181, 246, 0.2);
    padding: 18px 24px;
}
#modal_header_red {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #b71c1c, stop:1 #d32f2f);
    border-bottom: 1px solid rgba(244, 67, 54, 0.2);
    padding: 18px 24px;
}
#modal_title {
    color: #e3f2fd;
    font-size: 20px;
    font-weight: 600;
}
#modal_body {
    background: transparent;
    padding: 20px;
}
#config_section {
    background: rgba(13, 17, 23, 0.35);
    border: 1px solid rgba(100, 181, 246, 0.14);
    border-radius: 10px;
    padding: 14px;
}
#section_title {
    color: #42a5f5;
    font-size: 19px;
    font-weight: 700;
    border-left: 3px solid #42a5f5;
    padding-left: 8px;
    margin-bottom: 10px;
}
#field_label {
    color: #90caf9;
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 4px;
}
#field_hint {
    color: #546e7a;
    font-size: 15px;
    margin-top: 2px;
}
#modal_footer {
    background: transparent;
    border-top: 1px solid rgba(100, 181, 246, 0.1);
    padding: 16px 24px;
}
#btn_cancel {
    background: transparent;
    border: 1px solid rgba(100, 181, 246, 0.25);
    border-radius: 6px;
    color: #78909c;
    padding: 8px 20px;
    font-size: 17px;
}
#btn_cancel:hover {
    border-color: #42a5f5;
    color: #42a5f5;
}
#btn_save {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1565c0, stop:1 #0d47a1);
    border: 1px solid rgba(100, 181, 246, 0.3);
    border-radius: 6px;
    color: #e3f2fd;
    padding: 8px 24px;
    font-size: 17px;
    font-weight: 600;
}
#btn_save:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1976d2, stop:1 #1565c0);
}
#btn_confirm_red {
    background: #d32f2f;
    border: none;
    border-radius: 4px;
    color: white;
    padding: 8px 20px;
    font-size: 17px;
    font-weight: 600;
}
#btn_confirm_red:hover {
    background: #f44336;
}
#login_hint {
    color: #90caf9;
    font-size: 17px;
}
#login_field_label {
    color: #546e7a;
    font-size: 16px;
    font-weight: 600;
}
#error_text {
    color: #ef5350;
    background: rgba(244, 67, 54, 0.1);
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 16px;
}
"""

