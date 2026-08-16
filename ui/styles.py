LIGHT_WORKSTATION_STYLE = """
/* 极简无框黑字白纸 (Borderless Monochrome Paper) QSS Style for LabelImg2 Integrations */
QDialog, QMainWindow {
    background-color: #FFFFFF;
    color: #000000;
    font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    font-size: 13px;
}

QWidget {
    color: #000000;
    font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ScrollArea Styling */
QScrollArea {
    background-color: #FFFFFF;
    border: none;
}

QScrollBar:vertical {
    border: none;
    background: #F5F5F5;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #888888;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #000000;
}

/* GroupBox & Section Header Styling (No Boxed Outer Border) */
QGroupBox {
    background-color: #FFFFFF;
    border: none;
    margin-top: 14px;
    font-weight: 700;
    font-size: 14px;
    color: #000000;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 0px;
    padding: 0px 0px 4px 0px;
    background-color: transparent;
    border: none;
    border-bottom: 2px solid #000000;
    color: #000000;
    font-weight: bold;
}

/* Section Header Label */
QLabel#section_header {
    font-size: 14px;
    font-weight: bold;
    color: #000000;
    padding-bottom: 4px;
    border-bottom: 2px solid #000000;
    margin-bottom: 8px;
}

/* Buttons (Stark Black & White) */
QPushButton {
    background-color: #000000;
    color: #FFFFFF;
    border: 1px solid #000000;
    border-radius: 6px;
    padding: 6px 16px;
    min-height: 28px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #333333;
    border-color: #333333;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #555555;
}

QPushButton:disabled {
    background-color: #F5F5F5;
    border-color: #CCCCCC;
    color: #888888;
}

QPushButton#btn_secondary {
    background-color: #FFFFFF;
    border: 1px solid #000000;
    color: #000000;
}

QPushButton#btn_secondary:hover {
    background-color: #F0F0F0;
    border-color: #000000;
    color: #000000;
}

QPushButton#btn_danger {
    background-color: #000000;
    border-color: #000000;
    color: #FFFFFF;
}

/* Inputs, SpinBoxes & ComboBoxes */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #000000;
    border-radius: 4px;
    padding: 5px 10px;
    min-height: 26px;
    color: #000000;
    font-size: 13px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 2px solid #000000;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #000000;
    selection-background-color: #000000;
    selection-color: #FFFFFF;
    color: #000000;
    padding: 4px;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background: #E5E5E5;
    border: 1px solid #000000;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #000000;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 2px solid #000000;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #E5E5E5;
}

/* Table Widget */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #000000;
    border-radius: 4px;
    color: #000000;
    gridline-color: #E5E5E5;
}

QHeaderView::section {
    background-color: #F5F5F5;
    color: #000000;
    padding: 6px;
    border: 1px solid #000000;
    font-weight: 600;
    font-size: 12px;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #000000;
    border-radius: 4px;
    text-align: center;
    background-color: #FFFFFF;
    color: #000000;
    font-weight: 600;
    min-height: 22px;
}

QProgressBar::chunk {
    background-color: #000000;
    border-radius: 3px;
}

/* Text Edit Log Terminal */
QTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #000000;
    border-radius: 4px;
    color: #000000;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 8px;
}
"""
