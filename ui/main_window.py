import os
from typing import Optional, List, Dict, Any
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QAction, QKeySequence, QIcon
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter, QStatusBar,
    QToolBar, QMessageBox, QLabel
)

from ui.left_panel import LeftPanel
from ui.canvas import ImageAnnotationCanvas
from ui.right_panel import RightPanel
from ui.train_tab import TrainTab
from core.yolo_annotator import YOLOAnnotator
from core.xml_handler import XMLHandler
from utils.worker_thread import BatchAnnotationThread
from PyQt6.QtWidgets import QTabWidget
from libs.settings import Settings

class MainWindow(QMainWindow):
    """
    YOLO 自动标注与模型训练一体化工作站主窗口
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YOLO 模型训练 & 自动图像标注工作站 v2.0 (Pascal VOC XML)")
        self.resize(1550, 950)

        # 读取持久化配置
        self.settings = Settings()
        self.settings.load()
        self.lastOpenDir = self.settings.get('lastOpenDir', None)
        self.defaultSaveDir = self.settings.get('defaultSaveDir', None)

        # 核心逻辑与组件
        self.annotator = YOLOAnnotator()
        self.current_image_path: Optional[str] = None
        self.batch_thread: Optional[BatchAnnotationThread] = None

        self.init_ui()
        self.init_shortcuts()
        self.check_system_cuda()
        self.restore_previous_state()

    def init_ui(self):
        # 创建 QTabWidget 主选项卡组件
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Tab 1: 模型训练中心
        self.train_tab = TrainTab()
        self.train_tab.model_trained.connect(self.on_model_trained_and_switch)
        self.tab_widget.addTab(self.train_tab, "模型训练中心 (Train)")

        # Tab 2: 自动标注与交互画布工作站
        annotator_widget = QWidget()
        annotator_layout = QHBoxLayout(annotator_widget)
        annotator_layout.setContentsMargins(0, 0, 0, 0)
        annotator_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧文件面板
        self.left_panel = LeftPanel()
        self.left_panel.image_selected.connect(self.on_image_selected)
        self.splitter.addWidget(self.left_panel)

        # 中间交互画布
        self.canvas = ImageAnnotationCanvas()
        self.canvas.box_changed.connect(self.on_canvas_boxes_changed)
        self.canvas.cursor_position_changed.connect(self.on_cursor_moved)
        self.canvas.zoom_changed.connect(self.on_zoom_changed)
        self.splitter.addWidget(self.canvas)

        # 右侧控制面板
        self.right_panel = RightPanel()
        self.right_panel.model_loaded.connect(self.load_yolo_model)
        self.right_panel.run_single_auto.connect(self.auto_annotate_current_image)
        self.right_panel.run_batch_auto.connect(self.start_batch_annotation)
        self.right_panel.stop_batch.connect(self.stop_batch_annotation)
        self.right_panel.save_current_annotation.connect(self.save_current_annotation)
        self.splitter.addWidget(self.right_panel)

        # 初始分割比例 (300px : 880px : 370px)
        self.splitter.setSizes([300, 880, 370])
        annotator_layout.addWidget(self.splitter)

        self.tab_widget.addTab(annotator_widget, "Yolo")

        # 2. 顶部工具栏
        self.create_toolbar()

        # 3. 底部状态栏
        self.create_statusbar()

    def on_model_trained_and_switch(self, best_pt_path: str):
        """当模型训练完成时，自动切换到标注页并加载该模型"""
        self.tab_widget.setCurrentIndex(1) # 切换到标注页
        self.load_yolo_model(best_pt_path)


    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        # 打开文件夹
        act_open_dir = QAction("打开图片目录", self)
        act_open_dir.setShortcut("Ctrl+O")
        act_open_dir.triggered.connect(self.left_panel.select_directory)
        toolbar.addAction(act_open_dir)

        # 加载模型
        act_load_model = QAction("加载 YOLO 模型", self)
        act_load_model.triggered.connect(self.right_panel.select_model_file)
        toolbar.addAction(act_load_model)

        toolbar.addSeparator()

        # 划框新建按钮
        self.act_draw_mode = QAction("手动划框 (W)", self)
        self.act_draw_mode.setCheckable(True)
        self.act_draw_mode.triggered.connect(self.toggle_draw_mode)
        toolbar.addAction(self.act_draw_mode)

        # 删除选中框
        act_del_box = QAction("删除选中框 (Del / Q)", self)
        act_del_box.setShortcuts([QKeySequence("Delete"), QKeySequence("q")])
        act_del_box.triggered.connect(self.canvas.remove_selected_box)
        toolbar.addAction(act_del_box)

        # 清空所有框
        act_clear_all = QAction("清空所有框", self)
        act_clear_all.triggered.connect(self.canvas.clear_boxes)
        toolbar.addAction(act_clear_all)

        toolbar.addSeparator()

        # 单图自动标注
        act_auto_single = QAction("自动标注当前图 (S)", self)
        act_auto_single.triggered.connect(self.auto_annotate_current_image)
        toolbar.addAction(act_auto_single)

        # 批量标注
        act_auto_batch = QAction("一键批量自动标注", self)
        act_auto_batch.triggered.connect(self.start_batch_annotation)
        toolbar.addAction(act_auto_batch)

        toolbar.addSeparator()

        # 保存
        act_save = QAction("保存 XML (Ctrl+S)", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self.save_current_annotation)
        toolbar.addAction(act_save)
        toolbar.addAction(act_save)

    def create_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        self.lbl_status_pos = QLabel("坐标: X: 0, Y: 0")
        self.lbl_status_zoom = QLabel("缩放: 100%")
        self.lbl_status_info = QLabel("就绪")
        self.lbl_status_cuda = QLabel("GPU (CUDA): 检查中...")

        self.statusbar.addPermanentWidget(self.lbl_status_pos, 1)
        self.statusbar.addPermanentWidget(self.lbl_status_zoom, 1)
        self.statusbar.addPermanentWidget(self.lbl_status_cuda, 1)
        self.statusbar.addWidget(self.lbl_status_info, 2)

    def check_system_cuda(self):
        if YOLOAnnotator.is_cuda_available():
            self.lbl_status_cuda.setText("🚀 CUDA GPU 加速就绪")
            self.lbl_status_cuda.setStyleSheet("color: #10B981; font-weight: bold;")
        else:
            self.lbl_status_cuda.setText("💻 使用 CPU 计算")
            self.lbl_status_cuda.setStyleSheet("color: #94A3B8;")

    def init_shortcuts(self):
        # 绑定快捷键 A (上一张), D (下一张)
        act_prev = QAction(self)
        act_prev.setShortcut("A")
        act_prev.triggered.connect(lambda: (print("[Shortcut A Terminal] 切换至上一张图片", flush=True), self.left_panel.select_previous()))
        self.addAction(act_prev)

        act_next = QAction(self)
        act_next.setShortcut("D")
        act_next.triggered.connect(lambda: (print("[Shortcut D Terminal] 切换至下一张图片", flush=True), self.left_panel.select_next()))
        self.addAction(act_next)

        # 快捷键 S (自动标注当前页面)
        act_auto_s = QAction(self)
        act_auto_s.setShortcut("S")
        act_auto_s.triggered.connect(self.auto_annotate_current_image)
        self.addAction(act_auto_s)

        # W 切换划框模式
        act_toggle_w = QAction(self)
        act_toggle_w.setShortcut("W")
        act_toggle_w.triggered.connect(lambda: (print("[Shortcut W Terminal] 切换划框新建模式", flush=True), self.act_draw_mode.trigger()))
        self.addAction(act_toggle_w)

        # Q 删除当前选中框
        act_del_q = QAction(self)
        act_del_q.setShortcut("Q")
        act_del_q.triggered.connect(self.canvas.remove_selected_box)
        self.addAction(act_del_q)

        # E 键切换 OBB 模式
        act_toggle_e = QAction(self)
        act_toggle_e.setShortcut("E")
        act_toggle_e.triggered.connect(lambda: (print("[Shortcut E Terminal] 切换 OBB 模式", flush=True)))
        self.addAction(act_toggle_e)

        # Ctrl+Shift+Z 重做键
        act_redo = QAction(self)
        act_redo.setShortcut("Ctrl+Shift+Z")
        act_redo.triggered.connect(lambda: print("[Shortcut Ctrl+Shift+Z Terminal] 触发重做操作", flush=True))
        self.addAction(act_redo)

    def load_yolo_model(self, model_path: str):
        """加载 YOLO 模型并更新右侧面板"""
        try:
            self.statusBar().showMessage("正在加载 YOLO 模型...", 3000)
            class_dict = self.annotator.load_model(model_path)
            self.right_panel.update_model_info(model_path, class_dict, self.annotator.device)
            self.statusBar().showMessage(f"成功加载模型: {os.path.basename(model_path)}", 5000)
            print(f"[Auto-Annotate Terminal] 成功加载模型: {model_path}", flush=True)
        except Exception as e:
            QMessageBox.critical(self, "模型加载错误", f"加载 YOLO 模型失败:\n{str(e)}")

    def on_image_selected(self, image_path: str):
        """左侧列表选中新图片时被触发"""
        if not os.path.exists(image_path):
            return

        self.current_image_path = image_path
        self.canvas.load_image(image_path)

        # 检查是否已存在同名 .xml 标注文件
        dir_name = os.path.dirname(image_path)
        stem = os.path.splitext(os.path.basename(image_path))[0]
        xml_path = os.path.join(dir_name, f"{stem}.xml")

        if os.path.exists(xml_path):
            try:
                _, objects = XMLHandler.read_pascal_voc_xml(xml_path)
                for obj in objects:
                    c_name = obj.get("class_name", "object")
                    bbox = obj.get("bbox", [0, 0, 0, 0])
                    self.canvas.add_box(bbox[0], bbox[1], bbox[2], bbox[3], c_name)
                self.lbl_status_info.setText(f"已载入标注 XML (目标框数: {len(objects)})")
            except Exception as e:
                self.lbl_status_info.setText(f"读取已有 XML 失败: {str(e)}")
        else:
            self.lbl_status_info.setText("当前图片未生成标注")

    def auto_annotate_current_image(self):
        """使用已加载的 YOLO 模型自动标注当前显示的图片 (快捷键 S 触发)"""
        if not self.current_image_path or not os.path.exists(self.current_image_path):
            QMessageBox.warning(self, "警告", "未找到有效的图片！请先在左侧导入并选择一张图片。")
            return

        if not self.annotator.model:
            QMessageBox.warning(self, "警告", "请先加载 YOLO 模型 (.pt)！")
            return

        # 检查同名 XML 是否已存在并弹窗确认
        stem = os.path.splitext(os.path.basename(self.current_image_path))[0]
        out_dir = os.path.dirname(self.current_image_path)
        xml_path = os.path.join(out_dir, f"{stem}.xml")
        if os.path.exists(xml_path):
            reply = QMessageBox.question(
                self,
                "覆盖标注确认",
                f"检测到标注文件 [{stem}.xml] 已存在！\n是否确定覆盖保存原有标注内容？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.lbl_status_info.setText("已取消自动标注 (保留原有标注)")
                return

        conf = self.right_panel.get_conf_threshold()
        iou = self.right_panel.get_iou_threshold()
        enabled_ids = self.right_panel.get_enabled_class_ids()

        try:
            detected_boxes = self.annotator.predict_image(
                image_path=self.current_image_path,
                conf_threshold=conf,
                iou_threshold=iou,
                enabled_classes=enabled_ids
            )

            # 刷新画布渲染
            self.canvas.clear_boxes()
            for box in detected_boxes:
                c_name = box["class_name"]
                b = box["bbox"]
                self.canvas.add_box(b[0], b[1], b[2], b[3], c_name)

            # 保存为 XML
            self.save_current_annotation()
            self.left_panel.update_item_status(self.current_image_path, is_auto=True)
            status_msg = f"自动标注完成 (快捷键 S): {os.path.basename(self.current_image_path)} -> 检测到 {len(detected_boxes)} 个目标对象"
            self.lbl_status_info.setText(status_msg)
            print(f"[Auto-Annotate Terminal] {status_msg}", flush=True)

        except Exception as e:
            QMessageBox.critical(self, "自动标注失败", f"推理过程中出错:\n{str(e)}")

    def start_batch_annotation(self):
        """开启后台异步批量全自动标注"""
        if not self.left_panel.image_paths:
            QMessageBox.warning(self, "警告", "未找到有效图片！请先在左侧导入包含图片的文件夹。")
            return

        if not self.annotator.model:
            QMessageBox.warning(self, "提示", "请先加载 YOLO 模型！")
            return

        # 检查批量覆盖弹窗
        existing_count = sum(1 for p in self.left_panel.image_paths if os.path.exists(os.path.join(os.path.dirname(p), f"{os.path.splitext(os.path.basename(p))[0]}.xml")))
        if existing_count > 0:
            reply = QMessageBox.question(
                self,
                "批量覆盖确认",
                f"在保存目录中检测到 {existing_count} 个已存在的 XML 标注文件！\n是否确定覆盖现有标注？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.lbl_status_info.setText("已取消批量自动标注")
                return

        conf = self.right_panel.get_conf_threshold()
        iou = self.right_panel.get_iou_threshold()
        enabled_ids = self.right_panel.get_enabled_class_ids()
        mapping = self.right_panel.get_class_mapping()
        export_opts = self.right_panel.get_export_options()

        self.right_panel.set_batch_running(True)
        print(f"[Auto-Annotate Terminal] 启动批量自动化标注 (共 {len(self.left_panel.image_paths)} 张图片)...", flush=True)

        self.batch_thread = BatchAnnotationThread(
            annotator=self.annotator,
            image_paths=self.left_panel.image_paths,
            conf_threshold=conf,
            iou_threshold=iou,
            class_mapping=mapping,
            enabled_class_ids=enabled_ids,
            save_xml=export_opts["save_xml"],
            save_yolo_txt=export_opts["save_yolo_txt"],
            overwrite=export_opts["overwrite"]
        )

        self.batch_thread.progress_signal.connect(self.right_panel.update_progress)
        self.batch_thread.item_finished_signal.connect(self.on_batch_item_finished)
        self.batch_thread.finished_signal.connect(self.on_batch_finished)
        self.batch_thread.error_signal.connect(self.on_batch_error)

        self.batch_thread.start()

    def stop_batch_annotation(self):
        if self.batch_thread and self.batch_thread.isRunning():
            self.batch_thread.cancel()

    def on_batch_item_finished(self, image_path: str, xml_path: str, box_count: int):
        self.left_panel.update_item_status(image_path, is_auto=True)
        print(f"[Auto-Annotate Terminal] 处理完成: {os.path.basename(image_path)} -> 框数: {box_count}", flush=True)

    def on_batch_finished(self, processed: int, total_boxes: int):
        self.right_panel.set_batch_running(False)
        msg = f"批量标注完成！成功处理 {processed} 张图片，共检测并记录 {total_boxes} 个目标标注框"
        self.lbl_status_info.setText(msg)
        print(f"[Auto-Annotate Terminal] {msg}", flush=True)

    def on_batch_error(self, error_msg: str):
        self.right_panel.set_batch_running(False)
        print(f"[Auto-Annotate Terminal Error] 批量任务错误: {error_msg}", flush=True)
        QMessageBox.critical(self, "批量任务错误", error_msg)

    def save_current_annotation(self):
        """保存当前画布上的标注内容为 XML"""
        if not self.current_image_path:
            return

        boxes_data = self.canvas.get_all_boxes()
        stem = os.path.splitext(os.path.basename(self.current_image_path))[0]
        out_dir = os.path.dirname(self.current_image_path)
        xml_path = os.path.join(out_dir, f"{stem}.xml")

        mapping = self.right_panel.get_class_mapping()
        export_opts = self.right_panel.get_export_options()

        try:
            XMLHandler.save_pascal_voc_xml(
                image_path=self.current_image_path,
                objects=boxes_data,
                output_xml_path=xml_path,
                class_mapping=mapping,
                overwrite=True
            )

            if export_opts["save_yolo_txt"]:
                txt_path = os.path.join(out_dir, f"{stem}.txt")
                cls_to_id = {v: k for k, v in self.annotator.class_names.items()}
                XMLHandler.save_yolo_txt(
                    image_path=self.current_image_path,
                    objects=boxes_data,
                    output_txt_path=txt_path,
                    class_to_id=cls_to_id
                )

            self.left_panel.update_item_status(self.current_image_path, is_auto=False)
            self.lbl_status_info.setText(f"已成功保存标注: {os.path.basename(xml_path)}")
        except Exception as e:
            QMessageBox.critical(self, "保存 XML 失败", str(e))

    def toggle_draw_mode(self, checked: bool):
        current_cls = "object"
        if self.right_panel.class_info_list:
            # 默认使用右侧被选中的第一个类别
            for info in self.right_panel.class_info_list:
                if info["enabled"]:
                    current_cls = info["mapped_name"]
                    break

        self.canvas.set_draw_mode(checked, current_cls)

    def on_canvas_boxes_changed(self):
        box_count = len(self.canvas.box_items)
        self.lbl_status_info.setText(f"当前画布目标数量: {box_count}")

    def on_cursor_moved(self, x: int, y: int):
        self.lbl_status_pos.setText(f"坐标: X: {x}, Y: {y}")

    def on_zoom_changed(self, factor: float):
        self.lbl_status_zoom.setText(f"缩放: {int(factor * 100)}%")

    def restore_previous_state(self):
        """启动时自动恢复上一次关闭前的目录、文件与模型状态"""
        last_dir = self.settings.get('lastOpenDir', None) or self.settings.get('filename', None)
        if last_dir and os.path.exists(last_dir):
            if os.path.isfile(last_dir):
                last_dir = os.path.dirname(last_dir)
            if os.path.isdir(last_dir):
                self.lastOpenDir = last_dir
                self.left_panel.load_directory(last_dir)

        last_file = self.settings.get('filename', None)
        if last_file and os.path.exists(last_file) and os.path.isfile(last_file):
            self.on_image_selected(last_file)

        save_dir = self.settings.get('defaultSaveDir', None) or self.settings.get('savedir', None)
        if save_dir and os.path.exists(save_dir) and os.path.isdir(save_dir):
            self.defaultSaveDir = save_dir

        last_model = self.settings.get('last_model_path', None)
        if last_model and os.path.exists(last_model):
            self.load_yolo_model(last_model)
            print(f"[MainWindow Startup] 已自动恢复加载模型: {os.path.basename(last_model)}", flush=True)

    def closeEvent(self, event):
        """窗口关闭时自动全量持久化当前状态"""
        cur_dir = getattr(self.left_panel, 'current_dir', None) or self.lastOpenDir
        if cur_dir and os.path.exists(cur_dir):
            self.settings['lastOpenDir'] = cur_dir

        if self.current_image_path and os.path.exists(self.current_image_path):
            self.settings['filename'] = self.current_image_path

        if self.defaultSaveDir and os.path.exists(self.defaultSaveDir):
            self.settings['defaultSaveDir'] = self.defaultSaveDir

        if hasattr(self, 'annotator') and self.annotator and self.annotator.model_path:
            self.settings['last_model_path'] = self.annotator.model_path

        self.settings.save()
        super().closeEvent(event)
