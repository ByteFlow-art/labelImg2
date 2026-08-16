import os
from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, 
    QListWidget, QListWidgetItem, QLabel, QFileDialog, QFrame, QComboBox
)

class LeftPanel(QWidget):
    """
    左侧文件/数据集列表控制面板
    """
    image_selected = pyqtSignal(str)          # (image_path)
    directory_loaded = pyqtSignal(str, list)   # (dir_path, image_paths)

    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff'}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_dir: Optional[str] = None
        self.image_paths: List[str] = []
        self.status_map = {}  # {img_path: 'labeled' | 'unlabeled' | 'auto'}

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. 文件夹导入按钮与全盘选择
        btn_layout = QHBoxLayout()
        self.btn_open_dir = QPushButton("📁 打开图片文件夹")
        self.btn_open_dir.setObjectName("btn_secondary")
        self.btn_open_dir.clicked.connect(self.select_directory)
        btn_layout.addWidget(self.btn_open_dir)

        layout.addLayout(btn_layout)

        # 2. 文件夹路径展示标签
        self.lbl_dir_info = QLabel("未选择文件夹")
        self.lbl_dir_info.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.lbl_dir_info.setWordWrap(True)
        layout.addWidget(self.lbl_dir_info)

        # 3. 统计与过滤条
        filter_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 搜索文件名...")
        self.txt_search.textChanged.connect(self.filter_items)
        filter_layout.addWidget(self.txt_search)

        self.combo_filter = QComboBox()
        self.combo_filter.addItems(["全部图片", "仅已标注", "仅未标注"])
        self.combo_filter.currentIndexChanged.connect(self.filter_items)
        filter_layout.addWidget(self.combo_filter)

        layout.addLayout(filter_layout)

        # 4. 图片文件列表 Widget
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.on_item_changed)
        layout.addWidget(self.list_widget)

        # 5. 上一张/下一张 导航控制条
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("⬅ 上一张 (A)")
        self.btn_prev.setObjectName("btn_secondary")
        self.btn_prev.clicked.connect(self.select_previous)

        self.btn_next = QPushButton("下一张 (D) ➡")
        self.btn_next.setObjectName("btn_secondary")
        self.btn_next.clicked.connect(self.select_next)

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.btn_next)
        layout.addLayout(nav_layout)

        # 底部计数卡片
        self.lbl_stats = QLabel("已加载: 0 张图片")
        self.lbl_stats.setStyleSheet("color: #60A5FA; font-weight: bold;")
        layout.addWidget(self.lbl_stats)

    def select_directory(self):
        init_d = ""
        p = self.parent()
        if p and hasattr(p, 'lastOpenDir') and p.lastOpenDir and os.path.exists(p.lastOpenDir):
            init_d = p.lastOpenDir
        dir_path = QFileDialog.getExistingDirectory(self, "选择图片数据集文件夹", init_d)
        if dir_path and os.path.exists(dir_path):
            if p and hasattr(p, 'lastOpenDir'):
                p.lastOpenDir = dir_path
                if hasattr(p, 'settings'):
                    p.settings['lastOpenDir'] = dir_path
                    p.settings.save()
            self.load_directory(dir_path)

    def load_directory(self, dir_path: str):
        self.current_dir = dir_path
        self.lbl_dir_info.setText(f"📁 {os.path.basename(dir_path)}")

        # 扫盘寻找图片文件
        self.image_paths = []
        for file in os.listdir(dir_path):
            ext = os.path.splitext(file)[1].lower()
            if ext in self.IMAGE_EXTENSIONS:
                self.image_paths.append(os.path.join(dir_path, file))

        self.image_paths.sort()
        self.refresh_list()
        self.directory_loaded.emit(dir_path, self.image_paths)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def refresh_list(self):
        self.list_widget.clear()
        labeled_cnt = 0

        for idx, img_path in enumerate(self.image_paths, 1):
            filename = os.path.basename(img_path)
            stem = os.path.splitext(filename)[0]
            xml_path = os.path.join(os.path.dirname(img_path), f"{stem}.xml")

            is_labeled = os.path.exists(xml_path)
            if is_labeled:
                labeled_cnt += 1
                status_text = f"{idx}. 🟢 {filename}"
                self.status_map[img_path] = 'labeled'
            else:
                status_text = f"{idx}. ⚪ {filename}"
                self.status_map[img_path] = 'unlabeled'

            item = QListWidgetItem(status_text)
            item.setData(Qt.ItemDataRole.UserRole, img_path)
            
            if is_labeled:
                item.setForeground(QColor(52, 211, 153))  # Emerald Green
            else:
                item.setForeground(QColor(148, 163, 184))  # Slate Gray

            self.list_widget.addItem(item)

        total = len(self.image_paths)
        self.lbl_stats.setText(f"总计: {total} | 已标注: {labeled_cnt} | 未标注: {total - labeled_cnt}")

    def update_item_status(self, img_path: str, is_auto: bool = False):
        """标注完成后更新特定列表项的图标与状态"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == img_path:
                filename = os.path.basename(img_path)
                idx = i + 1
                if is_auto:
                    item.setText(f"{idx}. 🔵 {filename}")
                    item.setForeground(QColor(96, 165, 250)) # Blue
                else:
                    item.setText(f"{idx}. 🟢 {filename}")
                    item.setForeground(QColor(52, 211, 153)) # Green
                break

    def filter_items(self):
        search_kw = self.txt_search.text().lower()
        filter_mode = self.combo_filter.currentIndex()

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            img_path = item.data(Qt.ItemDataRole.UserRole)
            filename = os.path.basename(img_path).lower()
            status = self.status_map.get(img_path, 'unlabeled')

            match_search = search_kw in filename
            match_status = True
            if filter_mode == 1: # 仅已标注
                match_status = (status == 'labeled' or status == 'auto')
            elif filter_mode == 2: # 仅未标注
                match_status = (status == 'unlabeled')

            item.setHidden(not (match_search and match_status))

    def on_item_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if current:
            img_path = current.data(Qt.ItemDataRole.UserRole)
            self.image_selected.emit(img_path)

    def select_previous(self):
        row = self.list_widget.currentRow()
        if row > 0:
            self.list_widget.setCurrentRow(row - 1)

    def select_next(self):
        row = self.list_widget.currentRow()
        if row < self.list_widget.count() - 1:
            self.list_widget.setCurrentRow(row + 1)
