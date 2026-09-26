# -*- coding: utf-8 -*-
import os
import json
from libs.pascal_voc_io import PascalVocReader, PascalVocWriter, XML_EXT
from libs.yolo_io import YoloReader, YoloWriter, TXT_EXT
from libs.create_ml_io import CreateMLReader, CreateMLWriter
from libs.coco_io import COCOReader, COCOWriter

FORMAT_PASCAL_VOC = "Pascal VOC XML (*.xml)"
FORMAT_YOLO = "YOLO TXT (*.txt)"
FORMAT_CREATE_ML = "Create ML JSON (*.json)"
FORMAT_COCO = "COCO JSON (*.json)"

SUPPORTED_FORMATS = [
    FORMAT_PASCAL_VOC,
    FORMAT_YOLO,
    FORMAT_CREATE_ML,
    FORMAT_COCO
]

def get_format_ext(format_name):
    if not format_name:
        return ".xml"
    fmt = str(format_name).upper()
    if "YOLO" in fmt or ".TXT" in fmt:
        return ".txt"
    elif "CREATE_ML" in fmt or "CREATE ML" in fmt or "COCO" in fmt or ".JSON" in fmt:
        return ".json"
    return ".xml"

def find_annotation_file(image_path, preferred_format=None, save_dir=None, image_dir=None):
    """
    智能兼容探测与当前图片关联的标注文件 (支持 XML、YOLO TXT、CreateML/COCO JSON 以及通用数据集 JSON)
    返回 (found_file_path, detected_format_name)
    """
    if not image_path:
        return None, None

    stem = os.path.splitext(os.path.basename(image_path))[0]
    img_dir = os.path.dirname(os.path.abspath(image_path))
    
    # 候选搜索目录列表
    search_dirs = []
    if save_dir and os.path.exists(save_dir):
        save_dir = os.path.abspath(save_dir)
        if save_dir not in search_dirs:
            search_dirs.append(save_dir)
        for sub in ("Annotations", "annotations", "labels", "Labels"):
            p = os.path.join(save_dir, sub)
            if os.path.exists(p) and p not in search_dirs:
                search_dirs.append(p)

    if img_dir not in search_dirs:
        search_dirs.append(img_dir)
    for sub in ("Annotations", "annotations", "labels", "Labels"):
        p = os.path.join(img_dir, sub)
        if os.path.exists(p) and p not in search_dirs:
            search_dirs.append(p)

    # 兼容父目录同级 labels / Annotations (如 dataset/images 对应 dataset/labels)
    parent_img_dir = os.path.dirname(img_dir)
    if parent_img_dir and os.path.exists(parent_img_dir):
        for sub in ("labels", "Labels", "Annotations", "annotations"):
            p = os.path.join(parent_img_dir, sub)
            if os.path.exists(p) and p not in search_dirs:
                search_dirs.append(p)

    if image_dir and os.path.exists(image_dir):
        image_dir = os.path.abspath(image_dir)
        if image_dir not in search_dirs:
            search_dirs.append(image_dir)
        for sub in ("Annotations", "annotations", "labels", "Labels"):
            p = os.path.join(image_dir, sub)
            if os.path.exists(p) and p not in search_dirs:
                search_dirs.append(p)

    # 计算相对路径 stem (支持多层子目录)
    rel_stems = [stem]
    if image_dir and os.path.exists(image_dir):
        try:
            rel = os.path.relpath(image_path, image_dir)
            rel_stem = os.path.splitext(rel)[0]
            if rel_stem not in rel_stems:
                rel_stems.append(rel_stem)
        except Exception:
            pass

    # 根据 preferred_format 确定扩展名优先级
    ext_priority = [".xml", ".txt", ".json"]
    fmt_upper = str(preferred_format or "").upper()
    if "YOLO" in fmt_upper or ".TXT" in fmt_upper:
        ext_priority = [".txt", ".xml", ".json"]
    elif "CREATE_ML" in fmt_upper or "CREATE ML" in fmt_upper or "COCO" in fmt_upper or ".JSON" in fmt_upper:
        ext_priority = [".json", ".xml", ".txt"]
    elif "VOC" in fmt_upper or "PASCAL" in fmt_upper or ".XML" in fmt_upper:
        ext_priority = [".xml", ".txt", ".json"]

    # 1. 精确匹配单图对应标注文件
    for ext in ext_priority:
        for d in search_dirs:
            for s in rel_stems:
                cand = os.path.join(d, s + ext)
                if os.path.isfile(cand):
                    fmt = identify_file_format(cand, preferred_format)
                    return cand, fmt

    # 2. 检索数据集级别的全局 JSON 文件 (如 _annotations.coco.json, instances_default.json, annotations.json)
    dataset_json_names = [
        "_annotations.coco.json",
        "instances_default.json",
        "instances_train.json",
        "instances_val.json",
        "annotations.json",
        "labels.json",
        "train.json",
        "val.json"
    ]
    for d in search_dirs:
        for jname in dataset_json_names:
            jpath = os.path.join(d, jname)
            if os.path.isfile(jpath):
                fmt = identify_file_format(jpath, preferred_format)
                return jpath, fmt

    return None, None

