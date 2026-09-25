# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import sys
import re
import codecs
from PyQt5.QtGui import QIcon, QFont, QColor, QBrush, QCursor, QDesktopServices
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QListWidget, QListWidgetItem,
    QMessageBox, QInputDialog, QGroupBox, QDialogButtonBox,
    QAbstractItemView, QFrame, QSizePolicy
)

from .lib import newIcon, labelValidator

BB = QDialogButtonBox

DIALOG_STYLE = """
QDialog {
    background-color: #F8FAFC;
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
}
QGroupBox {
    font-size: 13px;
    font-weight: bold;
    color: #1E293B;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    background-color: #FFFFFF;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background-color: #FFFFFF;
}
QLabel {
    color: #334155;
    font-size: 12px;
}
QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    padding: 6px 10px;
    font-size: 13px;
    color: #0F172A;
}
QLineEdit:focus {
    border: 1px solid #3B82F6;
    background-color: #F8FAFC;
}
QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 13px;
    color: #0F172A;
    min-height: 26px;
}
QComboBox:hover {
    border: 1px solid #94A3B8;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #E2E8F0;
}
QListWidget {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    font-size: 13px;
    outline: none;
}
QListWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #F1F5F9;
    color: #1E293B;
}
QListWidget::item:hover {
    background-color: #F1F5F9;
}
QListWidget::item:selected {
    background-color: #E0E7FF;
    color: #1E40AF;
    font-weight: 600;
}
QPushButton {
    background-color: #FFFFFF;
    color: #334155;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #F1F5F9;
    border-color: #94A3B8;
    color: #0F172A;
}
QPushButton:pressed {
    background-color: #E2E8F0;
}
QPushButton#btn_primary {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
    font-weight: 600;
}
QPushButton#btn_primary:hover {
    background-color: #1D4ED8;
}
QPushButton#btn_danger {
    background-color: #FEE2E2;
    color: #B91C1C;
    border: 1px solid #FECACA;
}
QPushButton#btn_danger:hover {
    background-color: #FCA5A5;
    color: #7F1D1D;
}
QPushButton#btn_success {
    background-color: #ECFDF5;
    color: #047857;
    border: 1px solid #A7F3D0;
}
QPushButton#btn_success:hover {
    background-color: #D1FAE5;
    color: #065F46;
}
"""

