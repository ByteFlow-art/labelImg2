import os
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QGroupBox, QSpinBox, QDoubleSpinBox, QComboBox, QFileDialog,
    QProgressBar, QTextEdit, QMessageBox, QGridLayout
)
from utils.trainer_thread import ModelTrainerThread
from core.yolo_annotator import YOLOAnnotator

class TrainTab(QWidget):
    """
    YOLO 模型自训练 Tab 选项卡界面
    """
    model_trained = pyqtSignal(str) # 当训练结束输出 best.pt 路径时触发

    def __init__(self, parent=None):
        super().__init__(parent)
        self.trainer_thread: Optional[ModelTrainerThread] = None
        self.last_trained_pt: Optional[str] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 1. 已标注数据集路径配置
        group_dataset = QGroupBox("📁 标注数据集路径设置")
        ds_layout = QVBoxLayout()

        ds_box = QHBoxLayout()
        self.txt_dataset_path = QLineEdit()
        self.txt_dataset_path.setPlaceholderText("请选择包含图片与同名 .xml 标注文件的目录 (或已有 data.yaml)...")
        ds_box.addWidget(self.txt_dataset_path)

        btn_browse_ds = QPushButton("📂 浏览文件夹")
        btn_browse_ds.setObjectName("btn_secondary")
        btn_browse_ds.clicked.connect(self.browse_dataset_path)
        ds_box.addWidget(btn_browse_ds)

        ds_layout.addLayout(ds_box)

        lbl_tip = QLabel("💡 提示: 系统会自动扫描该目录下所有的 【图片 + .xml 标注文件】，自动划分为训练集与验证集并完成 YOLO 格式转换。")
        lbl_tip.setStyleSheet("color: #94A3B8; font-size: 12px;")
        ds_layout.addWidget(lbl_tip)

        group_dataset.setLayout(ds_layout)
        layout.addWidget(group_dataset)

        # 2. 模型与超参数设置
        group_params = QGroupBox("⚙️ 模型与训练超参数")
        grid = QGridLayout()

        # 基础模型选择
        grid.addWidget(QLabel("基础预训练权重:"), 0, 0)
        self.combo_base_model = QComboBox()
        self.refresh_base_model_list()
        self.combo_base_model.currentIndexChanged.connect(self.on_base_model_changed)
        grid.addWidget(self.combo_base_model, 0, 1)

        # 训练轮数 (Epochs)
        grid.addWidget(QLabel("训练轮数 (Epochs):"), 0, 2)
        self.spin_epochs = QSpinBox()
        self.spin_epochs.setRange(1, 1000)
        self.spin_epochs.setValue(50)
        grid.addWidget(self.spin_epochs, 0, 3)

        # 批次大小 (Batch Size)
        grid.addWidget(QLabel("批次大小 (Batch Size):"), 1, 0)
        self.spin_batch = QSpinBox()
        self.spin_batch.setRange(1, 256)
        self.spin_batch.setValue(16)
        grid.addWidget(self.spin_batch, 1, 1)

        # 图像分辨率 (Image Size)
        grid.addWidget(QLabel("输入分辨率 (Img Size):"), 1, 2)
        self.spin_imgsz = QSpinBox()
        self.spin_imgsz.setRange(64, 2048)
        self.spin_imgsz.setSingleStep(32)
        self.spin_imgsz.setValue(640)
        grid.addWidget(self.spin_imgsz, 1, 3)

        # 验证集划分比例
        grid.addWidget(QLabel("验证集划分比例:"), 2, 0)
        self.spin_val_ratio = QDoubleSpinBox()
        self.spin_val_ratio.setRange(0.05, 0.5)
        self.spin_val_ratio.setSingleStep(0.05)
        self.spin_val_ratio.setValue(0.20)
        grid.addWidget(self.spin_val_ratio, 2, 1)

        # 计算设备 (Device)
        grid.addWidget(QLabel("训练硬件设备:"), 2, 2)
        self.combo_device = QComboBox()
        if YOLOAnnotator.is_cuda_available():
            self.combo_device.addItems(["CUDA:0 (NVIDIA GPU 加速)", "CPU"])
        else:
            self.combo_device.addItems(["CPU (未检测到 CUDA GPU)"])
        grid.addWidget(self.combo_device, 2, 3)

        # 实验名称
        grid.addWidget(QLabel("训练输出工程名:"), 3, 0)
        self.txt_exp_name = QLineEdit("my_custom_yolo")
        grid.addWidget(self.txt_exp_name, 3, 1)

        group_params.setLayout(grid)
        layout.addWidget(group_params)

        # 3. 实时训练指标仪表盘
        group_dashboard = QGroupBox("实时训练状态指标")
        dash_layout = QVBoxLayout()

        metrics_layout = QHBoxLayout()
        self.lbl_m_pct = QLabel("总进度: 0.0%")
        self.lbl_m_epoch = QLabel("Epoch: 0/0")
        self.lbl_m_box = QLabel("Box Loss: 0.0000")
        self.lbl_m_cls = QLabel("Cls Loss: 0.0000")
        self.lbl_m_map50 = QLabel("mAP50: 0.0000")
        self.lbl_m_map95 = QLabel("mAP50-95: 0.0000")

        for lbl in [self.lbl_m_pct, self.lbl_m_epoch, self.lbl_m_box, self.lbl_m_cls, self.lbl_m_map50, self.lbl_m_map95]:
            lbl.setStyleSheet("background-color: #0F111A; border: 1px solid #2D3348; border-radius: 6px; padding: 8px; font-weight: bold; color: #60A5FA;")
            metrics_layout.addWidget(lbl)

        dash_layout.addLayout(metrics_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("等待启动训练...")
        dash_layout.addWidget(self.progress_bar)

        group_dashboard.setLayout(dash_layout)
        layout.addWidget(group_dashboard)

        # 4. 控制按钮组
        ctrl_box = QHBoxLayout()
        self.btn_start_train = QPushButton(" 开始训练模型")
        self.btn_start_train.setObjectName("btn_primary")
        self.btn_start_train.clicked.connect(self.start_training)
        ctrl_box.addWidget(self.btn_start_train)

        self.btn_apply_to_auto = QPushButton(" 一键应用新模型至自动标注工作站")
        self.btn_apply_to_auto.setObjectName("btn_secondary")
        self.btn_apply_to_auto.setEnabled(False)
        self.btn_apply_to_auto.clicked.connect(self.apply_model_to_annotator)
        ctrl_box.addWidget(self.btn_apply_to_auto)

        layout.addLayout(ctrl_box)

        # 5. 实时训练日志输出终端
        group_log = QGroupBox("📝 训练日志输出终端")
        log_layout = QVBoxLayout()
        self.txt_log_console = QTextEdit()
        self.txt_log_console.setReadOnly(True)
        self.txt_log_console.setStyleSheet("background-color: #0F111A; color: #34D399; font-family: 'Consolas', 'Courier New', monospace;")
        log_layout.addWidget(self.txt_log_console)

        group_log.setLayout(log_layout)
        layout.addWidget(group_log)

    def refresh_base_model_list(self):
        """扫描本地工作目录中的所有 .pt 模型，优先添加到下拉框中"""
        self.combo_base_model.blockSignals(True)
        self.combo_base_model.clear()

        local_pts = []
        curr_dir = os.getcwd()
        for f in os.listdir(curr_dir):
            if f.endswith(".pt"):
                local_pts.append(os.path.join(curr_dir, f))

        items = []
        if local_pts:
            for p in local_pts:
                items.append(f"📁 本地: {os.path.basename(p)}")

        default_models = ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov11n.pt", "yolov11s.pt"]
        for dm in default_models:
            if not any(dm in it for it in items):
                items.append(dm)

        items.append("📂 自定义选择本地 .pt 模型...")
        self.combo_base_model.addItems(items)
        self.combo_base_model.blockSignals(False)

    def browse_dataset_path(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择包含已标注 .xml 图片的数据集文件夹")
        if dir_path:
            self.txt_dataset_path.setText(dir_path)

    def on_base_model_changed(self, idx: int):
        text = self.combo_base_model.currentText()
        if "自定义选择" in text:
            file_path, _ = QFileDialog.getOpenFileName(self, "选择自定义基础 YOLO 权重", "", "YOLO Models (*.pt)")
            if file_path:
                self.combo_base_model.setItemText(idx, f"📁 本地: {os.path.basename(file_path)}")
                self.combo_base_model.setItemData(idx, file_path)
            else:
                self.combo_base_model.setCurrentIndex(0)

    def start_training(self):
        dataset_path = self.txt_dataset_path.text().strip()
        if not dataset_path or not os.path.exists(dataset_path):
            QMessageBox.warning(self, "警告", "请先选择有效的已标注数据集路径！")
            return

        raw_base_model = self.combo_base_model.currentText()
        if "📁 本地:" in raw_base_model:
            base_model = raw_base_model.replace("📁 本地:", "").strip()
            # 如果是本地完整路径数据
            data_path = self.combo_base_model.itemData(self.combo_base_model.currentIndex())
            if data_path:
                base_model = data_path
        else:
            base_model = raw_base_model
        epochs = self.spin_epochs.value()
        batch_size = self.spin_batch.value()
        imgsz = self.spin_imgsz.value()
        val_ratio = self.spin_val_ratio.value()
        exp_name = self.txt_exp_name.text().strip() or "my_custom_yolo"

        device_text = self.combo_device.currentText()
        device = "0" if "CUDA" in device_text else "cpu"

        self.btn_start_train.setEnabled(False)
        self.btn_apply_to_auto.setEnabled(False)
        self.txt_log_console.clear()
        self.progress_bar.setValue(0)

        self.trainer_thread = ModelTrainerThread(
            dataset_path=dataset_path,
            base_model=base_model,
            epochs=epochs,
            imgsz=imgsz,
            batch_size=batch_size,
            val_ratio=val_ratio,
            device=device,
            output_name=exp_name
        )

        self.trainer_thread.log_signal.connect(self.append_log)
        self.trainer_thread.epoch_progress_signal.connect(self.on_epoch_progress)
        self.trainer_thread.detailed_progress_signal.connect(self.on_detailed_progress)
        self.trainer_thread.train_finished_signal.connect(self.on_train_finished)
        self.trainer_thread.train_error_signal.connect(self.on_train_error)

        self.trainer_thread.start()

    def append_log(self, text: str):
        self.txt_log_console.append(text)
        # 自动滚动到底部
        sb = self.txt_log_console.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_detailed_progress(self, epoch: int, total: int, batch: int, total_batches: int, pct: float, b_loss: float, c_loss: float, map50: float, map95: float):
        self.lbl_m_pct.setText(f"总进度: {pct:.1f}%")
        self.lbl_m_epoch.setText(f"Epoch: {epoch}/{total}")
        self.lbl_m_box.setText(f"Box Loss: {b_loss:.4f}")
        self.lbl_m_cls.setText(f"Cls Loss: {c_loss:.4f}")
        self.lbl_m_map50.setText(f"mAP50: {map50:.4f}")
        self.lbl_m_map95.setText(f"mAP50-95: {map95:.4f}")
        self.progress_bar.setValue(int(pct))
        self.progress_bar.setFormat(f"训练总进度: {pct:.1f}% (Epoch {epoch}/{total} | Batch {batch}/{total_batches})")

    def on_epoch_progress(self, epoch: int, total: int, b_loss: float, c_loss: float, map50: float, map95: float):
        self.lbl_m_epoch.setText(f"Epoch: {epoch}/{total}")
        self.lbl_m_box.setText(f"Box Loss: {b_loss:.4f}")
        self.lbl_m_cls.setText(f"Cls Loss: {c_loss:.4f}")
        self.lbl_m_map50.setText(f"mAP50: {map50:.4f}")
        self.lbl_m_map95.setText(f"mAP50-95: {map95:.4f}")

        val = int(epoch / total * 100)
        self.progress_bar.setValue(val)

    def on_train_finished(self, best_pt_path: str, data_yaml_path: str):
        self.btn_start_train.setEnabled(True)
        self.btn_apply_to_auto.setEnabled(True)
        self.last_trained_pt = best_pt_path

        QMessageBox.information(
            self,
            "训练成功",
            f"🎉 模型训练成功完成！\n最优权重已保存至:\n{best_pt_path}\n\n点击【一键应用新模型】可直接载入此模型进行自动化标注！"
        )

    def on_train_error(self, error_msg: str):
        self.btn_start_train.setEnabled(True)
        QMessageBox.critical(self, "训练失败", f"模型训练中断:\n{error_msg}")

    def apply_model_to_annotator(self):
        if self.last_trained_pt and os.path.exists(self.last_trained_pt):
            self.model_trained.emit(self.last_trained_pt)
        else:
            QMessageBox.warning(self, "提示", "未找到训练好的模型权重文件！")