def identify_file_format(file_path, preferred_format=None):
    """根据文件后缀与内容结构识别标注格式"""
    if not file_path:
        return FORMAT_PASCAL_VOC

    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.xml':
        return FORMAT_PASCAL_VOC
    elif ext == '.txt':
        return FORMAT_YOLO
    elif ext == '.json':
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                snippet = f.read(2048)
            if '"categories"' in snippet and '"images"' in snippet:
                return FORMAT_COCO
            elif '"annotations"' in snippet and '"coordinates"' in snippet:
                return FORMAT_CREATE_ML
            elif '"categories"' in snippet or '"annotations"' in snippet:
                return FORMAT_COCO
        except Exception:
            pass
        if preferred_format in (FORMAT_CREATE_ML, FORMAT_COCO):
            return preferred_format
        return FORMAT_COCO
    return FORMAT_PASCAL_VOC

def read_annotations(file_path, format_name, image_shape, class_list=None, image_path=None):
    """
    通用读取标注文件，统一返回符合 loadLabels 规范的 shapes 列表
    shapes 格式: [(label, points, line_color, fill_color, difficult, isRotated, direction, extra_label), ...]
    """
    if not file_path or not os.path.isfile(file_path):
        return []

    try:
        ext = os.path.splitext(file_path)[1].lower()
        fmt_upper = str(format_name or "").upper()

        # 1. Pascal VOC XML
        if ext == '.xml' or "VOC" in fmt_upper or "PASCAL" in fmt_upper:
            reader = PascalVocReader(file_path)
            return reader.getShapes()

        # 2. YOLO TXT
        elif ext == '.txt' or "YOLO" in fmt_upper:
            reader = YoloReader(file_path, image_shape, classList=class_list)
            return reader.getShapes()

        # 3. JSON (Create ML 或 COCO)
        elif ext == '.json' or "CREATE_ML" in fmt_upper or "COCO" in fmt_upper or "JSON" in fmt_upper:
            detected_fmt = identify_file_format(file_path, format_name)
            if detected_fmt == FORMAT_COCO:
                reader = COCOReader(file_path, imagePath=image_path)
                shapes = reader.getShapes()
                if shapes:
                    return shapes
                ml_reader = CreateMLReader(file_path, imagePath=image_path)
                return ml_reader.getShapes()
            else:
                reader = CreateMLReader(file_path, imagePath=image_path)
                shapes = reader.getShapes()
                if shapes:
                    return shapes
                coco_reader = COCOReader(file_path, imagePath=image_path)
                return coco_reader.getShapes()
    except Exception as e:
        print(f"[AnnotationIO] Error reading {file_path}: {e}")
        return []

    return []

