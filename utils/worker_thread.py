import os
from typing import List, Dict, Any, Optional
from core.qt_compat import QThread, pyqtSignal
from core.yolo_annotator import YOLOAnnotator
from core.xml_handler import XMLHandler

class BatchAnnotationThread(QThread):
    """
    后台异步批量 YOLO 标注线程
    """
    # 信号定义
    progress_signal = pyqtSignal(int, int, str, str)  # (current, total, filename, status_msg)
    item_finished_signal = pyqtSignal(str, str, int)  # (image_path, xml_path, box_count)
    finished_signal = pyqtSignal(int, int)            # (total_images, total_boxes)
    error_signal = pyqtSignal(str)                    # (error_msg)

    def __init__(
        self,
        annotator: YOLOAnnotator,
        image_paths: List[str],
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        class_mapping: Optional[Dict[str, str]] = None,
        enabled_class_ids: Optional[List[int]] = None,
        save_xml: bool = True,
        save_yolo_txt: bool = False,
        overwrite: bool = True,
        custom_output_dir: Optional[str] = None
    ):
        super().__init__()
        self.annotator = annotator
        self.image_paths = image_paths
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.class_mapping = class_mapping or {}
        self.enabled_class_ids = enabled_class_ids
        self.save_xml = save_xml
        self.save_yolo_txt = save_yolo_txt
        self.overwrite = overwrite
        self.custom_output_dir = custom_output_dir
        self._is_cancelled = False

    def cancel(self):
        """取消批量推理任务"""
        self._is_cancelled = True

    def run(self):
        total_images = len(self.image_paths)
        total_boxes_found = 0
        processed_count = 0

        if not self.annotator or not self.annotator.model:
            self.error_signal.emit("YOLO 模型尚未加载！")
            return

        for idx, img_path in enumerate(self.image_paths):
            if self._is_cancelled:
                self.progress_signal.emit(idx, total_images, os.path.basename(img_path), "已取消批量标注")
                break

            filename = os.path.basename(img_path)
            self.progress_signal.emit(idx + 1, total_images, filename, f"正在推理 ({idx + 1}/{total_images})...")

            try:
                # 执行 YOLO 推理
                boxes = self.annotator.predict_image(
                    image_path=img_path,
                    conf_threshold=self.conf_threshold,
                    iou_threshold=self.iou_threshold,
                    enabled_classes=self.enabled_class_ids
                )
                
                box_count = len(boxes)
                total_boxes_found += box_count

                # 确定输出路径
                base_dir = self.custom_output_dir if self.custom_output_dir else os.path.dirname(img_path)
                file_stem = os.path.splitext(filename)[0]

                xml_path = os.path.join(base_dir, f"{file_stem}.xml")
                txt_path = os.path.join(base_dir, f"{file_stem}.txt")

                if self.save_xml:
                    XMLHandler.save_pascal_voc_xml(
                        image_path=img_path,
                        objects=boxes,
                        output_xml_path=xml_path,
                        class_mapping=self.class_mapping,
                        overwrite=self.overwrite
                    )

                if self.save_yolo_txt:
                    # 创建类别名 -> ID 映射
                    cls_to_id = {v: k for k, v in self.annotator.class_names.items()}
                    XMLHandler.save_yolo_txt(
                        image_path=img_path,
                        objects=boxes,
                        output_txt_path=txt_path,
                        class_to_id=cls_to_id
                    )

                processed_count += 1
                self.item_finished_signal.emit(img_path, xml_path, box_count)

            except Exception as e:
                self.progress_signal.emit(idx + 1, total_images, filename, f"推理出错: {str(e)}")

        self.finished_signal.emit(processed_count, total_boxes_found)
