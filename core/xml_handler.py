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
        生成并保存 Pascal VOC .xml 文件

        :param image_path: 图片完整路径
        :param objects: 目标标注框列表 [{'class_name': str, 'bbox': [xmin, ymin, xmax, ymax], ...}, ...]
        :param output_xml_path: 导出的 XML 文件路径
        :param class_mapping: 类别重命名映射表 {original_name: mapped_name}
        :param overwrite: 是否覆盖已有 XML 标注（如果为 False，则与已有 XML 内容合并）
        :return: 保存后的 XML 路径
        """
        class_mapping = class_mapping or {}

        # 获取图片实际像素大小
        if os.path.exists(image_path):
            with Image.open(image_path) as img:
                width, height = img.size
                mode = img.mode
                depth = 3 if mode == 'RGB' else (1 if mode == 'L' else 4)
        else:
            width, height, depth = 0, 0, 3

        folder_name = os.path.basename(os.path.dirname(image_path))
        filename_val = os.path.basename(image_path)

        final_objects = []
        if not overwrite and os.path.exists(output_xml_path):
            try:
                _, existing_objs = XMLHandler.read_pascal_voc_xml(output_xml_path)
                final_objects.extend(existing_objs)
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
            new_box = new_obj.get("bbox", [0, 0, 0, 0])
            new_cls = new_obj.get("class_name", "")
            # 检查是否与已有目标高度重叠 (IoU > 0.85 且类别相同)
            is_dup = False
            for exist_obj in final_objects:
                exist_box = exist_obj.get("bbox", [0, 0, 0, 0])
                exist_cls = exist_obj.get("class_name", "")
                if new_cls == exist_cls and calc_box_iou(new_box, exist_box) > 0.85:
                    is_dup = True
                    break
            if not is_dup:
                final_objects.append(new_obj)


        # 面积排序：面积大的置于底层(先写入XML)，面积小的置于顶层(后写入XML)
        def get_box_area(obj):
            try:
                b = obj.get("bbox", [0, 0, 0, 0])
                w = max(0.0, float(b[2]) - float(b[0]))
                h = max(0.0, float(b[3]) - float(b[1]))
                return w * h
            except Exception:
                return 0.0
        final_objects = sorted(final_objects, key=get_box_area, reverse=True)

        annotation = ET.Element("annotation")
        
        folder_elem = ET.SubElement(annotation, "folder")
        folder_elem.text = folder_name

        filename_elem = ET.SubElement(annotation, "filename")
        filename_elem.text = filename_val

        path_elem = ET.SubElement(annotation, "path")
        path_elem.text = os.path.abspath(image_path)

        source_elem = ET.SubElement(annotation, "source")
        database_elem = ET.SubElement(source_elem, "database")
        database_elem.text = "Unknown"

        size_elem = ET.SubElement(annotation, "size")
        w_elem = ET.SubElement(size_elem, "width")
        w_elem.text = str(width)
        h_elem = ET.SubElement(size_elem, "height")
        h_elem.text = str(height)
        d_elem = ET.SubElement(size_elem, "depth")
        d_elem.text = str(depth)

        seg_elem = ET.SubElement(annotation, "segmented")
        seg_elem.text = "0"

        for obj in final_objects:
            raw_name = obj.get("class_name", "object")
            # 应用类别名称映射
            final_name = class_mapping.get(raw_name, raw_name)

            bbox = obj.get("bbox", [0, 0, 0, 0])
            xmin, ymin, xmax, ymax = bbox[0], bbox[1], bbox[2], bbox[3]

            # 坐标点防边界溢出与整形转换
            xmin = max(0, min(int(round(xmin)), width))
            ymin = max(0, min(int(round(ymin)), height))
            xmax = max(0, min(int(round(xmax)), width))
            ymax = max(0, min(int(round(ymax)), height))

            if xmax <= xmin or ymax <= ymin:
                continue  # 忽略非法无效框

            obj_elem = ET.SubElement(annotation, "object")
            
            name_elem = ET.SubElement(obj_elem, "name")
            name_elem.text = str(final_name)

            pose_elem = ET.SubElement(obj_elem, "pose")
            pose_elem.text = obj.get("pose", "Unspecified")

            trunc_elem = ET.SubElement(obj_elem, "truncated")
            trunc_elem.text = str(obj.get("truncated", 0))

            diff_elem = ET.SubElement(obj_elem, "difficult")
            diff_elem.text = str(obj.get("difficult", 0))

            bndbox_elem = ET.SubElement(obj_elem, "bndbox")
            
            xmin_elem = ET.SubElement(bndbox_elem, "xmin")
            xmin_elem.text = str(xmin)
            ymin_elem = ET.SubElement(bndbox_elem, "ymin")
            ymin_elem.text = str(ymin)
            xmax_elem = ET.SubElement(bndbox_elem, "xmax")
            xmax_elem.text = str(xmax)
            ymax_elem = ET.SubElement(bndbox_elem, "ymax")
            ymax_elem.text = str(ymax)

        # 格式化 XML 树（美化缩进）
        rough_string = ET.tostring(annotation, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="    ", encoding="utf-8")

        # 确保输出目录存在
        os.makedirs(os.path.dirname(os.path.abspath(output_xml_path)), exist_ok=True)
        with open(output_xml_path, "wb") as f:
            f.write(pretty_xml)

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
