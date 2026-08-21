import os
import time
from typing import Optional, List, Dict, Any
from core.qt_compat import *
from core.safe_widgets import SafeComboBox, SafeSlider, SafeDoubleSpinBox
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
        ico = self.get_icon("app.ico")
        if ico.isNull():
            ico = self.get_icon("app.png")
        if ico.isNull():
            ico = self.get_icon("labelImg2.ico")
        self.setWindowIcon(ico)

        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            w = min(920, int(avail.width() * 0.85))
            h = min(860, int(avail.height() * 0.92))
            self.resize(w, h)
        else:
            self.resize(920, 860)

        self.setMinimumSize(800, 680)
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
        self.restore_settings()
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

        self.combo_models = SafeComboBox()
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

        self.spin_conf = SafeDoubleSpinBox()
        self.spin_conf.setRange(0.01, 1.00)
        self.spin_conf.setSingleStep(0.01)
        self.spin_conf.setValue(0.25)
        self.spin_conf.setDecimals(2)
        self.spin_conf.setFixedWidth(70)
        self.spin_conf.setStyleSheet("font-size: 13px; font-weight: bold; color: #2563EB;")

        self.slider_conf = SafeSlider(Qt.Horizontal)
        self.slider_conf.setRange(1, 100)
        self.slider_conf.setValue(25)

        self.slider_conf.valueChanged.connect(lambda v: self.spin_conf.setValue(v / 100.0))
        self.spin_conf.valueChanged.connect(lambda v: self.slider_conf.setValue(int(round(v * 100))))
        conf_box.addWidget(self.slider_conf)
        conf_box.addWidget(self.spin_conf)
        t_layout.addLayout(conf_box)

        # IoU
        iou_box = QHBoxLayout()
        lbl_i = QLabel("IoU (NMS重叠阈值):")
        lbl_i.setMinimumWidth(130)
        lbl_i.setStyleSheet("font-size: 13px; font-weight: bold;")
        iou_box.addWidget(lbl_i)

        self.spin_iou = SafeDoubleSpinBox()
        self.spin_iou.setRange(0.01, 1.00)
        self.spin_iou.setSingleStep(0.01)
        self.spin_iou.setValue(0.45)
        self.spin_iou.setDecimals(2)
        self.spin_iou.setFixedWidth(70)
        self.spin_iou.setStyleSheet("font-size: 13px; font-weight: bold; color: #2563EB;")

        self.slider_iou = SafeSlider(Qt.Horizontal)
        self.slider_iou.setRange(1, 100)
        self.slider_iou.setValue(45)

        self.slider_iou.valueChanged.connect(lambda v: self.spin_iou.setValue(v / 100.0))
        self.spin_iou.valueChanged.connect(lambda v: self.slider_iou.setValue(int(round(v * 100))))
        iou_box.addWidget(self.slider_iou)
        iou_box.addWidget(self.spin_iou)
        t_layout.addLayout(iou_box)

        # imgsz & device
        param_grid = QGridLayout()
        param_grid.setHorizontalSpacing(20)
        param_grid.setVerticalSpacing(10)

        lbl_sz = QLabel("推理分辨率 (imgsz):")
        lbl_sz.setStyleSheet("font-size: 13px; font-weight: bold;")
        param_grid.addWidget(lbl_sz, 0, 0)

        self.combo_imgsz = SafeComboBox()
        self.combo_imgsz.addItems(["640 x 640 (推荐)", "320 x 320 (快速)", "1280 x 1280 (高清)"])
        self.combo_imgsz.setStyleSheet("font-size: 13px; padding: 3px;")
        param_grid.addWidget(self.combo_imgsz, 0, 1)

        lbl_dev = QLabel("推理设备 (Device):")
        lbl_dev.setStyleSheet("font-size: 13px; font-weight: bold;")
        param_grid.addWidget(lbl_dev, 0, 2)

        self.combo_device = SafeComboBox()
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

        rb_style = """
        QRadioButton {
            font-size: 13px;
            font-weight: bold;
            color: #1E293B;
        }
        QRadioButton:checked {
            color: #2563EB;
        }
        """
        self.rb_mode_overwrite = QRadioButton("完全覆盖模式")
        self.rb_mode_append = QRadioButton("追加合并模式")
        self.rb_mode_overwrite.setStyleSheet(rb_style)
        self.rb_mode_append.setStyleSheet(rb_style)
        self.rb_mode_overwrite.setChecked(True)

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

        self.combo_save_format = SafeComboBox()
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

        # 6. 进度条 (仅批量任务时显示)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)

    def sync_paths_from_main_window(self):
        """同步 LabelImg 主窗口中当前打开的图片路径、保存路径与保存格式（相互独立互不干扰）"""
        if self.main_window:
            cur_img_dir = getattr(self.main_window, 'dirname', "") or (os.path.dirname(self.main_window.filePath) if getattr(self.main_window, 'filePath', None) else "") or (self.main_window.settings.get('last_image_dir', "") if hasattr(self.main_window, 'settings') else "")
            cur_xml_dir = getattr(self.main_window, 'defaultSaveDir', "") or (self.main_window.settings.get('last_save_dir', "") if hasattr(self.main_window, 'settings') else "") or cur_img_dir

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
        try:
            selected_fmt = self.combo_save_format.currentText()
            self.save_format = selected_fmt
            if self.main_window and hasattr(self.main_window, 'set_save_format'):
                self.main_window.set_save_format(selected_fmt)
            msg = f"[Model Center Terminal] 标注保存文件格式类型已切换为: {selected_fmt}"
            safe_print(msg)
        except Exception as e:
            safe_print(f"[Model Center Error] 切换保存格式异常: {e}")


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
            self.set_status(msg)
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
        self.set_status(msg)
        QMessageBox.information(self, "模型推理测速报告", msg)

    def test_current_model(self):
        idx = self.combo_models.currentIndex()
        path_val = self.combo_models.itemData(idx)
        if not path_val or not os.path.exists(path_val):
            self.set_status("提示: 当前未选择有效的模型权重文件。")
            QMessageBox.warning(self, "提示", "当前未选择有效的模型权重文件。")
            return
        try:
            class_dict = self.annotator.load_model(path_val)
            model_name = os.path.basename(path_val)
            msg = f"✅ 模型 {model_name} 加载测试成功！包含 {len(class_dict)} 个类别"
            self.set_status(msg)

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

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        search_dirs = [
            base_dir,
            os.path.join(base_dir, "models"),
            os.path.join(base_dir, "weights"),
            os.path.join(base_dir, "runs", "train"),
            os.getcwd(),
            os.path.join(os.getcwd(), "models"),
            os.path.join(os.getcwd(), "weights"),
            os.path.join(os.getcwd(), "runs", "train")
        ]

        for s_dir in search_dirs:
            if s_dir and os.path.exists(s_dir):
                for root_dir, _, files in os.walk(s_dir):
                    for f in files:
                        if f.endswith(".pt") or f.endswith(".onnx") or f.endswith(".engine"):
                            full_p = os.path.abspath(os.path.join(root_dir, f))
                            if full_p not in seen_paths and os.path.exists(full_p):
                                seen_paths.add(full_p)
                                rel_p = os.path.relpath(full_p, base_dir)
                                model_items.append((f"模型: {rel_p}", full_p))

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
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return base_dir if os.path.exists(base_dir) else os.getcwd()

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

    def set_status(self, msg: str):
        """安全更新状态，统一输出到终端与主窗口状态栏"""
        if hasattr(self, 'lbl_status') and self.lbl_status is not None:
            try:
                self.lbl_status.setText(msg)
            except Exception:
                pass
        if self.main_window and hasattr(self.main_window, 'statusBar'):
            try:
                self.main_window.statusBar().showMessage(msg, 4000)
            except Exception:
                pass
        safe_print(f"[Model Center Terminal] {msg}")

    def on_model_selected(self, idx: int):
        if idx < 0:
            return
        path_val = self.combo_models.itemData(idx)
        if path_val == "custom":
            self.browse_custom_model()
        elif path_val:
            if not os.path.exists(path_val):
                self.combo_models.removeItem(idx)
                self.set_status("提示: 所选模型文件在磁盘上不存在。")
                return
            self.load_model(path_val)

    def load_model(self, model_path: str, silent: bool = False):
        if not os.path.exists(model_path):
            if not silent:
                QMessageBox.warning(self, "警告", f"模型文件不存在: {model_path}")
            self.refresh_model_selector()
            return

        try:
            class_dict = self.annotator.load_model(model_path)

            self.populate_class_table(class_dict)
            msg = f"已加载模型: {os.path.basename(model_path)} (包含类别数: {len(class_dict)})"
            self.set_status(msg)

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
            err_str = str(e)
            safe_print(f"[YOLO Model Center Error] 模型载入异常: {err_str}")
            if not silent:
                QMessageBox.critical(self, "模型载入失败", err_str)
            else:
                self.set_status(f"模型载入异常: {err_str}")



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

    def save_settings(self):
        """保存当前模型中心的所有参数真实状态"""
        try:
            settings = QSettings("ByteFlow", "LabelImg2")
            settings.setValue("model_center/geometry", self.saveGeometry())
            settings.setValue("model_center/conf", int(self.slider_conf.value()))
            settings.setValue("model_center/iou", int(self.slider_iou.value()))
            settings.setValue("model_center/imgsz_idx", int(self.combo_imgsz.currentIndex()))
            settings.setValue("model_center/device_idx", int(self.combo_device.currentIndex()))
            settings.setValue("model_center/mode", 2 if (hasattr(self, 'rb_mode_append') and self.rb_mode_append.isChecked()) else 1)
            settings.setValue("model_center/save_format_idx", int(self.combo_save_format.currentIndex()))
            if self.annotator and self.annotator.model_path:
                settings.setValue("model_center/last_model_path", str(self.annotator.model_path))
        except Exception:
            pass

    def restore_settings(self):
        """还原上次关闭前的真实参数状态"""
        try:
            settings = QSettings("ByteFlow", "LabelImg2")
            geom = settings.value("model_center/geometry")
            if geom:
                self.restoreGeometry(geom)

            conf_val = settings.value("model_center/conf", 25, type=int)
            iou_val = settings.value("model_center/iou", 45, type=int)
            self.slider_conf.setValue(conf_val)
            self.slider_iou.setValue(iou_val)

            imgsz_idx = settings.value("model_center/imgsz_idx", 0, type=int)
            if 0 <= imgsz_idx < self.combo_imgsz.count():
                self.combo_imgsz.setCurrentIndex(imgsz_idx)

            dev_idx = settings.value("model_center/device_idx", 0, type=int)
            if 0 <= dev_idx < self.combo_device.count():
                self.combo_device.setCurrentIndex(dev_idx)

            mode_val = settings.value("model_center/mode", 1, type=int)
            if mode_val == 2 and hasattr(self, 'rb_mode_append'):
                self.rb_mode_append.setChecked(True)
            elif hasattr(self, 'rb_mode_overwrite'):
                self.rb_mode_overwrite.setChecked(True)

            fmt_idx = settings.value("model_center/save_format_idx", 0, type=int)
            if 0 <= fmt_idx < self.combo_save_format.count():
                self.combo_save_format.setCurrentIndex(fmt_idx)

            last_pt = settings.value("model_center/last_model_path", "", type=str)
            if last_pt and os.path.exists(last_pt):
                self.load_model(last_pt, silent=True)
            else:
                for i in range(self.combo_models.count()):
                    p = self.combo_models.itemData(i)
                    if p and p != "custom" and os.path.exists(p):
                        self.load_model(p, silent=True)
                        break
        except Exception:
            pass


    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def hideEvent(self, event):
        self.save_settings()
        super().hideEvent(event)

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
                f"检测到标注文件 [{stem}.xml] 已存在！\n当前为【完全覆盖模式】，是否确定覆盖已有标注内容？\n\n(提示：若想保留原图已有标注，请在模型中心切换为【追加合并模式】)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No if hasattr(QMessageBox, 'StandardButton') else QMessageBox.Yes | QMessageBox.No,
                QMessageBox.StandardButton.No if hasattr(QMessageBox, 'StandardButton') else QMessageBox.No
            )
            yes_val = QMessageBox.StandardButton.Yes if hasattr(QMessageBox, 'StandardButton') else QMessageBox.Yes
            if reply != yes_val:
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

            # 过滤未选中的类别并应用映射
            filtered_boxes = []
            for b in boxes:
                raw_n = b.get("class_name", "object")
                if mapping and raw_n not in mapping:
                    continue
                final_n = mapping.get(raw_n, raw_n) if mapping else raw_n
                b_copy = dict(b)
                b_copy["class_name"] = final_n
                filtered_boxes.append(b_copy)

            from libs.shape import Shape
            from libs.lib import generateColorByText

            if is_append:
                # 追加合并模式：
                # 1. 保持当前画布上已有所有标注框（名称、位置、尺寸、角度）100% 绝不发生改变
                existing_shapes = list(self.main_window.canvas.shapes) if hasattr(self.main_window, 'canvas') else []

                def get_shape_rect(s):
                    xs = [p.x() for p in s.points]
                    ys = [p.y() for p in s.points]
                    return [min(xs), min(ys), max(xs), max(ys)]

                def calc_box_iou(b1, b2):
                    x1 = max(b1[0], b2[0])
                    y1 = max(b1[1], b2[1])
                    x2 = min(b1[2], b2[2])
                    y2 = min(b1[3], b2[3])
                    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
                    a1 = max(0.0, b1[2] - b1[0]) * max(0.0, b1[3] - b1[1])
                    a2 = max(0.0, b2[2] - b2[0]) * max(0.0, b2[3] - b2[1])
                    union = a1 + a2 - inter
                    return inter / union if union > 0 else 0.0

                existing_rects = [get_shape_rect(s) for s in existing_shapes if len(s.points) >= 2]
                added_count = 0

                for b in filtered_boxes:
                    bbox = b.get("bbox", [0, 0, 0, 0])
                    # 若与已有任何标注框发生明显重叠 (IoU > 0.65)，说明已有人工/现有标注覆盖，跳过
                    is_covered = False
                    for ex_r in existing_rects:
                        if calc_box_iou(bbox, ex_r) > 0.65:
                            is_covered = True
                            break
                    if not is_covered:
                        xmin, ymin, xmax, ymax = bbox[0], bbox[1], bbox[2], bbox[3]
                        new_s = Shape(label=b["class_name"])
                        new_s.addPoint(QPointF(xmin, ymin))
                        new_s.addPoint(QPointF(xmax, ymin))
                        new_s.addPoint(QPointF(xmax, ymax))
                        new_s.addPoint(QPointF(xmin, ymax))
                        new_s.close()
                        c = generateColorByText(b["class_name"])
                        new_s.line_color = c
                        new_s.fill_color = c
                        if hasattr(self.main_window, 'drawCorner'):
                            new_s.alwaysShowCorner = self.main_window.drawCorner.isChecked()
                        self.main_window.canvas.shapes.append(new_s)
                        self.main_window.addLabel(new_s)
                        existing_rects.append([xmin, ymin, xmax, ymax])
                        added_count += 1

                # 2. 保存并刷新
                if hasattr(self.main_window, 'setDirty'):
                    self.main_window.setDirty()
                if hasattr(self.main_window, 'saveFile'):
                    self.main_window.saveFile()
                if hasattr(self.main_window, 'canvas'):
                    self.main_window.canvas.update()
                if hasattr(self.main_window, 'markFileSavedInList'):
                    self.main_window.markFileSavedInList(img_path)
                if hasattr(self.main_window, 'update_stats'):
                    self.main_window.update_stats()

                mode_str = "追加合并模式"
                status_msg = f"单图自动批注完成 [{mode_str}]: 已在原标注基础上追加新检测目标 {added_count} 个 (原标注完全保留) -> {os.path.basename(xml_path)}"
            else:
                # 完全覆盖替换模式：清空现有标签，载入模型检测的所有目标
                if hasattr(self.main_window, 'remAllLabels'):
                    self.main_window.remAllLabels()

                for b in filtered_boxes:
                    bbox = b.get("bbox", [0, 0, 0, 0])
                    xmin, ymin, xmax, ymax = bbox[0], bbox[1], bbox[2], bbox[3]
                    new_s = Shape(label=b["class_name"])
                    new_s.addPoint(QPointF(xmin, ymin))
                    new_s.addPoint(QPointF(xmax, ymin))
                    new_s.addPoint(QPointF(xmax, ymax))
                    new_s.addPoint(QPointF(xmin, ymax))
                    new_s.close()
                    c = generateColorByText(b["class_name"])
                    new_s.line_color = c
                    new_s.fill_color = c
                    if hasattr(self.main_window, 'drawCorner'):
                        new_s.alwaysShowCorner = self.main_window.drawCorner.isChecked()
                    self.main_window.canvas.shapes.append(new_s)
                    self.main_window.addLabel(new_s)

                if hasattr(self.main_window, 'setDirty'):
                    self.main_window.setDirty()
                if hasattr(self.main_window, 'saveFile'):
                    self.main_window.saveFile()
                if hasattr(self.main_window, 'canvas'):
                    self.main_window.canvas.update()
                if hasattr(self.main_window, 'markFileSavedInList'):
                    self.main_window.markFileSavedInList(img_path)
                if hasattr(self.main_window, 'update_stats'):
                    self.main_window.update_stats()

                mode_str = "完全覆盖模式"
                status_msg = f"单图自动批注完成 [{mode_str}]: 替换为 {len(filtered_boxes)} 个目标 -> {os.path.basename(xml_path)}"

            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
                self.main_window.statusBar().showMessage(status_msg, 5000)
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
                    f"在保存目录中检测到 {existing_count} 个已存在的标注文件！\n当前为【完全覆盖模式】，是否确定覆盖现有标注？\n\n(提示：若想保留已有标注并在其上新增目标，请切换为【追加合并模式】)",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No if hasattr(QMessageBox, 'StandardButton') else QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.StandardButton.No if hasattr(QMessageBox, 'StandardButton') else QMessageBox.No
                )
                yes_val = QMessageBox.StandardButton.Yes if hasattr(QMessageBox, 'StandardButton') else QMessageBox.Yes
                if reply != yes_val:
                    return

        if hasattr(self.main_window, 'defaultSaveDir'):
            self.main_window.defaultSaveDir = save_dir

        conf = self.slider_conf.value() / 100.0
        iou = self.slider_iou.value() / 100.0
        mapping = self.get_class_mapping()

        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

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

        msg = f"[Auto-Annotate Terminal] 开始批量自动批注文件夹 (共 {len(image_paths)} 张图片)..."
        if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
            self.main_window.statusBar().showMessage(msg, 5000)
        print(msg, flush=True)
        self.batch_thread.start()

    def on_batch_progress(self, current: int, total: int, filename: str, status_msg: str):
        val = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(val)
        msg = f"[批量标注 {current}/{total}] {filename} - {status_msg}"
        if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
            self.main_window.statusBar().showMessage(msg, 3000)
        print(f"[Auto-Annotate Terminal] {msg}", flush=True)

    def on_batch_finished(self, processed: int, total_boxes: int):
        self.progress_bar.setVisible(False)
        if hasattr(self.main_window, 'filePath') and self.main_window.filePath:
            self.main_window.loadFile(self.main_window.filePath)

        save_dir = self.cur_xml_dir
        finish_msg = f"批量自动批注完成！成功处理 {processed} 张图片，生成 {total_boxes} 个目标标注 (保存于: {save_dir})"
        if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
            self.main_window.statusBar().showMessage(finish_msg, 6000)
        print(f"[Auto-Annotate Terminal] {finish_msg}", flush=True)

    def on_batch_error(self, err_msg: str):
        self.progress_bar.setVisible(False)
        print(f"[Auto-Annotate Terminal Error] 批量批注中断: {err_msg}", flush=True)
        QMessageBox.critical(self, "批量批注中断", err_msg)

