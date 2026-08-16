import os
from typing import Dict, List, Any, Optional
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel,
    QGroupBox, QTableWidget, QTableWidgetItem, QCheckBox, QProgressBar,
    QFileDialog, QRadioButton, QSpinBox, QDoubleSpinBox, QHeaderView, QColorDialog
)
from ui.canvas import CLASS_COLORS

class RightPanel(QWidget):
    """
    右侧模型控制、推断阈值、类别重命名与批量任务控制面板
    """
    model_loaded = pyqtSignal(str)                   # (model_path)
    run_single_auto = pyqtSignal()                   # 一键单图推断
    run_batch_auto = pyqtSignal()                    # 一键批量推断
    stop_batch = pyqtSignal()                         # 停止批量
    save_current_annotation = pyqtSignal()           # 保存当前图片标注
    class_mapping_changed = pyqtSignal()             # 类别映射规则变更

    def __init__(self, parent=None):
        super().__init__(parent)
        self.class_info_list: List[Dict[str, Any]] = [] # [{id, name, mapped_name, enabled, color}]
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # 1. 模型加载与设备配置区域
        group_model = QGroupBox("🤖 YOLO 模型与设备配置")
        model_layout = QVBoxLayout()

        m_btn_layout = QHBoxLayout()
        self.btn_load_model = QPushButton("📂 加载 YOLO 模型 (.pt)")
        self.btn_load_model.setObjectName("btn_secondary")
        self.btn_load_model.clicked.connect(self.select_model_file)
        m_btn_layout.addWidget(self.btn_load_model)

        model_layout.addLayout(m_btn_layout)

        self.lbl_model_status = QLabel("状态: 尚未加载模型")
        self.lbl_model_status.setStyleSheet("color: #F59E0B; font-size: 12px;")
        self.lbl_model_status.setWordWrap(True)
        model_layout.addWidget(self.lbl_model_status)

        self.lbl_device_info = QLabel("推理设备: 检测中...")
        self.lbl_device_info.setStyleSheet("color: #94A3B8; font-size: 11px;")
        model_layout.addWidget(self.lbl_device_info)

        group_model.setLayout(model_layout)
        layout.addWidget(group_model)

        # 2. 推理参数调节区域
        group_params = QGroupBox("🎛 置信度与 NMS 阈值")
        param_layout = QVBoxLayout()

        # Conf 置信度滑块
        conf_box = QHBoxLayout()
        conf_box.addWidget(QLabel("Conf (置信度):"))
        self.lbl_conf_val = QLabel("0.25")
        self.lbl_conf_val.setStyleSheet("color: #3B82F6; font-weight: bold;")
        
        self.slider_conf = QSlider(Qt.Orientation.Horizontal)
        self.slider_conf.setRange(1, 100)
        self.slider_conf.setValue(25)
        self.slider_conf.valueChanged.connect(self.on_conf_changed)

        conf_box.addWidget(self.slider_conf)
        conf_box.addWidget(self.lbl_conf_val)
        param_layout.addLayout(conf_box)

        # IoU NMS 滑块
        iou_box = QHBoxLayout()
        iou_box.addWidget(QLabel("IoU (重叠率):"))
        self.lbl_iou_val = QLabel("0.45")
        self.lbl_iou_val.setStyleSheet("color: #3B82F6; font-weight: bold;")

        self.slider_iou = QSlider(Qt.Orientation.Horizontal)
        self.slider_iou.setRange(1, 100)
        self.slider_iou.setValue(45)
        self.slider_iou.valueChanged.connect(self.on_iou_changed)

        iou_box.addWidget(self.slider_iou)
        iou_box.addWidget(self.lbl_iou_val)
        param_layout.addLayout(iou_box)

        group_params.setLayout(param_layout)
        layout.addWidget(group_params)

        # 3. 类别管理与 XML 输出标签重命名表
        group_classes = QGroupBox("🏷 类别列表与 XML <name> 标签映射")
        cls_layout = QVBoxLayout()

        self.table_classes = QTableWidget(0, 4)
        self.table_classes.setHorizontalHeaderLabels(["启用", "模型类别", "XML导出标签(可双击编辑)", "颜色"])
        self.table_classes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_classes.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_classes.cellChanged.connect(self.on_table_cell_changed)

        cls_layout.addWidget(self.table_classes)
        group_classes.setLayout(cls_layout)
        layout.addWidget(group_classes)

        # 4. 导出格式与覆盖模式规则
        group_export = QGroupBox("💾 导出选项设置")
        export_layout = QVBoxLayout()

        fmt_box = QHBoxLayout()
        self.chk_export_xml = QCheckBox("Pascal VOC XML (.xml)")
        self.chk_export_xml.setChecked(True)
        self.chk_export_txt = QCheckBox("YOLO TXT (.txt)")
        fmt_box.addWidget(self.chk_export_xml)
        fmt_box.addWidget(self.chk_export_txt)
        export_layout.addLayout(fmt_box)

        mode_box = QHBoxLayout()
        self.rad_overwrite = QRadioButton("覆盖已有 XML 标注")
        self.rad_overwrite.setChecked(True)
        self.rad_append = QRadioButton("保留并增量追加标注")
        mode_box.addWidget(self.rad_overwrite)
        mode_box.addWidget(self.rad_append)
        export_layout.addLayout(mode_box)

        group_export.setLayout(export_layout)
        layout.addWidget(group_export)

        # 5. 一键标注与批量推断按钮
        btn_action_layout = QVBoxLayout()
        
        self.btn_single_auto = QPushButton("自动标注当前单图 (S)")
        self.btn_single_auto.setObjectName("btn_secondary")
        self.btn_single_auto.clicked.connect(self.run_single_auto.emit)
        btn_action_layout.addWidget(self.btn_single_auto)

        self.btn_batch_auto = QPushButton("一键批量全自动标注")
        self.btn_batch_auto.setObjectName("btn_primary")
        self.btn_batch_auto.clicked.connect(self.run_batch_auto.emit)
        btn_action_layout.addWidget(self.btn_batch_auto)

        self.btn_save_curr = QPushButton("保存当前图标注 (Ctrl+S)")
        self.btn_save_curr.setObjectName("btn_secondary")
        self.btn_save_curr.clicked.connect(self.save_current_annotation.emit)
        btn_action_layout.addWidget(self.btn_save_curr)

        self.btn_stop = QPushButton("停止批量任务")
        self.btn_stop.setObjectName("btn_danger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_batch.emit)
        btn_action_layout.addWidget(self.btn_stop)

        layout.addLayout(btn_action_layout)

        # 6. 进度条与状态显示
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.lbl_batch_status = QLabel("等待执行任务...")
        self.lbl_batch_status.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(self.lbl_batch_status)

    def select_model_file(self):
        init_d = ""
        p = self.parent()
        if p and hasattr(p, 'lastOpenDir') and p.lastOpenDir and os.path.exists(p.lastOpenDir):
            init_d = p.lastOpenDir
        file_path, _ = QFileDialog.getOpenFileName(self, "选择 YOLO 模型权重文件", init_d, "YOLO Models (*.pt *.onnx)")
        if file_path and os.path.exists(file_path):
            d = os.path.dirname(file_path)
            if p and hasattr(p, 'lastOpenDir'):
                p.lastOpenDir = d
                if hasattr(p, 'settings'):
                    p.settings['lastOpenDir'] = d
                    p.settings.save()
            self.model_loaded.emit(file_path)

    def update_model_info(self, model_path: str, class_dict: Dict[int, str], device: str):
        self.lbl_model_status.setText(f"已加载: {os.path.basename(model_path)}")
        self.lbl_model_status.setStyleSheet("color: #10B981; font-weight: bold;")
        self.lbl_device_info.setText(f"推理计算设备: {device.upper()}")

        self.class_info_list = []
        for cls_id, cls_name in class_dict.items():
            color = CLASS_COLORS[cls_id % len(CLASS_COLORS)]
            self.class_info_list.append({
                "id": cls_id,
                "name": cls_name,
                "mapped_name": cls_name, # 默认等于模型原类别名
                "enabled": True,
                "color": color
            })

        self.populate_class_table()

    def populate_class_table(self):
        self.table_classes.blockSignals(True)
        self.table_classes.setRowCount(len(self.class_info_list))

        for row, info in enumerate(self.class_info_list):
            # Checkbox Column
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk_item.setCheckState(Qt.CheckState.Checked if info["enabled"] else Qt.CheckState.Unchecked)
            self.table_classes.setItem(row, 0, chk_item)

            # Original Class Name
            orig_item = QTableWidgetItem(info["name"])
            orig_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table_classes.setItem(row, 1, orig_item)

            # XML Mapped Name (Editable)
            map_item = QTableWidgetItem(info["mapped_name"])
            map_item.setFlags(Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)
            self.table_classes.setItem(row, 2, map_item)

            # Color Indicator Item
            color_item = QTableWidgetItem("  ")
            color_item.setBackground(info["color"])
            color_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table_classes.setItem(row, 3, color_item)

        self.table_classes.blockSignals(False)

    def on_table_cell_changed(self, row: int, column: int):
        if row < len(self.class_info_list):
            if column == 0:
                chk_item = self.table_classes.item(row, 0)
                self.class_info_list[row]["enabled"] = (chk_item.checkState() == Qt.CheckState.Checked)
            elif column == 2:
                map_item = self.table_classes.item(row, 2)
                self.class_info_list[row]["mapped_name"] = map_item.text().strip()
            
            self.class_mapping_changed.emit()

    def on_conf_changed(self, val: int):
        conf = val / 100.0
        self.lbl_conf_val.setText(f"{conf:.2f}")

    def on_iou_changed(self, val: int):
        iou = val / 100.0
        self.lbl_iou_val.setText(f"{iou:.2f}")

    def get_conf_threshold(self) -> float:
        return self.slider_conf.value() / 100.0

    def get_iou_threshold(self) -> float:
        return self.slider_iou.value() / 100.0

    def get_class_mapping(self) -> Dict[str, str]:
        """返回 {original_name: mapped_name} 映射词典"""
        mapping = {}
        for info in self.class_info_list:
            if info["enabled"]:
                mapping[info["name"]] = info["mapped_name"]
        return mapping

    def get_enabled_class_ids(self) -> Optional[List[int]]:
        """返回被勾选使能检测的类别 ID 列表"""
        enabled = [info["id"] for info in self.class_info_list if info["enabled"]]
        return enabled if len(enabled) < len(self.class_info_list) else None

    def get_export_options(self) -> Dict[str, bool]:
        return {
            "save_xml": self.chk_export_xml.isChecked(),
            "save_yolo_txt": self.chk_export_txt.isChecked(),
            "overwrite": self.rad_overwrite.isChecked()
        }

    def set_batch_running(self, running: bool):
        self.btn_batch_auto.setEnabled(not running)
        self.btn_single_auto.setEnabled(not running)
        self.btn_load_model.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    def update_progress(self, current: int, total: int, filename: str, status_msg: str):
        if total > 0:
            val = int(current / total * 100)
            self.progress_bar.setValue(val)
        self.lbl_batch_status.setText(f"[{current}/{total}] {filename} - {status_msg}")
