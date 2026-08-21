import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image

class XMLHandler:
    """
    Pascal VOC XML 标注格式读写器（兼容 LabelImg）
    与 YOLO TXT 格式同步生成器
    """

    @staticmethod
    def read_pascal_voc_xml(xml_path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        读取并解析 Pascal VOC .xml 文件

        :param xml_path: XML 文件路径
        :return: (image_info_dict, objects_list)
        """
        if not os.path.exists(xml_path):
            raise FileNotFoundError(f"XML 文件不存在: {xml_path}")

        tree = ET.parse(xml_path)
        root = tree.getroot()

        filename = root.findtext("filename", "")
        path = root.findtext("path", "")
        
        size_node = root.find("size")
        width = int(size_node.findtext("width", "0")) if size_node is not None else 0
        height = int(size_node.findtext("height", "0")) if size_node is not None else 0
        depth = int(size_node.findtext("depth", "3")) if size_node is not None else 3

        meta_info = {
            "filename": filename,
            "path": path,
            "width": width,
            "height": height,
            "depth": depth
        }

        objects = []
        for obj in root.findall("object"):
            name = obj.findtext("name", "")
            pose = obj.findtext("pose", "Unspecified")
            truncated = int(obj.findtext("truncated", "0"))
            difficult = int(obj.findtext("difficult", "0"))
            
            bndbox = obj.find("bndbox")
            robndbox = obj.find("robndbox")
            if bndbox is not None:
                xmin = float(bndbox.findtext("xmin", "0"))
                ymin = float(bndbox.findtext("ymin", "0"))
                xmax = float(bndbox.findtext("xmax", "0"))
                ymax = float(bndbox.findtext("ymax", "0"))
            elif robndbox is not None:
                cx = float(robndbox.findtext("cx", "0"))
                cy = float(robndbox.findtext("cy", "0"))
                w = float(robndbox.findtext("w", "0"))
                h = float(robndbox.findtext("h", "0"))
                xmin = cx - w / 2.0
                ymin = cy - h / 2.0
                xmax = cx + w / 2.0
                ymax = cy + h / 2.0
            else:
                xmin, ymin, xmax, ymax = 0.0, 0.0, 0.0, 0.0

            objects.append({
                "class_name": name,
                "confidence": 1.0,
                "bbox": [xmin, ymin, xmax, ymax],
                "pose": pose,
                "truncated": truncated,
                "difficult": difficult
            })

        return meta_info, objects

    @staticmethod
    def save_pascal_voc_xml(
        image_path: str,
        objects: List[Dict[str, Any]],
        output_xml_path: str,
        class_mapping: Optional[Dict[str, str]] = None,
        overwrite: bool = True
    ) -> str:
        """
        生成并保存 Pascal VOC .xml 文件，完美支持水平矩形框与 OBB 旋转框
        并在追加合并模式下 100% 保持已有手工标注框的所有属性（名称、位置、尺寸、角度）不发生改变。
        """
        class_mapping = class_mapping or {}
        from libs.pascal_voc_io import PascalVocWriter, PascalVocReader

        # 获取图片实际像素大小
        width, height, depth = 0, 0, 3
        if os.path.exists(image_path):
            try:
                with Image.open(image_path) as img:
                    width, height = img.size
                    mode = img.mode
                    depth = 3 if mode == 'RGB' else (1 if mode == 'L' else 4)
            except Exception:
                pass

        folder_name = os.path.basename(os.path.dirname(image_path))
        filename_val = os.path.basename(image_path)

        writer = PascalVocWriter(folder_name, filename_val, (height, width, depth), localImgPath=os.path.abspath(image_path))

        existing_boxes_coords = []
        if not overwrite and os.path.exists(output_xml_path):
            try:
                reader = PascalVocReader(output_xml_path)
                # 遍历所有已有标注，原汁原味全部保留
                for s_info in reader.shapes:
                    if len(s_info) == 5:
                        lbl, pts, _, _, diff = s_info
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        xmin, ymin, xmax, ymax = min(xs), min(ys), max(xs), max(ys)
                        writer.addBndBox(xmin, ymin, xmax, ymax, lbl, int(diff), None)
                        existing_boxes_coords.append((lbl, [xmin, ymin, xmax, ymax]))
                    elif len(s_info) == 6:
                        lbl, pts, _, _, diff, extra = s_info
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        xmin, ymin, xmax, ymax = min(xs), min(ys), max(xs), max(ys)
                        writer.addBndBox(xmin, ymin, xmax, ymax, lbl, int(diff), extra)
                        existing_boxes_coords.append((lbl, [xmin, ymin, xmax, ymax]))
                    elif len(s_info) >= 7:
                        # 旋转框：保留 cx, cy, w, h, angle
                        lbl = s_info[0]
                        pts = s_info[1]
                        diff = s_info[4]
                        angle = s_info[6] if len(s_info) > 6 else 0.0
                        extra = s_info[7] if len(s_info) > 7 else None
                        
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        xmin, ymin, xmax, ymax = min(xs), min(ys), max(xs), max(ys)
                        cx = (xmin + xmax) / 2.0
                        cy = (ymin + ymax) / 2.0
                        import math
                        w = math.sqrt((pts[1][0] - pts[0][0])**2 + (pts[1][1] - pts[0][1])**2)
                        h = math.sqrt((pts[2][0] - pts[1][0])**2 + (pts[2][1] - pts[1][1])**2)
                        writer.addRotatedBndBox(cx, cy, w, h, angle, lbl, int(diff), extra)
                        existing_boxes_coords.append((lbl, [xmin, ymin, xmax, ymax]))
            except Exception:
                pass

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

        for new_obj in objects:
            raw_name = new_obj.get("class_name", "object")
            final_name = class_mapping.get(raw_name, raw_name) if class_mapping else raw_name
            bbox = new_obj.get("bbox", [0, 0, 0, 0])
            xmin, ymin, xmax, ymax = bbox[0], bbox[1], bbox[2], bbox[3]

            # 坐标限制
            xmin = max(0, min(int(round(xmin)), width))
            ymin = max(0, min(int(round(ymin)), height))
            xmax = max(0, min(int(round(xmax)), width))
            ymax = max(0, min(int(round(ymax)), height))

            if xmax <= xmin or ymax <= ymin:
                continue

            # 若为追加合并模式，检查是否与现有已有标注重合 (IoU > 0.65)
            if not overwrite:
                is_dup = False
                for ex_lbl, ex_bbox in existing_boxes_coords:
                    if calc_box_iou([xmin, ymin, xmax, ymax], ex_bbox) > 0.65:
                        is_dup = True
                        break
                if is_dup:
                    continue

            writer.addBndBox(xmin, ymin, xmax, ymax, final_name, int(new_obj.get("difficult", 0)), None)

        os.makedirs(os.path.dirname(os.path.abspath(output_xml_path)), exist_ok=True)
        writer.save(output_xml_path)
        return output_xml_path

    @staticmethod
    def save_yolo_txt(
        image_path: str,
        objects: List[Dict[str, Any]],
        output_txt_path: str,
        class_to_id: Dict[str, int]
    ) -> str:
        """
        导出 YOLO TXT 格式标注 (class_id center_x center_y width height)

        :param image_path: 图片路径
        :param objects: 目标框列表
        :param output_txt_path: TXT 文件保存路径
        :param class_to_id: 类别名到 ID 的映射
        """
        if not os.path.exists(image_path):
            return output_txt_path

        with Image.open(image_path) as img:
            img_w, img_h = img.size

        lines = []
        for obj in objects:
            c_name = obj.get("class_name", "")
            if c_name not in class_to_id:
                continue
            
            cid = class_to_id[c_name]
            xmin, ymin, xmax, ymax = obj["bbox"]

            # 归一化中心坐标与宽高
            bw = (xmax - xmin) / img_w
            bh = (ymax - ymin) / img_h
            cx = (xmin + xmax) / 2.0 / img_w
            cy = (ymin + ymax) / 2.0 / img_h

            lines.append(f"{cid} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

        os.makedirs(os.path.dirname(os.path.abspath(output_txt_path)), exist_ok=True)
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        return output_txt_path
