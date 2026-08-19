import os
from typing import Optional
from core.qt_compat import *
from core.safe_widgets import SafeComboBox, SafeSpinBox, SafeDoubleSpinBox
from utils.trainer_thread import ModelTrainerThread
from core.yolo_annotator import YOLOAnnotator
from ui.styles import LIGHT_WORKSTATION_STYLE

class TrainDialog(QDialog):
    """
    YOLO 模型训练控制台
    """
    model_trained_signal = pyqtSignal(str) # (best_pt_path)

    def __init__(self, default_image_dir: str = "", default_xml_dir: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("YOLO 模型训练与权重导出")
        ico = self.get_icon("app.ico")
        if ico.isNull():
            ico = self.get_icon("app.png")
        if ico.isNull():
            ico = self.get_icon("labelImg2.ico")
        self.setWindowIcon(ico)
        self.resize(750, 720)

        self.setMinimumSize(760, 660)
        self.setStyleSheet(LIGHT_WORKSTATION_STYLE)

        # 启用非模态窗口与完整的【最小化、最大化、关闭】功能
        non_modal_val = getattr(Qt, 'NonModal', None) or getattr(getattr(Qt, 'WindowModality', None), 'NonModal', 0)
        self.setWindowModality(non_modal_val)
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint
        )

        self.default_image_dir = default_image_dir
        self.default_xml_dir = default_xml_dir or default_image_dir
        self.trainer_thread: Optional[ModelTrainerThread] = None
        self.last_trained_pt: Optional[str] = None

        self.init_ui()
        self.restore_settings()


    def get_icon(self, icon_name: str) -> QIcon:
        from libs.lib import newIcon
        return newIcon(icon_name)


    def create_section_header(self, title_text: str) -> QLabel:
        lbl = QLabel(title_text)
        lbl.setObjectName("section_header")
        lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #1E293B; margin-top: 6px; margin-bottom: 2px;")
        return lbl

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # 滚动区域以保证极端窗口尺寸下的排版灵活性
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(16)

        # 1. 数据集配置 (图片与 XML 分离)
        layout.addWidget(self.create_section_header("1. 训练数据集目录配置"))
        ds_layout = QVBoxLayout()
        ds_layout.setSpacing(10)

        # 图片文件夹
        img_box = QHBoxLayout()
        lbl_img = QLabel("图片文件夹:")
        lbl_img.setMinimumWidth(110)
        img_box.addWidget(lbl_img)

        self.txt_img_path = QLineEdit()
        self.txt_img_path.setText(self.default_image_dir)
        self.txt_img_path.setPlaceholderText("选择包含训练图片的文件夹...")
        img_box.addWidget(self.txt_img_path)

        btn_browse_img = QPushButton(" 选择图片目录")
        btn_browse_img.setIcon(self.get_icon("dir.svg"))
        btn_browse_img.setObjectName("btn_secondary")
        btn_browse_img.clicked.connect(self.browse_image_dir)
        img_box.addWidget(btn_browse_img)
        ds_layout.addLayout(img_box)

        # 标签文件夹
        xml_box = QHBoxLayout()
        lbl_xml = QLabel("标签文件夹:")
        lbl_xml.setMinimumWidth(110)
        xml_box.addWidget(lbl_xml)

        self.txt_xml_path = QLineEdit()
        self.txt_xml_path.setText(self.default_xml_dir)
        self.txt_xml_path.setPlaceholderText("选择保存标签文件的文件夹...")
        xml_box.addWidget(self.txt_xml_path)

        btn_browse_xml = QPushButton(" 选择标签目录")
        btn_browse_xml.setIcon(self.get_icon("dir.svg"))
        btn_browse_xml.setObjectName("btn_secondary")
        btn_browse_xml.clicked.connect(self.browse_xml_dir)
        xml_box.addWidget(btn_browse_xml)
        ds_layout.addLayout(xml_box)

        layout.addLayout(ds_layout)

        # 2. 超参数设置
        layout.addWidget(self.create_section_header("2. 模型与训练超参数配置"))
        grid = QGridLayout()
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(16)

        grid.addWidget(QLabel("基础预训练权重:"), 0, 0)
        self.combo_base_model = SafeComboBox()
        self.refresh_base_models()
        self.combo_base_model.currentIndexChanged.connect(self.on_base_model_changed)
        grid.addWidget(self.combo_base_model, 0, 1)

        grid.addWidget(QLabel("训练轮数 (Epochs):"), 0, 2)
        self.spin_epochs = SafeSpinBox()
        self.spin_epochs.setRange(1, 1000)
        self.spin_epochs.setValue(50)
        grid.addWidget(self.spin_epochs, 0, 3)

        grid.addWidget(QLabel("批次大小 (Batch Size):"), 1, 0)
        self.spin_batch = SafeSpinBox()
        self.spin_batch.setRange(1, 256)
        self.spin_batch.setValue(16)
        grid.addWidget(self.spin_batch, 1, 1)

        grid.addWidget(QLabel("输入分辨率 (Img Size):"), 1, 2)
        self.spin_imgsz = SafeSpinBox()
        self.spin_imgsz.setRange(64, 2048)
        self.spin_imgsz.setSingleStep(32)
        self.spin_imgsz.setValue(640)
        grid.addWidget(self.spin_imgsz, 1, 3)

        grid.addWidget(QLabel("验证集划分比例:"), 2, 0)
        self.spin_val = SafeDoubleSpinBox()
        self.spin_val.setRange(0.05, 0.5)
        self.spin_val.setSingleStep(0.05)
        self.spin_val.setValue(0.20)
        grid.addWidget(self.spin_val, 2, 1)

        grid.addWidget(QLabel("计算硬件设备:"), 2, 2)
        self.combo_device = SafeComboBox()
        if YOLOAnnotator.is_cuda_available():
            self.combo_device.addItems(["CUDA:0 (NVIDIA GPU 加速)", "CPU"])
        else:
            self.combo_device.addItems(["CPU (未检测到 CUDA GPU)"])
        grid.addWidget(self.combo_device, 2, 3)

        grid.addWidget(QLabel("训练模型产出名称:"), 3, 0)
        self.txt_model_name = QLineEdit("labelimg_custom_yolo")
        self.txt_model_name.setPlaceholderText("请输入自定义模型保存文件夹名称...")
        grid.addWidget(self.txt_model_name, 3, 1, 1, 3)




        layout.addLayout(grid)

        # 3. 实时指标与进度
        layout.addWidget(self.create_section_header("3. 训练进度与实时指标"))
        dash_layout = QVBoxLayout()
        dash_layout.setSpacing(10)

        m_box = QHBoxLayout()
        self.lbl_pct = QLabel("总进度: 0.0%")
        self.lbl_epoch = QLabel("Epoch: 0/0")
        self.lbl_box_loss = QLabel("Box Loss: 0.0000")
        self.lbl_cls_loss = QLabel("Cls Loss: 0.0000")
        self.lbl_map50 = QLabel("mAP50: 0.0000")

        for lbl in [self.lbl_pct, self.lbl_epoch, self.lbl_box_loss, self.lbl_cls_loss, self.lbl_map50]:
            lbl.setStyleSheet("background-color: #FFFFFF; border: 1px solid #000000; border-radius: 4px; padding: 6px 12px; font-weight: bold; color: #000000; min-height: 20px;")
            m_box.addWidget(lbl)

        dash_layout.addLayout(m_box)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("等待开始训练...")
        dash_layout.addWidget(self.progress_bar)

        layout.addLayout(dash_layout)

        # 4. 训练日志文本域
        layout.addWidget(self.create_section_header("4. 训练日志输出终端"))
        self.txt_log = QTextEdit()
        self.txt_log.setMinimumHeight(120)
        self.txt_log.setReadOnly(True)
        layout.addWidget(self.txt_log)

        # 5. 操作控制按钮区域
        btn_box = QHBoxLayout()
        btn_box.setSpacing(14)

        self.btn_start = QPushButton(" 开始模型训练")
        self.btn_start.setIcon(self.get_icon("play.svg"))
        self.btn_start.clicked.connect(self.start_train)
        btn_box.addWidget(self.btn_start)

        self.btn_apply = QPushButton(" 应用训练模型至自动标注")
        self.btn_apply.setIcon(self.get_icon("export.svg"))
        self.btn_apply.setObjectName("btn_secondary")
        self.btn_apply.setEnabled(False)
        self.btn_apply.clicked.connect(self.apply_trained_model)
        btn_box.addWidget(self.btn_apply)

        layout.addLayout(btn_box)

        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)

    def refresh_base_models(self):
        self.combo_base_model.blockSignals(True)
        self.combo_base_model.clear()
        
        local_pts = [os.path.join(os.getcwd(), f) for f in os.listdir(os.getcwd()) if f.endswith(".pt")]
        items = []
        if local_pts:
            for p in local_pts:
                if os.path.exists(p):
                    items.append((f"本地: {os.path.basename(p)}", p))

        defaults = ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov11n.pt"]
        for d in defaults:
            full_d = os.path.join(os.getcwd(), d)
            if os.path.exists(full_d) and not any(d in item[0] for item in items):
                items.append((d, full_d))

        for display_name, path_val in items:
            self.combo_base_model.addItem(display_name, path_val)

        self.combo_base_model.addItem("自定义选择本地 .pt 模型...", "custom")
        self.combo_base_model.blockSignals(False)

    def get_initial_dir(self, current_path: str = "", dir_type: str = "img") -> str:
        """根据 dir_type 返回独立记忆的路径，不影响主窗口"""
        if current_path and os.path.exists(current_path):
            return current_path if os.path.isdir(current_path) else os.path.dirname(current_path)
        attr = '_last_train_img_dir' if dir_type == 'img' else '_last_train_xml_dir'
        saved = getattr(self, attr, None)
        if saved and os.path.exists(saved):
            return saved
        return os.getcwd()

    def browse_image_dir(self):
        init_d = self.get_initial_dir(self.txt_img_path.text().strip(), 'img')
        d = QFileDialog.getExistingDirectory(self, "选择包含训练图片的文件夹", init_d)
        if d:
            self.txt_img_path.setText(d)
            self._last_train_img_dir = d
            if not self.txt_xml_path.text():
                self.txt_xml_path.setText(d)

    def browse_xml_dir(self):
        init_d = self.get_initial_dir(self.txt_xml_path.text().strip(), 'xml')
        d = QFileDialog.getExistingDirectory(self, "选择标签文件的文件夹", init_d)
        if d:
            self.txt_xml_path.setText(d)
            self._last_train_xml_dir = d

    def on_base_model_changed(self, idx: int):
        text = self.combo_base_model.currentText()
        if "自定义选择" in text:
            saved = getattr(self, '_last_train_model_dir', None)
            init_d = (saved if saved and os.path.exists(saved) else os.getcwd())
            f_path, _ = QFileDialog.getOpenFileName(self, "选择自定义基础 YOLO 权重", init_d, "YOLO Models (*.pt)")
            if f_path and os.path.exists(f_path):
                self._last_train_model_dir = os.path.dirname(f_path)
                self.combo_base_model.setItemText(idx, f"本地: {os.path.basename(f_path)}")
                self.combo_base_model.setItemData(idx, f_path)
            else:
                self.combo_base_model.setCurrentIndex(0)

    def start_train(self):
        img_dir = self.txt_img_path.text().strip()
        xml_dir = self.txt_xml_path.text().strip() or img_dir

        if not img_dir or not os.path.exists(img_dir):
            QMessageBox.warning(self, "警告", "请先选择有效的训练图片文件夹！")
            return

        raw_base = self.combo_base_model.currentText()
        if "本地:" in raw_base:
            base_model = raw_base.replace("本地:", "").strip()
            data_path = self.combo_base_model.itemData(self.combo_base_model.currentIndex())
            if data_path:
                base_model = data_path
        else:
            base_model = raw_base

        model_name = self.txt_model_name.text().strip() or "labelimg_custom_yolo"
        epochs = self.spin_epochs.value()
        batch_size = self.spin_batch.value()
        imgsz = self.spin_imgsz.value()
        val_ratio = self.spin_val.value()
        device = "0" if "CUDA" in self.combo_device.currentText() else "cpu"

        self.btn_start.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.txt_log.clear()
        self.progress_bar.setValue(0)

        self.trainer_thread = ModelTrainerThread(
            image_dir=img_dir,
            xml_dir=xml_dir,
            base_model=base_model,
            epochs=epochs,
            imgsz=imgsz,
            batch_size=batch_size,
            val_ratio=val_ratio,
            device=device,
            output_name=model_name
        )

        self.trainer_thread.log_signal.connect(self.append_log)
        self.trainer_thread.epoch_progress_signal.connect(self.on_progress)
        self.trainer_thread.detailed_progress_signal.connect(self.on_detailed_progress)
        self.trainer_thread.train_finished_signal.connect(self.on_finished)
        self.trainer_thread.train_error_signal.connect(self.on_error)

        self.trainer_thread.start()

    def append_log(self, text: str):
        self.txt_log.append(text)
        sb = self.txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_detailed_progress(self, epoch: int, total: int, batch: int, total_batches: int, pct: float, b_loss: float, c_loss: float, map50: float, map95: float):
        self.lbl_pct.setText(f"总进度: {pct:.1f}%")
        self.lbl_epoch.setText(f"Epoch: {epoch}/{total}")
        self.lbl_box_loss.setText(f"Box Loss: {b_loss:.4f}")
        self.lbl_cls_loss.setText(f"Cls Loss: {c_loss:.4f}")
        self.lbl_map50.setText(f"mAP50: {map50:.4f}")
        self.progress_bar.setValue(int(pct))
        self.progress_bar.setFormat(f"训练总进度: {pct:.1f}%  (Epoch {epoch}/{total} | Batch {batch}/{total_batches})")

    def on_progress(self, epoch: int, total: int, b_loss: float, c_loss: float, map50: float, map95: float):
        self.lbl_epoch.setText(f"Epoch: {epoch}/{total}")
        self.lbl_box_loss.setText(f"Box Loss: {b_loss:.4f}")
        self.lbl_cls_loss.setText(f"Cls Loss: {c_loss:.4f}")
        self.lbl_map50.setText(f"mAP50: {map50:.4f}")

    def on_finished(self, best_pt_path: str, data_yaml_path: str):
        self.btn_start.setEnabled(True)
        self.btn_apply.setEnabled(True)
        self.last_trained_pt = best_pt_path

        if self.isMinimized() or not self.isVisible():
            self.showNormal()
            self.raise_()
            self.activateWindow()

        QMessageBox.information(self, "训练成功", f"模型训练顺利完成！\n最优化模型保存至:\n{best_pt_path}")

    def on_error(self, err_msg: str):
        self.btn_start.setEnabled(True)
        if self.isMinimized() or not self.isVisible():
            self.showNormal()
            self.raise_()
            self.activateWindow()
        QMessageBox.critical(self, "训练失败", f"模型训练过程报错:\n{err_msg}")

    def save_settings(self):
        """保存当前模型训练控制台的所有参数真实状态"""
        try:
            settings = QSettings("ByteFlow", "LabelImg2")
            settings.setValue("trainer/epochs", int(self.spin_epochs.value()))
            settings.setValue("trainer/batch", int(self.spin_batch.value()))
            settings.setValue("trainer/imgsz", int(self.spin_imgsz.value()))
            settings.setValue("trainer/val_ratio", float(self.spin_val.value()))
            settings.setValue("trainer/base_model_idx", int(self.combo_base_model.currentIndex()))
            settings.setValue("trainer/device_idx", int(self.combo_device.currentIndex()))
            settings.setValue("trainer/model_name", str(self.txt_model_name.text()))
            if self.txt_img_path.text():
                settings.setValue("trainer/img_dir", str(self.txt_img_path.text()))
            if self.txt_xml_path.text():
                settings.setValue("trainer/xml_dir", str(self.txt_xml_path.text()))
        except Exception:
            pass

    def restore_settings(self):
        """还原上次关闭前的真实参数状态"""
        try:
            settings = QSettings("ByteFlow", "LabelImg2")
            self.spin_epochs.setValue(settings.value("trainer/epochs", 50, type=int))
            self.spin_batch.setValue(settings.value("trainer/batch", 16, type=int))
            self.spin_imgsz.setValue(settings.value("trainer/imgsz", 640, type=int))
            self.spin_val.setValue(settings.value("trainer/val_ratio", 0.20, type=float))

            model_idx = settings.value("trainer/base_model_idx", 0, type=int)
            if 0 <= model_idx < self.combo_base_model.count():
                self.combo_base_model.setCurrentIndex(model_idx)

            dev_idx = settings.value("trainer/device_idx", 0, type=int)
            if 0 <= dev_idx < self.combo_device.count():
                self.combo_device.setCurrentIndex(dev_idx)

            saved_name = settings.value("trainer/model_name", "labelimg_custom_yolo", type=str)
            if saved_name:
                self.txt_model_name.setText(saved_name)

            saved_img_dir = settings.value("trainer/img_dir", "", type=str)
            if saved_img_dir and os.path.exists(saved_img_dir) and not self.txt_img_path.text():
                self.txt_img_path.setText(saved_img_dir)

            saved_xml_dir = settings.value("trainer/xml_dir", "", type=str)
            if saved_xml_dir and os.path.exists(saved_xml_dir) and not self.txt_xml_path.text():
                self.txt_xml_path.setText(saved_xml_dir)
        except Exception:
            pass

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def hideEvent(self, event):
        self.save_settings()
        super().hideEvent(event)

    def apply_trained_model(self):
        if self.last_trained_pt and os.path.exists(self.last_trained_pt):
            self.model_trained_signal.emit(self.last_trained_pt)
            self.accept()

