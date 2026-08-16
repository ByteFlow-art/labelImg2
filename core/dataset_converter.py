import os
import shutil
import random
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple, Optional
from PIL import Image

class DatasetConverter:
    """
    Pascal VOC (.xml) 标注数据集转 YOLO 标准训练格式转换器
    生成 images/train, images/val, labels/train, labels/val 与 data.yaml
    """

    @staticmethod
    def extract_categories_from_voc_dir(xml_dir: str) -> List[str]:
        """扫描 XML 标注文件夹，提取所有非重复类别名称列表"""
        categories = set()
        if not os.path.exists(xml_dir):
            return []

        for root_dir, _, files in os.walk(xml_dir):
            for file in files:
                if file.lower().endswith(".xml"):
                    xml_path = os.path.join(root_dir, file)
                    try:
                        tree = ET.parse(xml_path)
                        for obj in tree.getroot().findall("object"):
                            c_name = obj.findtext("name", "").strip()
                            if c_name:
                                categories.add(c_name)
                    except Exception:
                        pass

        return sorted(list(categories))

    @staticmethod
    def voc_to_yolo_dataset(
        image_dir: str,
        xml_dir: Optional[str] = None,
        output_dataset_dir: str = "",
        val_ratio: float = 0.2,
        class_list: Optional[List[str]] = None
    ) -> Tuple[str, List[str], int]:
        """
        将图片文件夹与独立的 XML 标注保存文件夹匹配，转换为 YOLO 训练数据集

        :param image_dir: 图片文件夹路径
        :param xml_dir: XML 标注保存文件夹路径（如为空则与 image_dir 相同）
        :param output_dataset_dir: 输出 YOLO 数据集的目录
        :param val_ratio: 验证集比例
        :param class_list: 显式指定的类别列表
        :return: (yaml_file_path, class_list, total_image_count)
        """
        xml_dir = xml_dir if xml_dir and os.path.exists(xml_dir) else image_dir

        if not class_list:
            class_list = DatasetConverter.extract_categories_from_voc_dir(xml_dir)
            if not class_list and xml_dir != image_dir:
                class_list = DatasetConverter.extract_categories_from_voc_dir(image_dir)

        if not class_list:
            raise ValueError(f"在标注文件夹中未扫描到任何有效的 Pascal VOC XML 类别标签！\n(扫描路径: {xml_dir})")

        class_to_id = {c: i for i, c in enumerate(class_list)}

        # 1. 扫描匹配图片与对应的 .xml
        img_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        matched_pairs: List[Tuple[str, str]] = []

        for root_dir, _, files in os.walk(image_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in img_extensions:
                    img_path = os.path.join(root_dir, file)
                    stem = os.path.splitext(file)[0]

                    # 1. 相同目录检查
                    xml_path = os.path.join(root_dir, f"{stem}.xml")
                    if not os.path.exists(xml_path):
                        # 2. XML 根目录平铺检查
                        xml_path = os.path.join(xml_dir, f"{stem}.xml")
                    if not os.path.exists(xml_path):
                        # 3. XML 根目录按相对路径子目录检查
                        rel_dir = os.path.relpath(root_dir, image_dir)
                        xml_path = os.path.join(xml_dir, rel_dir, f"{stem}.xml")

                    if os.path.exists(xml_path):
                        matched_pairs.append((img_path, xml_path))

        if not matched_pairs:
            raise FileNotFoundError(
                f"未能发现匹配的【图片 + .xml】数据对！\n"
                f"图片目录: {image_dir}\n"
                f"XML 目录: {xml_dir}"
            )

        # 打乱随机分割训练集与验证集
        random.seed(42)
        random.shuffle(matched_pairs)

        val_count = int(len(matched_pairs) * val_ratio)
        if val_count == 0 and len(matched_pairs) > 0:
            val_pairs = matched_pairs
            train_pairs = matched_pairs
        else:
            val_pairs = matched_pairs[:val_count]
            train_pairs = matched_pairs[val_count:]

        # 2. 构建目录结构
        images_train_dir = os.path.join(output_dataset_dir, "images", "train")
        images_val_dir = os.path.join(output_dataset_dir, "images", "val")
        labels_train_dir = os.path.join(output_dataset_dir, "labels", "train")
        labels_val_dir = os.path.join(output_dataset_dir, "labels", "val")

        for d in [images_train_dir, images_val_dir, labels_train_dir, labels_val_dir]:
            os.makedirs(d, exist_ok=True)

        total_valid_boxes = 0

        # 3. 处理转换逻辑助手函数
        def process_pairs(pairs: List[Tuple[str, str]], target_img_dir: str, target_lbl_dir: str):
            nonlocal total_valid_boxes
            for img_p, xml_p in pairs:
                filename = os.path.basename(img_p)
                stem = os.path.splitext(filename)[0]

                # 复制图片
                shutil.copy2(img_p, os.path.join(target_img_dir, filename))

                try:
                    tree = ET.parse(xml_p)
                    root = tree.getroot()

                    # 尝试从 XML 中获取图片宽高
                    img_w, img_h = 0, 0
                    size_node = root.find("size")
                    if size_node is not None:
                        img_w = float(size_node.findtext("width", "0"))
                        img_h = float(size_node.findtext("height", "0"))

                    if img_w <= 0 or img_h <= 0:
                        with Image.open(img_p) as img:
                            img_w, img_h = float(img.size[0]), float(img.size[1])

                    txt_lines = []
                    for obj in root.findall("object"):
                        c_name = obj.findtext("name", "").strip()
                        if c_name not in class_to_id:
                            continue

                        cid = class_to_id[c_name]
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
                            continue

                        # 边界裁剪防越界与无效框过滤
                        xmin = max(0.0, min(xmin, img_w))
                        ymin = max(0.0, min(ymin, img_h))
                        xmax = max(0.0, min(xmax, img_w))
                        ymax = max(0.0, min(ymax, img_h))

                        if xmax <= xmin or ymax <= ymin:
                            continue

                        bw = (xmax - xmin) / img_w
                        bh = (ymax - ymin) / img_h
                        cx = (xmin + xmax) / 2.0 / img_w
                        cy = (ymin + ymax) / 2.0 / img_h

                        txt_lines.append(f"{cid} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")
                        total_valid_boxes += 1

                    txt_out_path = os.path.join(target_lbl_dir, f"{stem}.txt")
                    with open(txt_out_path, "w", encoding="utf-8") as f:
                        f.writelines(txt_lines)

                except Exception as e:
                    print(f"Warning: Failed to convert {xml_p}: {str(e)}")

        process_pairs(train_pairs, images_train_dir, labels_train_dir)
        process_pairs(val_pairs, images_val_dir, labels_val_dir)

        abs_path = os.path.abspath(output_dataset_dir).replace('\\', '/')
        yaml_content = f"""# Auto-generated YOLO dataset.yaml
path: {abs_path}
train: images/train
val: images/val

names:
"""
        for cid, cname in enumerate(class_list):
            yaml_content += f"  {cid}: '{cname}'\n"

        yaml_path = os.path.join(output_dataset_dir, "data.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        return yaml_path, class_list, len(matched_pairs)
