import sys

try:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
    QT_VERSION = 5
except ImportError:
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *
    from PyQt6.QtWidgets import *
    
    # PyQt6 兼容补丁：将 Qt.ItemDataRole / Qt.Orientation 等属性代理
    # 为双向兼容模式，避免 Qt5/Qt6 转换问题
    QT_VERSION = 6
