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
    禁用滚轮切换，通过键盘点击输入及末尾微调按钮调节。
    """
    def wheelEvent(self, event):
        event.ignore()


class SafeDoubleSpinBox(QDoubleSpinBox):
    """
    浮点数值调节型参数控件：
    禁用滚轮切换，通过键盘点击输入及末尾微调按钮调节。
    """
    def wheelEvent(self, event):
        event.ignore()


class SafeSlider(QSlider):
    """
    滑块调节控件：
    禁用滚轮切换，通过鼠标直接点击或拖动滑块调节。
    """
    def wheelEvent(self, event):
        event.ignore()