class LabelDialog(QDialog):
    def __init__(self, text="Enter object label", parent=None, listItem=None, currentFile=None, dataDir=None):
        super(LabelDialog, self).__init__(parent)
        self.setWindowTitle("标签组与类别管理 (Manage Labels & Groups)")
        self.resize(600, 620)
        self.setMinimumSize(540, 560)
        self.setStyleSheet(DIALOG_STYLE)

        self.data_dir = self._detect_data_dir(dataDir)
        self.current_file_path = currentFile
        self.default_label = None
        self._block_group_change = False

        self._init_ui()

        # 初始化扫描 data 目录中的 .txt 标签组
        self.scan_data_dir(prefer_file=self.current_file_path)

        # 如果传入了初始列表且未能从文件加载，使用传入的列表
        if listItem and self.listWidget.count() == 0:
            self.set_labels(listItem, default_label=listItem[0] if listItem else None)

    def _detect_data_dir(self, custom_dir=None):
        if custom_dir and os.path.isdir(custom_dir):
            return os.path.abspath(custom_dir)

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_p = os.path.join(base_dir, "data")
        if os.path.isdir(data_p):
            return data_p

        cwd_data = os.path.join(os.getcwd(), "data")
        if os.path.isdir(cwd_data):
            return cwd_data

        if hasattr(sys, '_MEIPASS'):
            mei_data = os.path.join(sys._MEIPASS, "data")
            if os.path.isdir(mei_data):
                return mei_data

        return os.path.abspath("data")

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # ---------------- 1. 顶部标签组选择面板 ----------------
        group_box = QGroupBox("1. 标签组选择 (data 目录中的 .txt 文件)")
        group_layout = QVBoxLayout(group_box)
        group_layout.setContentsMargins(14, 16, 14, 14)
        group_layout.setSpacing(10)

        row1 = QHBoxLayout()
        lbl_group = QLabel("当前标签组:")
        lbl_group.setStyleSheet("font-weight: bold;")
        self.groupCombo = QComboBox()
        self.groupCombo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.groupCombo.currentIndexChanged.connect(self.on_group_changed)

        btn_refresh = QPushButton("刷新")
        btn_refresh.setToolTip("重新扫描 data 目录下的所有 .txt 标签组")
        btn_refresh.clicked.connect(self.scan_data_dir)

        btn_open_folder = QPushButton("打开目录")
        btn_open_folder.setToolTip("在系统文件管理器中打开 data 目录")
        btn_open_folder.clicked.connect(self.open_data_folder)

        row1.addWidget(lbl_group)
        row1.addWidget(self.groupCombo, 1)
        row1.addWidget(btn_refresh)
        row1.addWidget(btn_open_folder)
        group_layout.addLayout(row1)

        row2 = QHBoxLayout()
        btn_new_group = QPushButton("新建标签组...")
        btn_new_group.setIcon(newIcon('icon_open_file.svg'))
        btn_new_group.clicked.connect(self.new_group)

        self.btn_save_file = QPushButton("保存修改到当前 .txt 文件")
        self.btn_save_file.setIcon(newIcon('save.svg'))
        self.btn_save_file.setObjectName("btn_success")
        self.btn_save_file.setToolTip("将当前列表中的修改（增删改排序）保存回当前的 .txt 标签文件")
        self.btn_save_file.clicked.connect(self.save_to_current_file)

        self.lbl_file_path = QLabel("")
        self.lbl_file_path.setStyleSheet("color: #64748B; font-size: 11px;")

        row2.addWidget(btn_new_group)
        row2.addWidget(self.btn_save_file)
        row2.addStretch()
        row2.addWidget(self.lbl_file_path)
        group_layout.addLayout(row2)

        main_layout.addWidget(group_box)

        # ---------------- 2. 中间标签类别管理面板 ----------------
        list_box = QGroupBox("2. 标签类别列表 (双击设为默认，支持增删改排)")
        list_layout = QVBoxLayout(list_box)
        list_layout.setContentsMargins(14, 16, 14, 14)
        list_layout.setSpacing(10)

        # 编辑输入行
        edit_layout = QHBoxLayout()
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("输入标签名称...")
        self.edit.setValidator(labelValidator())
        self.edit.returnPressed.connect(self.add_label)

        btn_add = QPushButton("添加")
        btn_add.setObjectName("btn_primary")
        btn_add.clicked.connect(self.add_label)

        btn_modify = QPushButton("修改")
        btn_modify.clicked.connect(self.modify_label)

        btn_delete = QPushButton("删除")
        btn_delete.setObjectName("btn_danger")
        btn_delete.clicked.connect(self.delete_label)

        btn_set_default = QPushButton("设为默认")
        btn_set_default.setToolTip("将当前选中的标签设为新建标注框时的默认类别")
        btn_set_default.clicked.connect(self.set_as_default)

        edit_layout.addWidget(self.edit, 1)
        edit_layout.addWidget(btn_add)
        edit_layout.addWidget(btn_modify)
        edit_layout.addWidget(btn_delete)
        edit_layout.addWidget(btn_set_default)
        list_layout.addLayout(edit_layout)

        # 列表与排序辅助操作
        content_layout = QHBoxLayout()
        self.listWidget = QListWidget()
        self.listWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.listWidget.itemClicked.connect(self.on_item_clicked)
        self.listWidget.itemDoubleClicked.connect(self.on_item_double_clicked)

        order_layout = QVBoxLayout()
        btn_up = QPushButton("上移")
        btn_up.clicked.connect(self.move_up)
        btn_down = QPushButton("下移")
        btn_down.clicked.connect(self.move_down)
        btn_clear = QPushButton("清空")
        btn_clear.clicked.connect(self.clear_labels)

        order_layout.addWidget(btn_up)
        order_layout.addWidget(btn_down)
        order_layout.addStretch()
        order_layout.addWidget(btn_clear)

        content_layout.addWidget(self.listWidget, 1)
        content_layout.addLayout(order_layout)
        list_layout.addLayout(content_layout)

        main_layout.addWidget(list_box, 1)

        # ---------------- 3. 底部状态与操作按钮 ----------------
        bottom_layout = QHBoxLayout()
        self.lbl_status = QLabel("就绪")
        self.lbl_status.setStyleSheet("color: #475569; font-weight: 500;")

        self.buttonBox = BB(BB.Ok | BB.Cancel, Qt.Horizontal, self)
        self.buttonBox.button(BB.Ok).setText("确认应用")
        self.buttonBox.button(BB.Ok).setObjectName("btn_primary")
        self.buttonBox.button(BB.Cancel).setText("取消")
        self.buttonBox.accepted.connect(self.validate)
        self.buttonBox.rejected.connect(self.reject)

        bottom_layout.addWidget(self.lbl_status)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.buttonBox)
        main_layout.addLayout(bottom_layout)

    def scan_data_dir(self, prefer_file=None):
        """扫描 data 目录下的所有 .txt 文件并填充下拉框"""
        self._block_group_change = True
        self.groupCombo.clear()

        if not os.path.isdir(self.data_dir):
            try:
                os.makedirs(self.data_dir, exist_ok=True)
            except Exception:
                pass

        txt_files = []
        if os.path.isdir(self.data_dir):
            for fname in os.listdir(self.data_dir):
                if fname.lower().endswith(".txt"):
                    full_p = os.path.join(self.data_dir, fname)
                    if os.path.isfile(full_p):
                        txt_files.append((fname, full_p))

        # 排序：让 predefined_classes.txt / predefined_classes1.txt 优先排前，其余按名称字母排
        def sort_key(item):
            fn = item[0].lower()
            if fn == "predefined_classes.txt":
                return (0, fn)
            elif fn.startswith("predefined_classes"):
                return (1, fn)
            return (2, fn)

        txt_files.sort(key=sort_key)

        target_idx = 0
        prefer_path = os.path.abspath(prefer_file) if prefer_file else None

        for idx, (fname, fpath) in enumerate(txt_files):
            count = 0
            try:
                with codecs.open(fpath, 'r', 'utf8', errors='ignore') as f:
                    count = len([line for line in f if line.strip()])
            except Exception:
                pass

            display_name = f"{fname}  ({count} 类)"
            self.groupCombo.addItem(display_name, fpath)

            if prefer_path and os.path.abspath(fpath) == prefer_path:
                target_idx = idx

        self._block_group_change = False

        if self.groupCombo.count() > 0:
            self.groupCombo.setCurrentIndex(target_idx)
            self.load_group_by_index(target_idx)
        else:
            self.current_file_path = None
            self.lbl_file_path.setText("data 目录下无 .txt 文件")
            self.update_status()

    def on_group_changed(self, index):
        if self._block_group_change or index < 0:
            return
        self.load_group_by_index(index)

    def load_group_by_index(self, index):
        fpath = self.groupCombo.itemData(index)
        if not fpath or not os.path.isfile(fpath):
            return

        self.current_file_path = fpath
        self.lbl_file_path.setText(os.path.basename(fpath))
        self.lbl_file_path.setToolTip(fpath)

        # 读取文件内容
        labels = []
        try:
            with codecs.open(fpath, 'r', 'utf8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and line not in labels:
                        labels.append(line)
        except Exception as e:
            QMessageBox.warning(self, "读取失败", f"无法读取标签文件:\n{fpath}\n错误: {e}")
            return

        # 更新列表
        self.set_labels(labels)

    def set_labels(self, labels, default_label=None):
        """设置当前列表展示的标签项"""
        self.listWidget.clear()
        if not labels:
            self.default_label = None
            self.update_status()
            return

        if default_label and default_label in labels:
            self.default_label = default_label
        elif self.default_label not in labels:
            self.default_label = labels[0]

        for idx, lab in enumerate(labels):
            self._create_list_item(idx + 1, lab, is_default=(lab == self.default_label))

        self.update_status()

    def _create_list_item(self, index_num, label_text, is_default=False):
        clean_text = str(label_text).strip()
        item = QListWidgetItem()
        item.setData(Qt.UserRole, clean_text)

        if is_default:
            item.setText(f"[默认] {index_num}. {clean_text}")
            font = QFont()
            font.setBold(True)
            item.setFont(font)
            item.setForeground(QBrush(QColor("#1D4ED8")))
            item.setBackground(QBrush(QColor("#EFF6FF")))
        else:
            item.setText(f"{index_num}. {clean_text}")
            item.setForeground(QBrush(QColor("#1E293B")))
            item.setBackground(QBrush(QColor("#FFFFFF")))

        self.listWidget.addItem(item)
        return item

    def get_labels(self):
        """获取当前列表中的所有纯标签名称列表"""
        labels = []
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            raw = item.data(Qt.UserRole)
            if not raw:
                raw = re.sub(r'^(\[默认\]\s*)?\d+\.\s*', '', item.text())
            raw = str(raw).strip()
            if raw and raw not in labels:
                labels.append(raw)
        return labels

    def refresh_list_display(self):
        """重新整理序号与默认标签标记"""
        labels = self.get_labels()
        selected_row = self.listWidget.currentRow()
        self.listWidget.clear()

        for idx, lab in enumerate(labels):
            self._create_list_item(idx + 1, lab, is_default=(lab == self.default_label))

        if 0 <= selected_row < self.listWidget.count():
            self.listWidget.setCurrentRow(selected_row)

        self.update_status()

    def on_item_clicked(self, item):
        raw = item.data(Qt.UserRole)
        if not raw:
            raw = re.sub(r'^(\[默认\]\s*)?\d+\.\s*', '', item.text())
        self.edit.setText(str(raw).strip())

    def on_item_double_clicked(self, item):
        self.set_as_default()

    def add_label(self):
        txt = self.edit.text().strip()
        if not txt:
            return

        current_labels = self.get_labels()
        if txt in current_labels:
            QMessageBox.information(self, "提示", f"标签 [{txt}] 已经存在于列表中。")
            return

        current_labels.append(txt)
        if not self.default_label:
            self.default_label = txt

        self.set_labels(current_labels, self.default_label)
        self.listWidget.setCurrentRow(self.listWidget.count() - 1)
        self.edit.clear()

    def modify_label(self):
        txt = self.edit.text().strip()
        if not txt:
            return

        row = self.listWidget.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先在列表中选中需要修改的标签项。")
            return

        old_lab = self.listWidget.item(row).data(Qt.UserRole)
        current_labels = self.get_labels()

        if txt != old_lab and txt in current_labels:
            QMessageBox.information(self, "提示", f"标签 [{txt}] 已存在。")
            return

        current_labels[row] = txt
        if self.default_label == old_lab:
            self.default_label = txt

        self.set_labels(current_labels, self.default_label)
        self.listWidget.setCurrentRow(row)

    def delete_label(self):
        row = self.listWidget.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先在列表中选中需要删除的标签。")
            return

        del_item = self.listWidget.item(row)
        del_name = del_item.data(Qt.UserRole)

        current_labels = self.get_labels()
        current_labels.remove(del_name)

        if self.default_label == del_name:
            self.default_label = current_labels[0] if current_labels else None

        self.set_labels(current_labels, self.default_label)
        if current_labels:
            new_row = min(row, len(current_labels) - 1)
            self.listWidget.setCurrentRow(new_row)

    def set_as_default(self):
        row = self.listWidget.currentRow()
        if row < 0:
            return
        item = self.listWidget.item(row)
        lab = item.data(Qt.UserRole)
        self.default_label = lab
        self.refresh_list_display()

    def move_up(self):
        row = self.listWidget.currentRow()
        if row <= 0:
            return
        labels = self.get_labels()
        labels[row - 1], labels[row] = labels[row], labels[row]
        self.set_labels(labels, self.default_label)
        self.listWidget.setCurrentRow(row - 1)

    def move_down(self):
        row = self.listWidget.currentRow()
        if row < 0 or row >= self.listWidget.count() - 1:
            return
        labels = self.get_labels()
        labels[row + 1], labels[row] = labels[row], labels[row + 1]
        self.set_labels(labels, self.default_label)
        self.listWidget.setCurrentRow(row + 1)

    def clear_labels(self):
        if self.listWidget.count() == 0:
            return
        reply = QMessageBox.question(
            self,
            "清空确认",
            "确定要清空当前标签列表中的所有项吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.listWidget.clear()
            self.default_label = None
            self.update_status()

    def save_to_current_file(self):
        """将当前修改保存回选中的 .txt 文件"""
        if not self.current_file_path:
            QMessageBox.warning(self, "提示", "当前未选定有效的 .txt 标签文件！")
            return

        labels = self.get_labels()
        try:
            with codecs.open(self.current_file_path, 'w', 'utf8') as f:
                for lab in labels:
                    f.write(f"{lab}\n")

            fname = os.path.basename(self.current_file_path)
            # 刷新下拉框中的类别计数
            curr_idx = self.groupCombo.currentIndex()
            if curr_idx >= 0:
                self._block_group_change = True
                self.groupCombo.setItemText(curr_idx, f"{fname}  ({len(labels)} 类)")
                self._block_group_change = False

            QMessageBox.information(
                self,
                "保存成功",
                f"已成功将 {len(labels)} 个类别保存至文件:\n{self.current_file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入文件时出错:\n{e}")

    def new_group(self):
        """在 data 目录新建一个 .txt 标签文件"""
        name, ok = QInputDialog.getText(
            self,
            "新建标签组",
            "请输入新标签组名称 (无需写 .txt 后缀):",
            QLineEdit.Normal,
            ""
        )
        if not ok or not name.strip():
            return

        name = name.strip()
        if not name.lower().endswith(".txt"):
            filename = f"{name}.txt"
        else:
            filename = name

        new_path = os.path.join(self.data_dir, filename)
        if os.path.exists(new_path):
            QMessageBox.warning(self, "提示", f"文件 [{filename}] 已存在！")
            return

        try:
            with codecs.open(new_path, 'w', 'utf8') as f:
                pass  # 创建空文件
            self.scan_data_dir(prefer_file=new_path)
            QMessageBox.information(self, "新建成功", f"标签组 [{filename}] 创建成功！\n您可以在下方列表中添加标签类别后点击保存。")
        except Exception as e:
            QMessageBox.critical(self, "创建失败", f"无法创建文件:\n{e}")

    def open_data_folder(self):
        """在系统管理器中打开 data 目录"""
        if os.path.exists(self.data_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.data_dir))
        else:
            QMessageBox.warning(self, "提示", f"目录不存在:\n{self.data_dir}")

    def update_status(self):
        count = self.listWidget.count()
        def_text = self.default_label if self.default_label else "无"
        self.lbl_status.setText(f"共 {count} 个标签类别 | 当前默认: [{def_text}]")

    def updateListItems(self, listItem):
        """兼容原有调用方法"""
        self.set_labels(listItem or [])

    def updateData(self, listItem, default_label=None, current_file=None):
        """完整更新数据接口"""
        if current_file and os.path.isfile(current_file):
            self.scan_data_dir(prefer_file=current_file)
        else:
            self.set_labels(listItem or [], default_label=default_label)

    def validate(self):
        labels = self.get_labels()
        if not labels:
            reply = QMessageBox.question(
                self,
                "提示",
                "当前标签列表为空，确定应用吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self.accept()

    def postProcess(self):
        pass

    def popUp(self, move=False):
        if self.parent():
            geo = self.parent().geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(max(0, x), max(0, y))
        elif move:
            self.move(QCursor.pos())

        self.edit.setFocus()
        if self.exec_():
            return self.get_labels(), self.default_label, self.current_file_path
        return None