def write_annotations(target_file, format_name, shapes, image_path, image_shape, class_list=None):
    """
    根据选择的标注格式，将标注框导出保存到目标文件
    """
    out_dir = os.path.dirname(os.path.abspath(target_file))
    os.makedirs(out_dir, exist_ok=True)
    filename = os.path.basename(image_path)
    folder_name = os.path.basename(os.path.dirname(image_path))
    fmt_upper = str(format_name or "").upper()

    # 1. YOLO TXT 格式
    if "YOLO" in fmt_upper or ".TXT" in fmt_upper:
        if not target_file.lower().endswith('.txt'):
            target_file = os.path.splitext(target_file)[0] + '.txt'
        writer = YoloWriter(folder_name, filename, image_shape, classList=class_list)
        for s in shapes:
            label = s['label']
            diff = int(s.get('difficult', 0))
            isRot = s.get('isRotated', False)
            if not isRot:
                from libs.labelFile import LabelFile
                bndbox = LabelFile.convertPoints2BndBox(s['points'])
                writer.addBndBox(bndbox[0], bndbox[1], bndbox[2], bndbox[3], label, diff)
            else:
                from libs.labelFile import LabelFile
                robndbox = LabelFile.convertPoints2RotatedBndBox(s)
                writer.addRotatedBndBox(robndbox[0], robndbox[1], robndbox[2], robndbox[3], robndbox[4], label, diff)
        writer.save(target_file, classList=class_list)
        return target_file

    # 2. Create ML JSON 格式
    elif "CREATE_ML" in fmt_upper or "CREATE ML" in fmt_upper:
        if not target_file.lower().endswith('.json'):
            target_file = os.path.splitext(target_file)[0] + '.json'
        writer = CreateMLWriter(folder_name, filename, image_shape)
        for s in shapes:
            label = s['label']
            diff = int(s.get('difficult', 0))
            isRot = s.get('isRotated', False)
            if not isRot:
                from libs.labelFile import LabelFile
                bndbox = LabelFile.convertPoints2BndBox(s['points'])
                writer.addBndBox(bndbox[0], bndbox[1], bndbox[2], bndbox[3], label, diff)
            else:
                from libs.labelFile import LabelFile
                robndbox = LabelFile.convertPoints2RotatedBndBox(s)
                writer.addRotatedBndBox(robndbox[0], robndbox[1], robndbox[2], robndbox[3], robndbox[4], label, diff)
        writer.save(target_file)
        return target_file

    # 3. COCO JSON 格式
    elif "COCO" in fmt_upper:
        if not target_file.lower().endswith('.json'):
            target_file = os.path.splitext(target_file)[0] + '.json'
        writer = COCOWriter(folder_name, filename, image_shape)
        for s in shapes:
            label = s['label']
            diff = int(s.get('difficult', 0))
            isRot = s.get('isRotated', False)
            if not isRot:
                from libs.labelFile import LabelFile
                bndbox = LabelFile.convertPoints2BndBox(s['points'])
                writer.addBndBox(bndbox[0], bndbox[1], bndbox[2], bndbox[3], label, diff)
            else:
                from libs.labelFile import LabelFile
                robndbox = LabelFile.convertPoints2RotatedBndBox(s)
                writer.addRotatedBndBox(robndbox[0], robndbox[1], robndbox[2], robndbox[3], robndbox[4], label, diff)
        writer.save(target_file)
        return target_file

    # 4. 默认 Pascal VOC XML 格式
    else:
        if not target_file.lower().endswith('.xml'):
            target_file = os.path.splitext(target_file)[0] + '.xml'
        writer = PascalVocWriter(folder_name, filename, image_shape, localImgPath=image_path)
        for s in shapes:
            label = s['label']
            diff = int(s.get('difficult', 0))
            isRot = s.get('isRotated', False)
            extra_text = s.get('extra_text', '')
            if not isRot:
                from libs.labelFile import LabelFile
                bndbox = LabelFile.convertPoints2BndBox(s['points'])
                writer.addBndBox(bndbox[0], bndbox[1], bndbox[2], bndbox[3], label, diff, extra_text)
            else:
                from libs.labelFile import LabelFile
                robndbox = LabelFile.convertPoints2RotatedBndBox(s)
                writer.addRotatedBndBox(robndbox[0], robndbox[1], robndbox[2], robndbox[3], robndbox[4], label, diff, extra_text)
        writer.save(target_file)
        return target_file
