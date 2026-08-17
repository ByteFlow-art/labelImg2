import os
import time
from typing import Optional, List, Dict, Any
from core.qt_compat import *
from core.yolo_annotator import YOLOAnnotator
from core.xml_handler import XMLHandler
from utils.worker_thread import BatchAnnotationThread
from ui.styles import LIGHT_WORKSTATION_STYLE

def safe_print(msg):
    try:
        print(msg, flush=True)
    except Exception:
        pass

class AutoAnnotateDialog(QDialog):
    """
    YOLO 模型中心 (Model Center & Parameters)
    包含模型权重管理、专业化参数调节 (Conf/IoU/imgsz/device)、类别过滤与标签映射、
    模型推理测试 preview、标注保存文件格式配置。
    注意：根据要求，本窗口内不再嵌入【单图自动批注】与【批量自动批注】按钮。
    """
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff'}

    def __init__(self, main_window_ref, parent=None):
        super().__init__(parent)
        self.main_window = main_window_ref
        self.setWindowTitle("YOLO 模型中心")
        self.setWindowIcon(self.get_icon("labelImg2.ico") if not self.get_icon("labelImg2.ico").isNull() else self.get_icon("labelImg2.png"))
        self.resize(860, 800)
        self.setMinimumSize(780, 680)
        self.setStyleSheet(LIGHT_WORKSTATION_STYLE)

        # 窗口样式与非模态配置
        non_modal_val = getattr(Qt, 'NonModal', None) or getattr(getattr(Qt, 'WindowModality', None), 'NonModal', 0)
        self.setWindowModality(non_modal_val)
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint
        )

        self.annotator = YOLOAnnotator()
        self.batch_thread: Optional[BatchAnnotationThread] = None

        self.cur_img_dir = ""
        self.cur_xml_dir = ""
        self.save_format = "Pascal VOC XML (*.xml)"

        self.init_ui()
        self.sync_paths_from_main_window()

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
        main_layout.setContentsMargins(14, 14, 14, 14)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 1. 模型选择与权重设置
        layout.addWidget(self.create_section_header("1. YOLO 模型选择与权重加载"))
        m_layout = QVBoxLayout()
        m_layout.setSpacing(10)



        m_box = QHBoxLayout()
        lbl_m = QLabel("模型权重:")
        lbl_m.setMinimumWidth(100)
        lbl_m.setStyleSheet("font-size: 13px; font-weight: bold;")
        m_box.addWidget(lbl_m)

        self.combo_models = QComboBox()
        self.combo_models.setStyleSheet("font-size: 13px; padding: 4px;")
        self.refresh_model_selector()
        self.combo_models.currentIndexChanged.connect(self.on_model_selected)
        m_box.addWidget(self.combo_models, stretch=1)

        btn_browse_m = QPushButton(" 选择权重文件")
        btn_browse_m.setIcon(self.get_icon("open.svg"))
        btn_browse_m.setObjectName("btn_secondary")
        btn_browse_m.setStyleSheet("font-size: 13px; padding: 5px 12px;")
        btn_browse_m.clicked.connect(self.browse_custom_model)
        m_box.addWidget(btn_browse_m)

        btn_test_m = QPushButton(" 测试加载")
        btn_test_m.setObjectName("btn_secondary")
        btn_test_m.setStyleSheet("font-size: 13px; padding: 5px 12px;")
        btn_test_m.clicked.connect(self.test_current_model)
        m_box.addWidget(btn_test_m)

        m_layout.addLayout(m_box)

        self.lbl_device = QLabel("计算硬件设备: 检测中...")
        self.lbl_device.setStyleSheet("font-size: 13px; color: #0284C7; font-weight: bold;")
        m_layout.addWidget(self.lbl_device)

        layout.addLayout(m_layout)

        # 2. 专业化推理参数调节 (Conf, IoU, imgsz, device)
        layout.addWidget(self.create_section_header("2. 模型专业化推理参数调节"))
        t_layout = QVBoxLayout()
        t_layout.setSpacing(12)

        # Conf
        conf_box = QHBoxLayout()
        lbl_c = QLabel("Conf (置信度阈值):")
        lbl_c.setMinimumWidth(130)
        lbl_c.setStyleSheet("font-size: 13px; font-weight: bold;")
        conf_box.addWidget(lbl_c)

        self.lbl_conf = QLabel("0.25")
        self.lbl_conf.setMinimumWidth(45)
        self.lbl_conf.setStyleSheet("font-weight: bold; font-size: 13px; color: #2563EB;")
        
        self.slider_conf = QSlider(Qt.Horizontal)
        self.slider_conf.setRange(1, 100)
        self.slider_conf.setValue(25)
        self.slider_conf.valueChanged.connect(lambda v: self.lbl_conf.setText(f"{v/100.0:.2f}"))
        conf_box.addWidget(self.slider_conf)
        conf_box.addWidget(self.lbl_conf)
        t_layout.addLayout(conf_box)

        # IoU
        iou_box = QHBoxLayout()
        lbl_i = QLabel("IoU (NMS重叠阈值):")
        lbl_i.setMinimumWidth(130)
        lbl_i.setStyleSheet("font-size: 13px; font-weight: bold;")
        iou_box.addWidget(lbl_i)

        self.lbl_iou = QLabel("0.45")
        self.lbl_iou.setMinimumWidth(45)
        self.lbl_iou.setStyleSheet("font-weight: bold; font-size: 13px; color: #2563EB;")

        self.slider_iou = QSlider(Qt.Horizontal)
        self.slider_iou.setRange(1, 100)
        self.slider_iou.setValue(45)
        self.slider_iou.valueChanged.connect(lambda v: self.lbl_iou.setText(f"{v/100.0:.2f}"))
        iou_box.addWidget(self.slider_iou)
        iou_box.addWidget(self.lbl_iou)
        t_layout.addLayout(iou_box)

        # imgsz & device
        param_grid = QGridLayout()
        param_grid.setHorizontalSpacing(20)
        param_grid.setVerticalSpacing(10)

        lbl_sz = QLabel("推理分辨率 (imgsz):")
        lbl_sz.setStyleSheet("font-size: 13px; font-weight: bold;")
        param_grid.addWidget(lbl_sz, 0, 0)

        self.combo_imgsz = QComboBox()
        self.combo_imgsz.addItems(["640 x 640 (推荐)", "320 x 320 (快速)", "1280 x 1280 (高清)"])
        self.combo_imgsz.setStyleSheet("font-size: 13px; padding: 3px;")
        param_grid.addWidget(self.combo_imgsz, 0, 1)

        lbl_dev = QLabel("推理设备 (Device):")
        lbl_dev.setStyleSheet("font-size: 13px; font-weight: bold;")
        param_grid.addWidget(lbl_dev, 0, 2)

        self.combo_device = QComboBox()
        self.combo_device.addItems(["Auto (CUDA / GPU)", "CPU Mode"])
        self.combo_device.setStyleSheet("font-size: 13px; padding: 3px;")
        param_grid.addWidget(self.combo_device, 0, 3)

        t_layout.addLayout(param_grid)
        layout.addLayout(t_layout)

        # 3. 类别检测控制与标签映射
        layout.addWidget(self.create_section_header("3. 类别检测控制与标签映射"))
        cls_layout = QVBoxLayout()
        cls_layout.setSpacing(8)

        quick_act_box = QHBoxLayout()
        btn_sel_all = QPushButton("全选")
        btn_sel_all.setObjectName("btn_secondary")
        btn_sel_all.setFixedHeight(28)
        btn_sel_all.setStyleSheet("font-size: 12px;")
        btn_sel_all.clicked.connect(self.select_all_classes)
        quick_act_box.addWidget(btn_sel_all)

        btn_desel_all = QPushButton("清空")
        btn_desel_all.setObjectName("btn_secondary")
        btn_desel_all.setFixedHeight(28)
        btn_desel_all.setStyleSheet("font-size: 12px;")
        btn_desel_all.clicked.connect(self.deselect_all_classes)
        quick_act_box.addWidget(btn_desel_all)

        btn_invert_sel = QPushButton("反选")
        btn_invert_sel.setObjectName("btn_secondary")
        btn_invert_sel.setFixedHeight(28)
        btn_invert_sel.setStyleSheet("font-size: 12px;")
        btn_invert_sel.clicked.connect(self.invert_class_selection)
        quick_act_box.addWidget(btn_invert_sel)

        quick_act_box.addStretch()
        cls_layout.addLayout(quick_act_box)

        self.table_cls = QTableWidget(0, 3)
        self.table_cls.setMinimumHeight(180)
        self.table_cls.setMaximumHeight(240)
        self.table_cls.verticalHeader().setDefaultSectionSize(30)
        self.table_cls.verticalHeader().setVisible(False)
        self.table_cls.setHorizontalHeaderLabels(["启用检测", "模型原始类别", "导出标签映射 (双击修改)"])
        self.table_cls.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_cls.setStyleSheet("font-size: 13px;")
        cls_layout.addWidget(self.table_cls)

        layout.addLayout(cls_layout)



        # 4. 自动标注应用模式设置 (覆盖原标签 vs 追加合并)
        layout.addWidget(self.create_section_header("4. 自动标注应用模式设置"))
        mode_box = QHBoxLayout()
        lbl_mode = QLabel("标注应用模式:")
        lbl_mode.setMinimumWidth(130)
        lbl_mode.setStyleSheet("font-size: 13px; font-weight: bold;")
        mode_box.addWidget(lbl_mode)

        self.rb_mode_overwrite = QRadioButton("完全覆盖模式")
        self.rb_mode_append = QRadioButton("追加合并模式")
        self.rb_mode_overwrite.setChecked(True)
        self.rb_mode_overwrite.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        self.rb_mode_append.setStyleSheet("font-size: 13px; font-weight: bold; color: #2563EB;")

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.rb_mode_overwrite, 1)
        self.mode_group.addButton(self.rb_mode_append, 2)

        mode_box.addWidget(self.rb_mode_overwrite)
        mode_box.addWidget(self.rb_mode_append)
        mode_box.addStretch()
        layout.addLayout(mode_box)


        # 5. 自动批注保存文件格式类型选项
        layout.addWidget(self.create_section_header("5. 标注保存文件格式类型设置"))
        fmt_box = QHBoxLayout()
        lbl_fmt = QLabel("保存格式类型:")
        lbl_fmt.setMinimumWidth(130)
        lbl_fmt.setStyleSheet("font-size: 13px; font-weight: bold;")
        fmt_box.addWidget(lbl_fmt)

        self.combo_save_format = QComboBox()
        self.combo_save_format.addItems([
            "Pascal VOC XML (*.xml)",
            "YOLO TXT (*.txt)",
            "Create ML JSON (*.json)",
            "COCO JSON (*.json)"
        ])
        self.combo_save_format.setStyleSheet("font-size: 13px; padding: 4px;")
        self.combo_save_format.currentIndexChanged.connect(self.on_save_format_changed)
        fmt_box.addWidget(self.combo_save_format, stretch=1)
        layout.addLayout(fmt_box)


        # 6. 进度条与控制台状态
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("height: 18px;")
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("状态: YOLO 模型中心已就绪")
        self.lbl_status.setStyleSheet("font-size: 13px; color: #0F172A; font-weight: bold; background: #F1F5F9; padding: 6px; border-radius: 4px;")
        layout.addWidget(self.lbl_status)

        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)

        # 默认加载初始模型
        self.on_model_selected(0)

    def sync_paths_from_main_window(self):
        """同步 LabelImg 主窗口中当前打开的图片路径、保存路径与保存格式"""
        if self.main_window:
            cur_img_dir = getattr(self.main_window, 'dirpath', "") or getattr(self.main_window, 'lastOpenDir', "") or ""
            cur_xml_dir = getattr(self.main_window, 'defaultSaveDir', "") or cur_img_dir

            self.cur_img_dir = cur_img_dir
            self.cur_xml_dir = cur_xml_dir

            if hasattr(self.main_window, 'save_format') and self.main_window.save_format:
                fmt = self.main_window.save_format
                idx = self.combo_save_format.findText(fmt)
                if idx >= 0:
                    self.combo_save_format.blockSignals(True)
                    self.combo_save_format.setCurrentIndex(idx)
                    self.combo_save_format.blockSignals(False)

    def on_save_format_changed(self, index: int):
        selected_fmt = self.combo_save_format.currentText()
        self.save_format = selected_fmt
        if self.main_window and hasattr(self.main_window, 'set_save_format'):
            self.main_window.set_save_format(selected_fmt)
        msg = f"[Model Center Terminal] 标注保存文件格式类型已切换为: {selected_fmt}"
        self.lbl_status.setText(msg)
        safe_print(msg)

    def run_single_image_test(self):
        """运行单图模型推理测试，展示耗时、目标数与类别击中"""
        if not self.annotator.model:
            QMessageBox.warning(self, "提示", "请先加载 YOLO 模型权重！")
            return

        self.sync_paths_from_main_window()
        img_path = getattr(self.main_window, 'filePath', None)
        if not img_path or not os.path.exists(img_path):
            imgs = self.get_image_paths_to_process()
            if imgs:
                img_path = imgs[0]

        if not img_path or not os.path.exists(img_path):
            QMessageBox.warning(self, "警告", "未找到可用于测试的图片！请先在主界面打开图片或目录。")
            return

        conf = self.slider_conf.value() / 100.0
        iou = self.slider_iou.value() / 100.0

        t0 = time.time()
        try:
            boxes = self.annotator.predict_image(
                image_path=img_path,
                conf_threshold=conf,
                iou_threshold=iou
            )
            elapsed_ms = (time.time() - t0) * 1000.0
            
            # 统计各类别目标数
            class_counts = {}
            for b in boxes:
                cls_n = b.get('label', 'object')
                class_counts[cls_n] = class_counts.get(cls_n, 0) + 1

            cls_summary = ", ".join([f"{k}:{v}" for k, v in class_counts.items()]) if class_counts else "无击中目标"
            msg = f"⚡ 单图推理测试成功: 耗时 {elapsed_ms:.1f} ms | 检测到 {len(boxes)} 个目标 ({cls_summary})"
            self.lbl_status.setText(msg)
            safe_print(f"[YOLO Model Test Terminal] {msg} (图片: {os.path.basename(img_path)})")
            QMessageBox.information(self, "模型单图测试结果", f"图片: {os.path.basename(img_path)}\n推理耗时: {elapsed_ms:.1f} ms\n目标数量: {len(boxes)} 个\n类别明细: {cls_summary}")
        except Exception as e:
            QMessageBox.critical(self, "测试失败", str(e))

    def run_speed_benchmark(self):
        """批次推理速测评估"""
        if not self.annotator.model:
            QMessageBox.warning(self, "提示", "请先加载 YOLO 模型权重！")
            return

        imgs = self.get_image_paths_to_process()
        if not imgs:
            QMessageBox.warning(self, "警告", "未找到测试图片！")
            return

        test_count = min(10, len(imgs))
        conf = self.slider_conf.value() / 100.0
        iou = self.slider_iou.value() / 100.0

        t0 = time.time()
        total_boxes = 0
        for i in range(test_count):
            try:
                b = self.annotator.predict_image(imgs[i], conf_threshold=conf, iou_threshold=iou)
                total_boxes += len(b)
            except Exception:
                pass
        total_sec = time.time() - t0
        avg_ms = (total_sec / test_count) * 1000.0
        fps = test_count / total_sec if total_sec > 0 else 0

        msg = f"🚀 测速完成: 评估 {test_count} 张图 | 平均耗时 {avg_ms:.1f} ms/张 ({fps:.1f} FPS) | 共击中 {total_boxes} 个目标"
        self.lbl_status.setText(msg)
        safe_print(f"[YOLO Benchmark Terminal] {msg}")
        QMessageBox.information(self, "模型推理测速报告", msg)

    def test_current_model(self):
        idx = self.combo_models.currentIndex()
        path_val = self.combo_models.itemData(idx)
        if not path_val or not os.path.exists(path_val):
            self.lbl_status.setText("提示: 当前未选择有效的模型权重文件。")
            QMessageBox.warning(self, "提示", "当前未选择有效的模型权重文件。")
            return
        try:
            class_dict = self.annotator.load_model(path_val)
            model_name = os.path.basename(path_val)
            msg = f"✅ 模型 {model_name} 加载测试成功！包含 {len(class_dict)} 个类别"
            self.lbl_status.setText(msg)
            safe_print(f"[YOLO Model Center Terminal] {msg}")
            # 展示类别列表，每行一个
            class_lines = [f"  [{k}]  {v}" for k, v in list(class_dict.items())[:30]]
            if len(class_dict) > 30:
                class_lines.append(f"  ... (共 {len(class_dict)} 个类别)")
            class_list = "\n".join(class_lines)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("模型加载测试成功")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setText(f"模型文件: <b>{model_name}</b><br>类别数量: <b>{len(class_dict)} 个</b>")
            msg_box.setDetailedText(f"类别列表:\n{class_list}")
            msg_box.setMinimumWidth(520)
            msg_box.exec_()
        except Exception as e:
            safe_print(f"[YOLO Model Center Error] {str(e)}")
            QMessageBox.critical(self, "模型加载失败", str(e))

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_model_selector()
        if self.annotator.model_path and os.path.exists(self.annotator.model_path):
            for i in range(self.combo_models.count()):
                if self.combo_models.itemData(i) == self.annotator.model_path:
                    self.combo_models.blockSignals(True)
                    self.combo_models.setCurrentIndex(i)
                    self.combo_models.blockSignals(False)
                    break
        self.sync_paths_from_main_window()

    def refresh_model_selector(self):
        """动态刷新模型下拉框列表 (实时扫描当前目录、models、weights 及 runs/train)"""
        current_selected_path = self.annotator.model_path or (self.combo_models.currentData() if hasattr(self, 'combo_models') else None)
        self.combo_models.blockSignals(True)
        self.combo_models.clear()

        model_items = []
        seen_paths = set()

        for folder_name in ("models", "weights", os.path.join("runs", "train")):
            search_d = os.path.join(os.getcwd(), folder_name)
            if os.path.exists(search_d):
                for root_dir, _, files in os.walk(search_d):
                    for f in files:
                        if f.endswith(".pt") or f.endswith(".onnx") or f.endswith(".engine"):
                            full_p = os.path.abspath(os.path.join(root_dir, f))
                            if full_p not in seen_paths and os.path.exists(full_p):
                                seen_paths.add(full_p)
                                rel_p = os.path.relpath(full_p, os.getcwd())
                                model_items.append((f"模型库: {rel_p}", full_p))

        for f in os.listdir(os.getcwd()):
            if f.endswith(".pt") or f.endswith(".onnx") or f.endswith(".engine"):
                full_p = os.path.abspath(os.path.join(os.getcwd(), f))
                if full_p not in seen_paths and os.path.exists(full_p):
                    seen_paths.add(full_p)
                    model_items.append((f"当前目录: {f}", full_p))

        # 如果已有加载的模型不在扫描列表中，单独置顶加入
        if current_selected_path and os.path.exists(current_selected_path):
            abs_curr = os.path.abspath(current_selected_path)
            if abs_curr not in seen_paths:
                seen_paths.add(abs_curr)
                model_items.insert(0, (f"当前模型: {os.path.basename(current_selected_path)}", abs_curr))

        for display_name, path_val in model_items:
            self.combo_models.addItem(display_name, path_val)

        self.combo_models.addItem("自定义选择本地 .pt / .onnx 权重文件...", "custom")

        # 恢复选中当前模型
        if current_selected_path and os.path.exists(current_selected_path):
            abs_curr = os.path.abspath(current_selected_path)
            for i in range(self.combo_models.count()):
                if self.combo_models.itemData(i) == abs_curr or self.combo_models.itemData(i) == current_selected_path:
                    self.combo_models.setCurrentIndex(i)
                    break
        self.combo_models.blockSignals(False)

    def get_initial_dir(self, current_path: str = "", dir_type: str = "model") -> str:
        """根据 dir_type 返回独立记忆的路径，不共享主窗口的 lastOpenDir"""
        if current_path and os.path.exists(current_path):
            return current_path if os.path.isdir(current_path) else os.path.dirname(current_path)
        # 模型文件使用独立记忆
        if dir_type == "model":
            saved = getattr(self, '_last_model_dir', None)
            if saved and os.path.exists(saved):
                return saved
        return os.getcwd()

    def update_last_dir(self, selected_path: str):
        if not selected_path:
            return
        target_d = selected_path if os.path.isdir(selected_path) else os.path.dirname(selected_path)
        if self.main_window and hasattr(self.main_window, 'lastOpenDir'):
            self.main_window.lastOpenDir = target_d
            if hasattr(self.main_window, 'settings'):
                self.main_window.settings['lastOpenDir'] = target_d
                self.main_window.settings.save()

    def browse_custom_model(self):
        init_d = self.get_initial_dir(dir_type="model")
        f_path, _ = QFileDialog.getOpenFileName(self, "选择自定义 YOLO 权重文件", init_d, "YOLO Models (*.pt *.onnx *.engine)")
        if f_path and os.path.exists(f_path):
            # 独立记忆模型目录，不影响主窗口的文件路径
            self._last_model_dir = os.path.dirname(f_path)
            self.load_model(f_path)
            self.refresh_model_selector()

    def on_model_selected(self, idx: int):
        path_val = self.combo_models.itemData(idx)
        if path_val == "custom":
            self.browse_custom_model()
        elif path_val:
            if not os.path.exists(path_val):
                self.combo_models.removeItem(idx)
                self.lbl_status.setText("提示: 所选模型文件在磁盘上不存在。")
                return
            self.load_model(path_val)

    def load_model(self, model_path: str):
        if not os.path.exists(model_path):
            QMessageBox.warning(self, "警告", f"模型文件不存在: {model_path}")
            self.refresh_model_selector()
            return

        try:
            class_dict = self.annotator.load_model(model_path)
            self.lbl_device.setText(f"计算硬件设备: {self.annotator.device.upper()}")

            self.populate_class_table(class_dict)
            msg = f"已加载模型: {os.path.basename(model_path)} (包含类别数: {len(class_dict)})"
            self.lbl_status.setText(msg)
            safe_print(f"[YOLO Model Center Terminal] {msg}")

            if self.main_window and hasattr(self.main_window, 'settings'):
                self.main_window.settings['last_model_path'] = model_path
                self.main_window.settings.save()
            
            for i in range(self.combo_models.count()):
                if self.combo_models.itemData(i) == model_path:
                    self.combo_models.blockSignals(True)
                    self.combo_models.setCurrentIndex(i)
                    self.combo_models.blockSignals(False)
                    break
        except Exception as e:
            QMessageBox.critical(self, "模型载入失败", str(e))

    def populate_class_table(self, class_dict: Dict[int, str]):
        self.table_cls.setRowCount(len(class_dict))
        for row, (cls_id, cls_name) in enumerate(class_dict.items()):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled if hasattr(Qt, 'ItemFlag') else Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.CheckState.Checked if hasattr(Qt, 'CheckState') else Qt.Checked)
            self.table_cls.setItem(row, 0, chk_item)

            orig_item = QTableWidgetItem(cls_name)
            orig_item.setFlags(Qt.ItemFlag.ItemIsEnabled if hasattr(Qt, 'ItemFlag') else Qt.ItemIsEnabled)
            self.table_cls.setItem(row, 1, orig_item)

            map_item = QTableWidgetItem(cls_name)
            map_item.setFlags(Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled if hasattr(Qt, 'ItemFlag') else Qt.ItemIsEditable | Qt.ItemIsEnabled)
            self.table_cls.setItem(row, 2, map_item)

    def select_all_classes(self):
        for row in range(self.table_cls.rowCount()):
            item = self.table_cls.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked if hasattr(Qt, 'CheckState') else Qt.Checked)

    def deselect_all_classes(self):
        for row in range(self.table_cls.rowCount()):
            item = self.table_cls.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked if hasattr(Qt, 'CheckState') else Qt.Unchecked)

    def invert_class_selection(self):
        for row in range(self.table_cls.rowCount()):
            item = self.table_cls.item(row, 0)
            if item:
                cur_state = item.checkState()
                checked_val = (Qt.CheckState.Checked if hasattr(Qt, 'CheckState') else Qt.Checked)
                unchecked_val = (Qt.CheckState.Unchecked if hasattr(Qt, 'CheckState') else Qt.Unchecked)
                item.setCheckState(unchecked_val if cur_state == checked_val else checked_val)

    def get_class_mapping(self) -> Dict[str, str]:
        mapping = {}
        for row in range(self.table_cls.rowCount()):
            chk_item = self.table_cls.item(row, 0)
            is_checked = (chk_item.checkState() == (Qt.CheckState.Checked if hasattr(Qt, 'CheckState') else Qt.Checked))
            if is_checked:
                orig_name = self.table_cls.item(row, 1).text()
                map_name = self.table_cls.item(row, 2).text().strip()
                mapping[orig_name] = map_name
        return mapping

    def get_image_paths_to_process(self) -> List[str]:
        self.sync_paths_from_main_window()
        img_dir = self.cur_img_dir
        if not img_dir or not os.path.exists(img_dir):
            return []

        scanned_images = []
        for file in os.listdir(img_dir):
            ext = os.path.splitext(file)[1].lower()
            if ext in self.IMAGE_EXTENSIONS:
                scanned_images.append(os.path.join(img_dir, file))

        scanned_images.sort()
        return scanned_images

    # 供主界面【单图自动批注】快捷动作调用的底层接口
    def auto_annotate_single_image(self):
        if not self.annotator.model:
            QMessageBox.warning(self, "提示", "请先在 YOLO 模型中心加载模型权重！")
            return

        self.sync_paths_from_main_window()

        img_path = getattr(self.main_window, 'filePath', None)
        if not img_path or not os.path.exists(img_path):
            imgs = self.get_image_paths_to_process()
            if imgs:
                img_path = imgs[0]

        if not img_path or not os.path.exists(img_path):
            QMessageBox.warning(self, "警告", "未找到可标注的图片！请先在主界面打开图片或目录。")
            return

        save_dir = self.cur_xml_dir or os.path.dirname(img_path)
        if not save_dir or not os.path.exists(os.path.dirname(save_dir) if os.path.isfile(save_dir) else save_dir):
            QMessageBox.warning(self, "警告", "保存目录无效！请在主界面指定保存路径。")
            return

        os.makedirs(save_dir, exist_ok=True)

        stem = os.path.splitext(os.path.basename(img_path))[0]
        xml_path = os.path.join(save_dir, f"{stem}.xml")

        is_append = getattr(self, 'rb_mode_append', None) and self.rb_mode_append.isChecked()
        overwrite_mode = not is_append

        if overwrite_mode and os.path.exists(xml_path):
            reply = QMessageBox.question(
                self,
                "覆盖标注确认",
                f"检测到标注文件 [{stem}.xml] 已存在！\n当前为【完全覆盖替换模式】，是否确定覆盖已有标注内容？\n\n(提示：若想保留原图已有标注，请在模型中心切换为【追加合并模式】)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No if hasattr(QMessageBox, 'StandardButton') else QMessageBox.Yes | QMessageBox.No,
                QMessageBox.StandardButton.No if hasattr(QMessageBox, 'StandardButton') else QMessageBox.No
            )
            yes_val = QMessageBox.StandardButton.Yes if hasattr(QMessageBox, 'StandardButton') else QMessageBox.Yes
            if reply != yes_val:
                self.lbl_status.setText("已取消自动标注 (保留原有标注)")
                return

        conf = self.slider_conf.value() / 100.0
        iou = self.slider_iou.value() / 100.0
        mapping = self.get_class_mapping()

        try:
            boxes = self.annotator.predict_image(
                image_path=img_path,
                conf_threshold=conf,
                iou_threshold=iou
            )

            XMLHandler.save_pascal_voc_xml(
                image_path=img_path,
                objects=boxes,
                output_xml_path=xml_path,
                class_mapping=mapping,
                overwrite=overwrite_mode
            )

            if hasattr(self.main_window, 'defaultSaveDir'):
                self.main_window.defaultSaveDir = save_dir
            if hasattr(self.main_window, 'loadFile'):
                self.main_window.loadFile(img_path)

            mode_str = "追加模式 (保留原标注)" if is_append else "覆盖模式"
            status_msg = f"单图自动批注完成 [{mode_str}]: 检测到 {len(boxes)} 个目标 -> {os.path.basename(xml_path)}"
            self.lbl_status.setText(status_msg)
            safe_print(f"[Auto-Annotate Terminal] {status_msg}")

        except Exception as e:
            QMessageBox.critical(self, "批注出错", str(e))

    # 供主界面【批量自动批注】快捷动作调用的底层接口
    def start_batch_annotate(self):
        if not self.annotator.model:
            QMessageBox.warning(self, "提示", "请先在 YOLO 模型中心加载模型权重！")
            return

        self.sync_paths_from_main_window()
        image_paths = self.get_image_paths_to_process()
        if not image_paths:
            QMessageBox.warning(self, "警告", f"未找到有效图片！请先在主界面打开要标注的图片文件夹。\n(当前检测目录: {self.cur_img_dir})")
            return

        save_dir = self.cur_xml_dir or os.path.dirname(image_paths[0])
        os.makedirs(save_dir, exist_ok=True)

        is_append = getattr(self, 'rb_mode_append', None) and self.rb_mode_append.isChecked()
        overwrite_mode = not is_append

        if overwrite_mode:
            existing_count = sum(1 for p in image_paths if os.path.exists(os.path.join(save_dir, f"{os.path.splitext(os.path.basename(p))[0]}.xml")))
            if existing_count > 0:
                reply = QMessageBox.question(
                    self,
                    "批量覆盖确认",
                    f"在保存目录中检测到 {existing_count} 个已存在的标注文件！\n当前为【完全覆盖替换模式】，是否确定覆盖现有标注？\n\n(提示：若想保留已有标注并在其上新增目标，请切换为【追加合并模式】)",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No if hasattr(QMessageBox, 'StandardButton') else QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.StandardButton.No if hasattr(QMessageBox, 'StandardButton') else QMessageBox.No
                )
                yes_val = QMessageBox.StandardButton.Yes if hasattr(QMessageBox, 'StandardButton') else QMessageBox.Yes
                if reply != yes_val:
                    self.lbl_status.setText("已取消批量自动批注")
                    return

        if hasattr(self.main_window, 'defaultSaveDir'):
            self.main_window.defaultSaveDir = save_dir

        conf = self.slider_conf.value() / 100.0
        iou = self.slider_iou.value() / 100.0
        mapping = self.get_class_mapping()

        self.batch_thread = BatchAnnotationThread(
            annotator=self.annotator,
            image_paths=image_paths,
            conf_threshold=conf,
            iou_threshold=iou,
            class_mapping=mapping,
            save_xml=True,
            save_yolo_txt=False,
            overwrite=overwrite_mode,
            custom_output_dir=save_dir
        )


        self.batch_thread.progress_signal.connect(self.on_batch_progress)
        self.batch_thread.finished_signal.connect(self.on_batch_finished)
        self.batch_thread.error_signal.connect(self.on_batch_error)

        print(f"[Auto-Annotate Terminal] 开始批量自动批注文件夹 (共 {len(image_paths)} 张图片)...", flush=True)
        self.batch_thread.start()

    def on_batch_progress(self, current: int, total: int, filename: str, status_msg: str):
        val = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(val)
        msg = f"[{current}/{total}] {filename} - {status_msg}"
        self.lbl_status.setText(msg)
        print(f"[Auto-Annotate Terminal] {msg}", flush=True)

    def on_batch_finished(self, processed: int, total_boxes: int):
        if hasattr(self.main_window, 'filePath') and self.main_window.filePath:
            self.main_window.loadFile(self.main_window.filePath)

        save_dir = self.cur_xml_dir
        finish_msg = f"批量自动批注完成！成功处理 {processed} 张图片，生成 {total_boxes} 个目标标注 (保存于: {save_dir})"
        self.lbl_status.setText(finish_msg)
        print(f"[Auto-Annotate Terminal] {finish_msg}", flush=True)

    def on_batch_error(self, err_msg: str):
        print(f"[Auto-Annotate Terminal Error] 批量批注中断: {err_msg}", flush=True)
        QMessageBox.critical(self, "批量批注中断", err_msg)
