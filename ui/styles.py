# -*- coding: utf-8 -*-
"""
LabelImg2 - Unified Desktop Workstation Style (Light Workstation QSS)
全工作台统一现代工业级视觉规范，服务于：
- Manage Labels (标签与类别管理)
- YOLO 模型中心 (Model Center)
- YOLO 模型训练 (Model Training)
"""

LIGHT_WORKSTATION_STYLE = """
/* ==================== 1. 全局基础排版与字体系统 ==================== */
QDialog, QMainWindow {
    background-color: #FFFFFF;
    color: #0F172A;
    font-family: 'Segoe UI', -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
    font-size: 14px;
}

QWidget {
    color: #0F172A;
    font-family: 'Segoe UI', -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
    font-size: 14px;
}

QToolTip {
    background-color: #0F172A;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 13px;
}

/* ==================== 2. 滚动区与细致滚动条 ==================== */
QScrollArea {
    background-color: #FFFFFF;
    border: none;
}

QScrollBar:vertical {
    border: none;
    background: #F8FAFC;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    min-height: 28px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
}

QScrollBar:horizontal {
    border: none;
    background: #F8FAFC;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background: #CBD5E1;
    min-width: 28px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: #94A3B8;
}

/* ==================== 3. 分段标题与分组卡片 ==================== */
QLabel#section_header {
    font-size: 16px;
    font-weight: 700;
    color: #0F172A;
    padding-bottom: 6px;
    border-bottom: 2px solid #0F172A;
    margin-top: 8px;
    margin-bottom: 8px;
}

QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    margin-top: 16px;
    padding: 16px 14px 14px 14px;
    font-size: 14px;
    font-weight: 700;
    color: #0F172A;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0px 8px;
    background-color: #FFFFFF;
    color: #0F172A;
    font-weight: 700;
}

/* ==================== 4. 按钮系统 (层次清晰的主次交互) ==================== */
QPushButton {
    background-color: #0F172A;
    color: #FFFFFF;
    border: 1px solid #0F172A;
    border-radius: 6px;
    padding: 6px 16px;
    min-height: 32px;
    font-weight: 600;
    font-size: 14px;
    text-align: center;
}

QPushButton:hover {
    background-color: #1E293B;
    border-color: #1E293B;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #020617;
    border-color: #020617;
}

QPushButton:disabled {
    background-color: #F1F5F9;
    border-color: #E2E8F0;
    color: #94A3B8;
}

/* 次级按钮 (白底微灰边框) */
QPushButton#btn_secondary {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    color: #1E293B;
    font-weight: 500;
}

QPushButton#btn_secondary:hover {
    background-color: #F8FAFC;
    border-color: #94A3B8;
    color: #0F172A;
}

QPushButton#btn_secondary:pressed {
    background-color: #F1F5F9;
    border-color: #64748B;
}

/* 警示与删除按钮 */
QPushButton#btn_danger {
    background-color: #FEF2F2;
    border: 1px solid #FECACA;
    color: #DC2626;
    font-weight: 600;
}

QPushButton#btn_danger:hover {
    background-color: #FEE2E2;
    border-color: #FCA5A5;
    color: #B91C1C;
}

QPushButton#btn_danger:pressed {
    background-color: #FCA5A5;
    color: #991B1B;
}

/* 成功状态按钮 */
QPushButton#btn_success {
    background-color: #ECFDF5;
    border: 1px solid #A7F3D0;
    color: #059669;
    font-weight: 600;
}

QPushButton#btn_success:hover {
    background-color: #D1FAE5;
    border-color: #6EE7B7;
    color: #047857;
}

/* 主行动按钮显式标注 */
QPushButton#btn_primary {
    background-color: #0F172A;
    color: #FFFFFF;
    border: 1px solid #0F172A;
    font-weight: 600;
    text-align: center;
}

QPushButton#btn_primary:hover {
    background-color: #1E293B;
    border-color: #1E293B;
}

/* ==================== 5. 表单控件 (Inputs / Combos / SpinBoxes) ==================== */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 5px 10px;
    min-height: 32px;
    color: #0F172A;
    font-size: 14px;
    selection-background-color: #0F172A;
    selection-color: #FFFFFF;
}

QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {
    border-color: #94A3B8;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 2px solid #0F172A;
    padding: 4px 9px;
}

QComboBox::drop-down {
    border: none;
    width: 26px;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    selection-background-color: #F1F5F9;
    selection-color: #0F172A;
    color: #0F172A;
    padding: 6px;
    outline: none;
    font-size: 14px;
}

/* ==================== 6. 单选框与复选框 (Radio & Checkbox) ==================== */
QRadioButton, QCheckBox {
    font-size: 14px;
    color: #0F172A;
    spacing: 8px;
}

/* ==================== 7. 滑块微调控件 (Sliders) ==================== */
QSlider::groove:horizontal {
    height: 6px;
    background: #E2E8F0;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #0F172A;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 2px solid #0F172A;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #F8FAFC;
    border-color: #1E293B;
}

/* ==================== 8. 表格与列表控件 (Tables & Lists) ==================== */
QTableWidget, QListWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    color: #0F172A;
    gridline-color: #F1F5F9;
    font-size: 14px;
    outline: none;
}

QHeaderView::section {
    background-color: #F8FAFC;
    color: #475569;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #E2E8F0;
    font-weight: 600;
    font-size: 13px;
}

QTableWidget::item, QListWidget::item {
    padding: 8px 12px;
    border-bottom: 1px solid #F8FAFC;
    color: #0F172A;
    font-size: 14px;
}

QTableWidget::item:hover, QListWidget::item:hover {
    background-color: #F8FAFC;
}

QTableWidget::item:selected, QListWidget::item:selected {
    background-color: #F1F5F9;
    color: #0F172A;
    font-weight: 600;
}

/* ==================== 9. 进度条 (Progress Bar) ==================== */
QProgressBar {
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    text-align: center;
    background-color: #F8FAFC;
    color: #0F172A;
    font-weight: 600;
    font-size: 13px;
    min-height: 24px;
}

QProgressBar::chunk {
    background-color: #0F172A;
    border-radius: 5px;
}

/* ==================== 10. 控制台日志文本域 (Text Terminal) ==================== */
QTextEdit {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    color: #0F172A;
    font-family: 'Consolas', 'Cascadia Code', 'Courier New', monospace;
    font-size: 13px;
    padding: 8px 10px;
    line-height: 1.4;
}

/* ==================== 11. 专属指标卡片与状态指示器 ==================== */
QLabel#metric_card {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 700;
    color: #0F172A;
    font-size: 14px;
    min-height: 26px;
}

QLabel#status_indicator {
    color: #475569;
    font-size: 13px;
    font-weight: 500;
}
"""
