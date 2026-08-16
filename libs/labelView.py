import sys
import re
import weakref
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

class HashableQStandardItem(QStandardItem):
    def __init__(self, text):
        super(HashableQStandardItem, self).__init__(text)

    def __hash__(self):
        return hash(id(self))


class PopupKeyFilter(QObject):
    def __init__(self, combo, parent=None):
        super(PopupKeyFilter, self).__init__(parent)
        self.combo = combo

    def eventFilter(self, obj, e):
        if e.type() == QEvent.KeyPress:
            key = e.key()
            txt = e.text().lower() if e.text() else ""
            if key in (Qt.Key_Q, Qt.Key_Delete, Qt.Key_Backspace) or txt == 'q':
                if self.combo:
                    try:
                        self.combo.hidePopup()
                    except Exception:
                        pass
                win = self.combo.window() if self.combo else None
                if win and hasattr(win, 'deleteSelectedShape'):
                    win.deleteSelectedShape()
                return True
        return super(PopupKeyFilter, self).eventFilter(obj, e)


class CLabelComboBox(QComboBox):
    def event(self, e):
        if e.type() == QEvent.KeyPress:
            key = e.key()
            txt = e.text().lower() if e.text() else ""
            if key in (Qt.Key_Q, Qt.Key_Delete, Qt.Key_Backspace) or txt == 'q':
                try:
                    self.hidePopup()
                except Exception:
                    pass
                win = self.window()
                if hasattr(win, 'deleteSelectedShape'):
                    win.deleteSelectedShape()
                return True
        return super(CLabelComboBox, self).event(e)


class CComboBoxDelegate(QStyledItemDelegate):
    def __init__(self, parent, listItem):
        super(CComboBoxDelegate, self).__init__(parent)
        self.listItem = listItem

    def updateListItem(self, listItem):
        self.listItem = listItem

    def createEditor(self, parent, option, index):
        editor = CLabelComboBox(parent)
        for idx, i in enumerate(self.listItem):
            item_text = str(i)
            # 在展开的下拉菜单选项前增加 1. 2. 序号标记，方便区分选择
            display_text = f"{idx + 1}. {item_text}" if not re.match(r'^\d+\.\s*', item_text) else item_text
            editor.addItem(display_text, item_text)
        editor.currentIndexChanged.connect(self.editorIndexChanged)

        # 监听弹出列表视图上的快捷键，确保 Q 键随时一击必删
        if editor.view():
            self._popup_filter = PopupKeyFilter(editor, editor.view())
            editor.view().installEventFilter(self._popup_filter)
        
        curr_text = index.model().data(index, Qt.EditRole)
        tindex = -1
        for k in range(editor.count()):
            if editor.itemData(k) == curr_text or editor.itemText(k) == curr_text:
                tindex = k
                break
        if tindex >= 0:
            editor.setCurrentIndex(tindex)
        else:
            editor.setCurrentIndex(0)

        # 单击选中框时安全展开下拉列表 (使用 weakref 避免删除 C++ 对象引起 RuntimeError)
        w_editor = weakref.ref(editor)
        def popup_safely():
            try:
                ed = w_editor()
                if ed is not None:
                    ed.showPopup()
            except (RuntimeError, AttributeError):
                pass

        QTimer.singleShot(50, popup_safely)
        return editor

    # commit data early, prevent to loss data when clicking OpenNextImg
    def editorIndexChanged(self, index):
        try:
            combox = self.sender()
            if combox is not None:
                self.commitData.emit(combox)
                self.closeEditor.emit(combox)
        except (RuntimeError, AttributeError):
            pass

    def setEditorData(self, editor, index):
        try:
            text = index.model().data(index, Qt.EditRole)
            if sys.version_info < (3, 0, 0):
                text = text.toPyObject()
            combox = editor
            tindex = -1
            for k in range(combox.count()):
                if combox.itemData(k) == text or combox.itemText(k) == text:
                    tindex = k
                    break
            if tindex >= 0:
                combox.setCurrentIndex(tindex)
        except (RuntimeError, AttributeError):
            pass

    def setModelData(self, editor, model, index):
        try:
            comboBox = editor
            clean_data = comboBox.currentData()
            if clean_data is None:
                raw_text = comboBox.currentText()
                clean_data = re.sub(r'^\d+\.\s*', '', raw_text) if raw_text else raw_text
            old_str = index.model().data(index, Qt.EditRole)
            if clean_data != old_str:
                model.setData(index, clean_data, Qt.EditRole)
        except (RuntimeError, AttributeError):
            pass

    def updateEditorGeometry(self, editor, option, index):
        try:
            editor.setGeometry(option.rect)
        except (RuntimeError, AttributeError):
            pass


class CEditDelegate(QStyledItemDelegate):
    def __init__(self, parent):
        super(CEditDelegate, self).__init__(parent)
        self.editor = None
        self.parent = parent
        
    def createEditor(self, parent, option, index):
        self.editor = QLineEdit(parent)
        self.editor.textEdited.connect(self.textEdited)
        return self.editor

    def textEdited(self, str):
        self.parent.extraChanged(str)

    def setEditorData(self, editor, index):
        return super(CEditDelegate, self).setEditorData(editor, index)

    def destroyEditor(self, editor, index):
        self.parent.extraChanged(index.data())
        ret = super(CEditDelegate, self).destroyEditor(editor, index)
        self.editor = None
        return ret

    def earlyCommit(self, index):
        if self.editor is not None:
            self.commitData.emit(self.editor)
            self.destroyEditor(self.editor, index)


