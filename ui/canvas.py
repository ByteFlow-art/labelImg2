import math
from typing import List, Dict, Any, Optional
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt5.QtGui import (
    QPixmap, QPen, QColor, QBrush, QFont, QPainter, 
    QWheelEvent, QMouseEvent, QKeyEvent, QCursor
)
from PyQt5.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, 
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsItem
)

# 默认类别颜色画刷库
CLASS_COLORS = [
    QColor(239, 68, 68),    # Red
    QColor(59, 130, 246),   # Blue
    QColor(16, 185, 129),   # Green
    QColor(245, 158, 11),   # Amber
    QColor(168, 85, 247),   # Purple
    QColor(236, 72, 153),   # Pink
    QColor(14, 165, 233),   # Sky
    QColor(234, 179, 8),    # Yellow
    QColor(20, 184, 166),   # Teal
    QColor(99, 102, 241),   # Indigo
]

class BoundingBoxItem(QGraphicsRectItem):
    """
    可交互控制的 2D 矩形目标标注框
    支持拖拽移动、角落拉伸缩放、类别颜色渲染与标签显示
    """
    HANDLE_SIZE = 8.0

    def __init__(self, xmin: float, ymin: float, xmax: float, ymax: float, class_name: str, color: QColor, parent_canvas=None):
        rect = QRectF(xmin, ymin, max(1.0, xmax - xmin), max(1.0, ymax - ymin))
        super().__init__(rect)
        self.class_name = class_name
        self.color = color
        self.parent_canvas = parent_canvas
        self.selected_handle = None
        self.drag_start_pos = None
        self.drag_start_rect = None

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.update_style()

    def update_style(self):
        pen_color = self.color
        pen_width = 3 if self.isSelected() else 2
        pen = QPen(pen_color, pen_width, Qt.PenStyle.SolidLine)
        self.setPen(pen)

        fill_color = QColor(pen_color.red(), pen_color.green(), pen_color.blue(), 40 if self.isSelected() else 20)
        self.setBrush(QBrush(fill_color))

    def get_bbox_coords(self) -> List[float]:
        rect = self.rect()
        scene_pos = self.pos()
        xmin = rect.left() + scene_pos.x()
        ymin = rect.top() + scene_pos.y()
        xmax = rect.right() + scene_pos.x()
        ymax = rect.bottom() + scene_pos.y()
        return [round(xmin, 2), round(ymin, 2), round(xmax, 2), round(ymax, 2)]

    def get_handle_rects(self) -> Dict[str, QRectF]:
        r = self.rect()
        s = self.HANDLE_SIZE
        return {
            "top_left": QRectF(r.left() - s/2, r.top() - s/2, s, s),
            "top_right": QRectF(r.right() - s/2, r.top() - s/2, s, s),
            "bottom_left": QRectF(r.left() - s/2, r.bottom() - s/2, s, s),
            "bottom_right": QRectF(r.right() - s/2, r.bottom() - s/2, s, s),
        }

    def hoverMoveEvent(self, event):
        pos = event.pos()
        handles = self.get_handle_rects()

        if handles["top_left"].contains(pos) or handles["bottom_right"].contains(pos):
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        elif handles["top_right"].contains(pos) or handles["bottom_left"].contains(pos):
            self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            handles = self.get_handle_rects()
            self.selected_handle = None

            for handle_name, handle_rect in handles.items():
                if handle_rect.contains(pos):
                    self.selected_handle = handle_name
                    self.drag_start_pos = event.scenePos()
                    self.drag_start_rect = QRectF(self.rect())
                    break

            if not self.selected_handle:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.selected_handle and self.drag_start_pos and self.drag_start_rect:
            diff = event.scenePos() - self.drag_start_pos
            r = QRectF(self.drag_start_rect)

            if self.selected_handle == "top_left":
                r.setTopLeft(r.topLeft() + diff)
            elif self.selected_handle == "top_right":
                r.setTopRight(r.topRight() + diff)
            elif self.selected_handle == "bottom_left":
                r.setBottomLeft(r.bottomLeft() + diff)
            elif self.selected_handle == "bottom_right":
                r.setBottomRight(r.bottomRight() + diff)

            # 确保长宽有效
            if r.width() > 5 and r.height() > 5:
                self.setRect(r.normalized())
                if self.parent_canvas:
                    self.parent_canvas.box_changed.emit()
        else:
            super().mouseMoveEvent(event)
            if self.parent_canvas:
                self.parent_canvas.box_changed.emit()

    def mouseReleaseEvent(self, event):
        self.selected_handle = None
        self.drag_start_pos = None
        self.drag_start_rect = None
        super().mouseReleaseEvent(event)
        if self.parent_canvas:
            self.parent_canvas.box_changed.emit()

    def paint(self, painter: QPainter, option, widget=None):
        self.update_style()
        super().paint(painter, option, widget)

        # 绘制四角控制手柄
        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.white, 1))
            painter.setBrush(QBrush(self.color))
            for h_rect in self.get_handle_rects().values():
                painter.drawRect(h_rect)

        # 绘制顶部类别标签条
        rect = self.rect()
        painter.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
        text = f" {self.class_name} "
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(text) + 8
        text_height = fm.height() + 4

        label_bg = QRectF(rect.left(), rect.top() - text_height, text_width, text_height)
        painter.fillRect(label_bg, QBrush(self.color))
        painter.setPen(QPen(Qt.GlobalColor.white))
        painter.drawText(label_bg, Qt.AlignmentFlag.AlignCenter, text)


