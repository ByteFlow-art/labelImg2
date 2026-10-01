# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QAbstractButton, QSizePolicy
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt5.QtCore import Qt, QRectF, QSize, pyqtProperty, QPropertyAnimation, pyqtSlot

class SwitchButton(QAbstractButton):
    """
    自适应精致开关按钮 (Adaptive Toggle Switch Button)
    
    特性：
    1. 自包含现代交互设计，无需外部文字标签 ("外面不写那四个字")
    2. 水平工具栏 (顶部/底部): 呈现经典药丸型胶囊开关 (58x26)，内嵌清晰的 "AUTO" / "OFF" 状态与圆润滑块
    3. 垂直工具栏 (左侧/右侧): 自动自适应切换为紧凑工具按键形态 (宽度自适应贴合列宽，高度 42px)，
       内部图标与滑块严格在工具栏中心轴上水平居中绘制，
       彻底消除停靠在左侧时出现的“偏左错位”问题，完全对齐 Save 与其他原生工具按钮。
    4. 带有平滑动画、悬浮微动效、状态颜色插值与动态提示词 (Tooltip)。
    """
    def __init__(self, parent=None, checked=True, orientation=Qt.Horizontal):
        super(SwitchButton, self).__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self._orientation = orientation
        self._hover = False

        # 滑块动画插值位置 (0.0 ~ 1.0)
        self._thumb_position = 1.0 if checked else 0.0
        self._animation = QPropertyAnimation(self, b"thumb_position", self)
        self._animation.setDuration(120)

        self.toggled.connect(self._on_toggled)
        self.setOrientation(orientation)
        self.updateToolTip()

    def get_thumb_position(self):
        return self._thumb_position

    def set_thumb_position(self, pos):
        self._thumb_position = pos
        self.update()

    thumb_position = pyqtProperty(float, get_thumb_position, set_thumb_position)

    def sizeHint(self):
        if self._orientation == Qt.Horizontal:
            return QSize(58, 26)
        return QSize(43, 42)

    def setOrientation(self, orientation):
        """响应工具栏停靠区域或方向变化 (Qt.Horizontal <-> Qt.Vertical)"""
        self._orientation = orientation
        if orientation == Qt.Horizontal:
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.setFixedSize(58, 26)
        else:
            # 垂直工具栏 (左侧/右侧):
            # 采用 Expanding 策略自动适配当前垂直工具栏列宽，
            # 内部绘制时以 self.width() / 2.0 精准水平居中，彻底消除偏左错位
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.setFixedHeight(42)
        self.updateGeometry()
        self.update()

    def updateToolTip(self):
        if self.isChecked():
            self.setToolTip("自动保存 (Auto Save): 开启\n切换图片时自动保存标注与负样本空标签\n点击可关闭")
        else:
            self.setToolTip("自动保存 (Auto Save): 关闭\n切换图片时不自动保存\n点击可开启")

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super(SwitchButton, self).enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super(SwitchButton, self).leaveEvent(event)

    @pyqtSlot(bool)
    def _on_toggled(self, is_checked):
        self.updateToolTip()
        self._animation.stop()
        self._animation.setStartValue(self._thumb_position)
        self._animation.setEndValue(1.0 if is_checked else 0.0)
        self._animation.start()

    def setChecked(self, checked):
        super(SwitchButton, self).setChecked(checked)
        self._thumb_position = 1.0 if checked else 0.0
        self.updateToolTip()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0

        pos = self._thumb_position
        is_on = self.isChecked()

        # 计算轨道背景颜色插值 (开: #10B981 翡翠绿, 关: #94A3B8 中灰)
        r = int(148 + (16 - 148) * pos)
        g = int(163 + (185 - 163) * pos)
        b = int(184 + (129 - 184) * pos)
        bg = QColor(r, g, b)
        if self._hover:
            bg = bg.lighter(108)

        if self._orientation == Qt.Horizontal:
            # 1. 水平药丸胶囊开关 (58 x 26，内部精准居中)
            track_w = 56.0
            track_h = 24.0
            track_rect = QRectF(cx - track_w / 2.0, cy - track_h / 2.0, track_w, track_h)

            p.setPen(Qt.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(track_rect, 12, 12)

            # 微妙外边框质感
            p.setPen(QColor(0, 0, 0, 25))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(track_rect, 12, 12)

            # 内嵌文字: 开为 AUTO, 关为 OFF
            font = QFont("Segoe UI", 8, QFont.Bold)
            font.setPixelSize(11)
            p.setFont(font)
            p.setPen(QColor("#FFFFFF"))
            if pos > 0.5:
                # 状态开启: 文字在左侧，滑块在右侧
                p.drawText(QRectF(track_rect.left() + 4, track_rect.top(), 28, track_h), Qt.AlignCenter, "AUTO")
            else:
                # 状态关闭: 滑块在左侧，文字在右侧
                p.drawText(QRectF(track_rect.left() + 24, track_rect.top(), 28, track_h), Qt.AlignCenter, "OFF")

            # 圆形滑块 (直径 18px)
            thumb_radius = 9.0
            min_x = track_rect.left() + 12.0
            max_x = track_rect.right() - 12.0
            thumb_cx = min_x + (max_x - min_x) * pos
            thumb_cy = cy

            # 滑块柔和微阴影
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 30))
            p.drawEllipse(QRectF(thumb_cx - thumb_radius + 0.5, thumb_cy - thumb_radius + 1.0, thumb_radius * 2, thumb_radius * 2))

            # 滑块本体
            p.setBrush(QColor("#FFFFFF"))
            p.drawEllipse(QRectF(thumb_cx - thumb_radius, thumb_cy - thumb_radius, thumb_radius * 2, thumb_radius * 2))

        else:
            # 2. 垂直工具栏标准工具按键形态 (按列宽自适应居中，高度 42px)
            # 悬浮微底色 (模拟原生 QToolButton hover 效果，按 cx 居中)
            if self._hover:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(0, 0, 0, 18))
                p.drawRoundedRect(QRectF(cx - 21.0, 0, 42.0, 42.0), 4, 4)

            # 顶部 AUTO 标识文字 (在中心轴 cx 上严格水平居中)
            font = QFont("Segoe UI", 8, QFont.Bold)
            font.setPixelSize(10)
            p.setFont(font)
            text_color = QColor("#059669") if is_on else QColor("#64748B")
            p.setPen(text_color)
            p.drawText(QRectF(cx - 21.0, 3, 42.0, 13), Qt.AlignCenter, "AUTO")

            # 底部微型横向滑块轨道 (32 x 16，在中心轴 cx 上严格水平居中)
            track_w = 32.0
            track_h = 16.0
            track_rect = QRectF(cx - track_w / 2.0, 19, track_w, track_h)

            p.setPen(Qt.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(track_rect, 8, 8)

            p.setPen(QColor(0, 0, 0, 20))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(track_rect, 8, 8)

            # 微型圆形滑块 (直径 12px)
            thumb_radius = 6.0
            min_x = track_rect.left() + 8.0
            max_x = track_rect.right() - 8.0
            thumb_cx = min_x + (max_x - min_x) * pos
            thumb_cy = 27.0

            # 滑块阴影与本体
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 25))
            p.drawEllipse(QRectF(thumb_cx - thumb_radius + 0.3, thumb_cy - thumb_radius + 0.8, thumb_radius * 2, thumb_radius * 2))

            p.setBrush(QColor("#FFFFFF"))
            p.drawEllipse(QRectF(thumb_cx - thumb_radius, thumb_cy - thumb_radius, thumb_radius * 2, thumb_radius * 2))