class CHeaderView(QHeaderView):
    clicked = pyqtSignal(int, bool)
    _x_offset = 3
    _y_offset = 0 # This value is calculated later, based on the height of the paint rect
    _width = 18
    _height = 18

    def __init__(self, orientation, parent=None):
        super(CHeaderView, self).__init__(orientation, parent)
        self.setFixedWidth(55)
        self.isChecked = []

    def rowsInserted(self, parent, start, end):
        self.isChecked.insert(start, 1)
        return super(CHeaderView, self).rowsInserted(parent, start, end)

    def rowsAboutToBeRemoved(self, parent, start, end):
        del self.isChecked[start]
        return super(CHeaderView, self).rowsAboutToBeRemoved(parent, start, end)

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()
        self._y_offset = int((rect.height()-self._width)/2.)
        
        option = QStyleOptionButton()
        option.state = QStyle.State_Enabled | QStyle.State_Active
        option.rect = QRect(rect.x() + self._x_offset, rect.y() + self._y_offset, self._width, self._height)
        
        if logicalIndex < len(self.isChecked) and self.isChecked[logicalIndex]:
            option.state |= QStyle.State_On
        else:
            option.state |= QStyle.State_Off

        self.style().drawPrimitive(QStyle.PE_IndicatorCheckBox, option, painter)

        # 绘制独立清晰的 1, 2, 3... 行号标记
        num_str = f"{logicalIndex + 1}"
        painter.setPen(QColor(60, 60, 60))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(9)
        painter.setFont(font)
        text_rect = QRect(rect.x() + self._width + 4, rect.y(), rect.width() - self._width - 4, rect.height())
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, num_str)
        painter.restore()
        #self.style().drawControl(QStyle.CE_CheckBox, option, painter)
    
    def mouseReleaseEvent(self, e):
        index = self.logicalIndexAt(e.pos())
        
        if 0 <= index < self.count():
            # vertical orientation
            y = self.sectionViewportPosition(index)
            if self._x_offset < e.pos().x() < self._x_offset + self._width \
                and y + self._y_offset < e.pos().y() < y + self._y_offset + self._height:
                if self.isChecked[index] == 1:
                    self.isChecked[index] = 0
                else:
                    self.isChecked[index] = 1
                self.clicked.emit(index, self.isChecked[index])
                
                self.viewport().update()
            else:
                super(CHeaderView, self).mousePressEvent(e)
        else:
            super(CHeaderView, self).mousePressEvent(e)


class CLabelView(QTableView):
    extraEditing = pyqtSignal(QModelIndex, str)
    toggleEdit = pyqtSignal(bool)
    def __init__(self, labelHist, parent = None):
        super(CLabelView, self).__init__(parent)
        
        header = CHeaderView(Qt.Vertical, self)
        self.setVerticalHeader(header)

        self.label_delegate = CComboBoxDelegate(self, labelHist)
        self.setItemDelegateForColumn(0, self.label_delegate)
        self.extra_delegate = CEditDelegate(self)
        self.setItemDelegateForColumn(1, self.extra_delegate)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        # 禁用默认按键触发编辑，防止按 Q 键被 QTableView 误当做按键编辑触发器
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.clicked.connect(self.on_table_clicked)

        self.setStyleSheet("""
            QTableView {
                selection-background-color: #FFFFFF;
                selection-color: #000000;
            }
            QTableView::item:selected {
                background-color: #FFFFFF;
                color: #000000;
                font-weight: bold;
                border: 1px solid #2563EB;
            }
        """)

        model = QStandardItemModel(self)
        model.setColumnCount(2)
        model.setHorizontalHeaderLabels(["Label", "Extra Info"])

        self.setModel(model)
        
        self.sm = self.selectionModel()

    def on_table_clicked(self, index):
        # 单击右侧表格对应项时直接展开标签下拉选择栏，无需双击
        if index.isValid() and index.column() == 0:
            self.edit(index)

    def extraChanged(self, str):
        self.extraEditing.emit(self.sm.currentIndex(), str)

    def earlyCommit(self):
        # TODO: verify currentIndex
        extra_index = self.model().index(self.sm.currentIndex().row(), 1)
        self.extra_delegate.earlyCommit(extra_index)

    def updateLabelList(self, labelHist):
        self.label_delegate.updateListItem(labelHist)

    def keyPressEvent(self, e):
        key = e.key()
        txt = e.text().lower() if e.text() else ""
        if key in (Qt.Key_Q, Qt.Key_Delete, Qt.Key_Backspace) or txt == 'q':
            win = self.window()
            if hasattr(win, 'deleteSelectedShape'):
                win.deleteSelectedShape()
            e.accept()
            return
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            if self.extra_delegate.editor is None:
                self.toggleEdit.emit(True)
        return super(CLabelView, self).keyPressEvent(e)

    def wheelEvent(self, ev):
        """当鼠标处于右侧标签列表上且有选中行时，滚轮可在各标签之间滚动切换选中"""
        row_count = self.model().rowCount()
        if row_count <= 0:
            return super(CLabelView, self).wheelEvent(ev)

        current = self.sm.currentIndex()
        if not current.isValid() or current.row() < 0:
            return super(CLabelView, self).wheelEvent(ev)

        delta = ev.angleDelta().y() if hasattr(ev, 'angleDelta') else ev.delta()
        if delta == 0:
            return super(CLabelView, self).wheelEvent(ev)

        cur_row = current.row()
        if delta > 0:
            new_row = max(0, cur_row - 1)
        else:
            new_row = min(row_count - 1, cur_row + 1)

        if new_row != cur_row:
            new_idx = self.model().index(new_row, 0)
            self.selectRow(new_row)
            self.sm.setCurrentIndex(new_idx, self.sm.ClearAndSelect | self.sm.Rows)
            self.scrollTo(new_idx)

        ev.accept()