class ImageAnnotationCanvas(QGraphicsView):
    """
    交互式图形图像标注画布组件
    """
    box_changed = pyqtSignal()
    cursor_position_changed = pyqtSignal(int, int)
    zoom_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.pixmap_item: Optional[QGraphicsPixmapItem] = None
        self.box_items: List[BoundingBoxItem] = []
        
        self.image_width = 0
        self.image_height = 0
        self.zoom_factor = 1.0

        # 画框创建模式标志
        self.is_draw_mode = False
        self.drawing_start_pos: Optional[QPointF] = None
        self.temp_draw_item: Optional[QGraphicsRectItem] = None
        self.current_drawing_class = "object"

        # 平移模式标志
        self.is_panning = False
        self.pan_start_pos = None

        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setStyleSheet("background-color: #0F111A; border: none;")

    def load_image(self, image_path: str):
        """加载新图片并置于画布中央"""
        self.scene.clear()
        self.box_items.clear()
        self.pixmap_item = None

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            return

        self.image_width = pixmap.width()
        self.image_height = pixmap.height()

        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(0, 0, self.image_width, self.image_height)

        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.zoom_factor = self.transform().m11()
        self.zoom_changed.emit(self.zoom_factor)

    def clear_boxes(self):
        """清空当前画布上的所有标注框"""
        for item in self.box_items:
            self.scene.removeItem(item)
        self.box_items.clear()
        self.box_changed.emit()

    def add_box(self, xmin: float, ymin: float, xmax: float, ymax: float, class_name: str, color: Optional[QColor] = None) -> BoundingBoxItem:
        """在画布上新增一个标注框"""
        if not color:
            color_idx = abs(hash(class_name)) % len(CLASS_COLORS)
            color = CLASS_COLORS[color_idx]

        # 边界防越界处理
        xmin = max(0.0, min(xmin, float(self.image_width)))
        ymin = max(0.0, min(ymin, float(self.image_height)))
        xmax = max(0.0, min(xmax, float(self.image_width)))
        ymax = max(0.0, min(ymax, float(self.image_height)))

        box_item = BoundingBoxItem(xmin, ymin, xmax, ymax, class_name, color, parent_canvas=self)
        self.scene.addItem(box_item)
        self.box_items.append(box_item)
        self.box_changed.emit()
        return box_item

    def get_all_boxes(self) -> List[Dict[str, Any]]:
        """提取画布上当前所有标注框的数据"""
        boxes_data = []
        for item in self.box_items:
            coords = item.get_bbox_coords()
            boxes_data.append({
                "class_name": item.class_name,
                "confidence": 1.0,
                "bbox": coords
            })
        return boxes_data

    def set_draw_mode(self, enabled: bool, class_name: str = "object"):
        """开启或关闭手动划框模式"""
        self.is_draw_mode = enabled
        self.current_drawing_class = class_name
        if enabled:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def remove_selected_box(self):
        """删除当前选中的标注框"""
        selected_items = self.scene.selectedItems()
        count = 0
        for item in selected_items:
            if isinstance(item, BoundingBoxItem) and item in self.box_items:
                self.scene.removeItem(item)
                self.box_items.remove(item)
                count += 1
        self.box_changed.emit()
        if count > 0:
            print(f"[Shortcut Q/Del Terminal] 成功删除当前选中标注框 ({count} 个)", flush=True)
        else:
            print("[Shortcut Q/Del Terminal] 提示: 当前未选中任何标注框 (请先在画布中点击选中要删除的框)", flush=True)

    def wheelEvent(self, event: QWheelEvent):
        """滚轮缩放画布"""
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)
        self.zoom_factor = self.transform().m11()
        self.zoom_changed.emit(self.zoom_factor)

    def mousePressEvent(self, event: QMouseEvent):
        scene_pos = self.mapToScene(event.pos())
        
        # 中键或 Alt 拖拽平移
        if event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.AltModifier):
            self.is_panning = True
            self.pan_start_pos = event.pos()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
            return

        # 划框新建模式
        if self.is_draw_mode and event.button() == Qt.MouseButton.LeftButton:
            self.drawing_start_pos = scene_pos
            rect = QRectF(scene_pos, scene_pos)
            self.temp_draw_item = QGraphicsRectItem(rect)
            pen = QPen(QColor(59, 130, 246), 2, Qt.PenStyle.DashLine)
            self.temp_draw_item.setPen(pen)
            self.scene.addItem(self.temp_draw_item)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        scene_pos = self.mapToScene(event.pos())
        self.cursor_position_changed.emit(int(scene_pos.x()), int(scene_pos.y()))

        if self.is_panning and self.pan_start_pos:
            delta = event.pos() - self.pan_start_pos
            self.pan_start_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        if self.is_draw_mode and self.drawing_start_pos and self.temp_draw_item:
            rect = QRectF(self.drawing_start_pos, scene_pos).normalized()
            self.temp_draw_item.setRect(rect)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.is_panning:
            self.is_panning = False
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor if self.is_draw_mode else Qt.CursorShape.ArrowCursor))
            event.accept()
            return

        if self.is_draw_mode and self.drawing_start_pos and self.temp_draw_item:
            scene_pos = self.mapToScene(event.pos())
            rect = QRectF(self.drawing_start_pos, scene_pos).normalized()
            
            self.scene.removeItem(self.temp_draw_item)
            self.temp_draw_item = None
            self.drawing_start_pos = None

            # 若框的大小足够，则真实创建
            if rect.width() > 5 and rect.height() > 5:
                self.add_box(rect.left(), rect.top(), rect.right(), rect.bottom(), self.current_drawing_class)
            
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace, Qt.Key.Key_Q):
            self.remove_selected_box()
            event.accept()
        else:
            super().keyPressEvent(event)
