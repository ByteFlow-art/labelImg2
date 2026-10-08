# -*- coding: utf-8 -*-
"""
LabelImg2 - 安全交互控件库 (Safe Interactive Widgets)
防止在滚动查看面板时因鼠标滚轮误触而篡改参数：
1. SafeComboBox: 未点击展开下拉菜单时忽略滚轮事件；仅在展开下拉列表后响应滚轮。
2. SafeSpinBox / SafeDoubleSpinBox: 忽略滚轮滚动，仅支持点击输入和右侧微调加减按钮。
3. SafeSlider: 忽略滚轮滚动，支持鼠标点击与拖动调节。
"""

from core.qt_compat import QComboBox, QSpinBox, QDoubleSpinBox, QSlider, Qt

class SafeComboBox(QComboBox):
    """
    选择型参数控件：
    点击展开后才可通过滚轮查看并选择切换；未展开情况下忽略滚轮，防止滑动浏览时错把参数改乱。
    """
    def wheelEvent(self, event):
        # 仅在下拉列表视图弹出且可见时，才允许滚轮选择
        if self.view() and self.view().isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()


class SafeSpinBox(QSpinBox):
    """
    数值调节型参数控件：
    防误调机制：未聚焦时忽略滚轮（防止滚动浏览面板时误篡改参数）；鼠标点击获得焦点后才响应滚轮调节。
    """
    def __init__(self, *args, **kwargs):
        super(SafeSpinBox, self).__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            super(SafeSpinBox, self).wheelEvent(event)
        else:
            event.ignore()


class SafeDoubleSpinBox(QDoubleSpinBox):
    """
    浮点数值调节型参数控件：
    防误调机制：未聚焦时忽略滚轮；鼠标点击获得焦点后才响应滚轮调节。
    """
    def __init__(self, *args, **kwargs):
        super(SafeDoubleSpinBox, self).__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            super(SafeDoubleSpinBox, self).wheelEvent(event)
        else:
            event.ignore()


class SafeSlider(QSlider):
    """
    滑块调节控件：
    防误调机制：未聚焦时忽略滚轮；鼠标点击获得焦点后才响应滚轮调节。
    """
    def __init__(self, *args, **kwargs):
        super(SafeSlider, self).__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            super(SafeSlider, self).wheelEvent(event)
        else:
            event.ignore()
