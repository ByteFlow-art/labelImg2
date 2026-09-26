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
        save_format: str = "Pascal VOC XML (*.xml)",
        save_xml: bool = True,
        save_yolo_txt: bool = False,
        overwrite: bool = True,
        custom_output_dir: Optional[str] = None,
        class_list: Optional[List[str]] = None
    ):
        super().__init__()
        self.annotator = annotator
        self.image_paths = image_paths
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.class_mapping = class_mapping or {}
        self.enabled_class_ids = enabled_class_ids
        self.save_format = save_format
        self.save_xml = save_xml
        self.save_yolo_txt = save_yolo_txt
        self.overwrite = overwrite
        self.custom_output_dir = custom_output_dir
        self.class_list = class_list
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

        from libs.annotation_io import get_format_ext, write_annotations, read_annotations, find_annotation_file
        from PIL import Image

        ext = get_format_ext(self.save_format)

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

                # 确定输出路径与图片尺寸
                base_dir = self.custom_output_dir if self.custom_output_dir else os.path.dirname(img_path)
                file_stem = os.path.splitext(filename)[0]
                target_path = os.path.join(base_dir, f"{file_stem}{ext}")

                img_w, img_h = 0, 0
                try:
                    with Image.open(img_path) as img_pil:
                        img_w, img_h = img_pil.size
                except Exception:
                    img_w, img_h = 1920, 1080
                img_shape = (img_h, img_w, 3)

                # 将预测框转换为标准 shapes 列表
                new_shapes = []
                for b in boxes:
                    raw_n = b.get("class_name", "object")
                    final_n = self.class_mapping.get(raw_n, raw_n) if self.class_mapping else raw_n
                    xmin, ymin, xmax, ymax = b.get("bbox", [0, 0, 0, 0])
                    new_shapes.append({
                        "label": final_n,
                        "points": [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)],
                        "line_color": None,
                        "fill_color": None,
                        "difficult": False,
                        "isRotated": False,
                        "direction": 0.0,
                        "extra_label": ""
                    })

                final_shapes = []
                if not self.overwrite:
                    # 追加合并模式：先尝试读取已有标注文件
                    existing_anno, existing_fmt = find_annotation_file(
                        image_path=img_path,
                        preferred_format=self.save_format,
                        save_dir=base_dir,
                        image_dir=os.path.dirname(img_path)
                    )
                    existing_shapes = []
                    if existing_anno and os.path.isfile(existing_anno):
                        existing_shapes = read_annotations(
                            file_path=existing_anno,
                            format_name=existing_fmt,
                            image_shape=img_shape,
                            class_list=self.class_list,
                            image_path=img_path
                        )

                    existing_rects = []
                    for s in existing_shapes:
                        if isinstance(s, (list, tuple)):
                            lbl, pts = s[0], s[1]
                            diff = s[4] if len(s) > 4 else False
                            isRot = s[5] if len(s) > 5 else False
                            dir_val = s[6] if len(s) > 6 else 0.0
                            extra = s[7] if len(s) > 7 else ''
                            pts_coords = [(p.x(), p.y()) if hasattr(p, 'x') else tuple(p) for p in pts]
                            final_shapes.append({
                                'label': lbl, 'points': pts_coords, 'line_color': None, 'fill_color': None,
                                'difficult': diff, 'isRotated': isRot, 'direction': dir_val, 'extra_label': extra
                            })
                            xs = [p[0] for p in pts_coords]
                            ys = [p[1] for p in pts_coords]
                            if xs and ys:
                                existing_rects.append([min(xs), min(ys), max(xs), max(ys)])
                        elif isinstance(s, dict):
                            final_shapes.append(s)
                            pts_coords = s.get('points', [])
                            xs = [p[0] for p in pts_coords]
                            ys = [p[1] for p in pts_coords]
                            if xs and ys:
                                existing_rects.append([min(xs), min(ys), max(xs), max(ys)])

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

                    for ns in new_shapes:
                        xs = [p[0] for p in ns['points']]
                        ys = [p[1] for p in ns['points']]
                        nr = [min(xs), min(ys), max(xs), max(ys)]
                        if not any(calc_box_iou(nr, er) > 0.65 for er in existing_rects):
                            final_shapes.append(ns)
                            existing_rects.append(nr)
                else:
                    final_shapes = new_shapes

                # 统一以用户指定的格式保存
                write_annotations(
                    target_file=target_path,
                    format_name=self.save_format,
                    shapes=final_shapes,
                    image_path=img_path,
                    image_shape=img_shape,
                    class_list=self.class_list
                )

                box_count = len(final_shapes)
                total_boxes_found += box_count
                processed_count += 1
                self.item_finished_signal.emit(img_path, target_path, box_count)

            except Exception as e:
                self.progress_signal.emit(idx + 1, total_images, filename, f"推理出错: {str(e)}")

        self.finished_signal.emit(processed_count, total_boxes_found)
