# -*- coding: utf-8 -*-
"""
Smart Bounding Box Detector (智能点选自动成框算法)
借鉴 LabelQuick 的单点点击自动识别轮廓成框思想，结合 YOLO 检测吸附与 OpenCV 快速图像轮廓感知：
1. 优先检测当前点击点是否落在 YOLO 模型预测的目标框内（AI 智能吸附与分类）；
2. 离线/无模型模式下，使用自适应边缘分割与连通域轮廓分析，毫秒级计算点击物体的最小外接矩形框。
"""

import cv2
import numpy as np


def find_yolo_box_at_point(point, candidate_boxes):
    """
    检查点击坐标是否落在已有的候选 YOLO 框内
    point: (x, y)
    candidate_boxes: list of dict {'box': [xmin, ymin, xmax, ymax], 'label': str, 'score': float}
    """
    if not candidate_boxes:
        return None

    px, py = point
    matched = []
    for item in candidate_boxes:
        b = item['box']
        xmin, ymin, xmax, ymax = b[0], b[1], b[2], b[3]
        if xmin <= px <= xmax and ymin <= py <= ymax:
            area = (xmax - xmin) * (ymax - ymin)
            matched.append((area, item))

    if matched:
        # 优先返回面积较小（更紧密贴合物体）或置信度较高的候选框
        matched.sort(key=lambda x: x[0])
        return matched[0][1]
    return None


def detect_contour_bbox(image_bgr, click_point, roi_radius=120):
    """
    基于 OpenCV 快速轮廓与边缘检测，从点击点推断物体的外接矩形框 (xmin, ymin, xmax, ymax)
    """
    if image_bgr is None or image_bgr.size == 0:
        return None

    h, w = image_bgr.shape[:2]
    cx, cy = int(round(click_point[0])), int(round(click_point[1]))
    cx = max(0, min(w - 1, cx))
    cy = max(0, min(h - 1, cy))

    # 1. 确定局部感兴趣区域 (ROI)，避免全图大范围噪声干扰，极大提高响应速度 (<5ms)
    x1 = max(0, cx - roi_radius)
    y1 = max(0, cy - roi_radius)
    x2 = min(w, cx + roi_radius)
    y2 = min(h, cy + roi_radius)

    roi = image_bgr[y1:y2, x1:x2]
    if roi.size == 0:
        return None

    local_cx = cx - x1
    local_cy = cy - y1

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 2. 多重阈值融合提取边缘
    # 方法 A: Canny 边缘检测
    v = np.median(blurred)
    sigma = 0.33
    lower = int(max(0, (1.0 - sigma) * v))
    upper = int(min(255, (1.0 + sigma) * v))
    edges = cv2.Canny(blurred, lower, upper)

    # 膨胀闭合断开的边缘
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    # 方法 B: 漫水填充 / 区域生长 (FloodFill) 捕捉连通颜色区域
    mask_flood = np.zeros((roi.shape[0] + 2, roi.shape[1] + 2), np.uint8)
    flood_flags = 4 | cv2.FLOODFILL_MASK_ONLY | (255 << 8)
    lo_diff = (18, 18, 18)
    up_diff = (18, 18, 18)
    try:
        cv2.floodFill(roi.copy(), mask_flood, (local_cx, local_cy), 255, lo_diff, up_diff, flood_flags)
        flood_roi = mask_flood[1:-1, 1:-1]
    except Exception:
        flood_roi = np.zeros_like(gray)

    # 融合边缘与颜色连通域
    combined = cv2.bitwise_or(closed, flood_roi)

    # 查找所有外轮廓
    contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_box = None
    min_dist = float('inf')

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 64:  # 忽略极小杂质噪点
            continue

        rx, ry, rw, rh = cv2.boundingRect(cnt)
        # 检查是否包含点击点，或点击点在边界附近
        contains = (rx - 4 <= local_cx <= rx + rw + 4) and (ry - 4 <= local_cy <= ry + rh + 4)
        if contains:
            # 还原到全图绝对坐标
            abs_xmin = max(0, x1 + rx)
            abs_ymin = max(0, y1 + ry)
            abs_xmax = min(w, x1 + rx + rw)
            abs_ymax = min(h, y1 + ry + rh)

            box_w = abs_xmax - abs_xmin
            box_h = abs_ymax - abs_ymin

            # 过滤异常过小或全屏的情况
            if 15 <= box_w <= w * 0.95 and 15 <= box_h <= h * 0.95:
                # 优先选择离中心较近且面积合理的框
                center_dist = abs((rx + rw / 2.0) - local_cx) + abs((ry + rh / 2.0) - local_cy)
                if center_dist < min_dist:
                    min_dist = center_dist
                    best_box = (abs_xmin, abs_ymin, abs_xmax, abs_ymax)

    # 方法 C: GrabCut 交互式图割分割 (对齐 LabelQuick 交互分割与智能抠图外接矩形)
    if best_box is None:
        try:
            rw_h, rw_w = roi.shape[:2]
            gc_mask = np.full((rw_h, rw_w), cv2.GC_BGD, dtype=np.uint8)
            pad = min(rw_w, rw_h) // 3
            gc_x1 = max(0, local_cx - pad)
            gc_y1 = max(0, local_cy - pad)
            gc_x2 = min(rw_w, local_cx + pad)
            gc_y2 = min(rw_h, local_cy + pad)
            gc_mask[gc_y1:gc_y2, gc_x1:gc_x2] = cv2.GC_PR_FGD
            seed_r = max(2, min(rw_w, rw_h) // 25)
            gc_mask[max(0, local_cy-seed_r):min(rw_h, local_cy+seed_r),
                    max(0, local_cx-seed_r):min(rw_w, local_cx+seed_r)] = cv2.GC_FGD

            bgd_model = np.zeros((1, 65), np.float64)
            fgd_model = np.zeros((1, 65), np.float64)
            cv2.grabCut(roi, gc_mask, None, bgd_model, fgd_model, 2, cv2.GC_INIT_WITH_MASK)
            gc_fg = np.where((gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
            gc_cnts, _ = cv2.findContours(gc_fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in gc_cnts:
                if cv2.contourArea(cnt) < 64:
                    continue
                rx, ry, rw, rh = cv2.boundingRect(cnt)
                if rx - 2 <= local_cx <= rx + rw + 2 and ry - 2 <= local_cy <= ry + rh + 2:
                    abs_xmin = max(0, x1 + rx)
                    abs_ymin = max(0, y1 + ry)
                    abs_xmax = min(w, x1 + rx + rw)
                    abs_ymax = min(h, y1 + ry + rh)
                    if abs_xmax - abs_xmin >= 15 and abs_ymax - abs_ymin >= 15:
                        best_box = (abs_xmin, abs_ymin, abs_xmax, abs_ymax)
                        break
        except Exception:
            pass

    # 兜底：如果复合边缘检测未找到合适闭合轮廓，采用 Otsu 局部二值化做最终提取
    if best_box is None:
        _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(otsu, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            rx, ry, rw, rh = cv2.boundingRect(cnt)
            if rx <= local_cx <= rx + rw and ry <= local_cy <= ry + rh:
                abs_xmin = max(0, x1 + rx)
                abs_ymin = max(0, y1 + ry)
                abs_xmax = min(w, x1 + rx + rw)
                abs_ymax = min(h, y1 + ry + rh)
                if abs_xmax - abs_xmin >= 15 and abs_ymax - abs_ymin >= 15:
                    best_box = (abs_xmin, abs_ymin, abs_xmax, abs_ymax)
                    break

    # 最后的默认兜底：以点击点为中心提供自适应初始尺寸，防止落空
    if best_box is None:
        default_hw = 40
        abs_xmin = max(0, cx - default_hw)
        abs_ymin = max(0, cy - default_hw)
        abs_xmax = min(w, cx + default_hw)
        abs_ymax = min(h, cy + default_hw)
        best_box = (abs_xmin, abs_ymin, abs_xmax, abs_ymax)

    return best_box


def smart_snap_bbox(image_input, click_point, yolo_model=None):
    """
    智能成框融合引擎：
    优先执行 YOLO 候选框吸附；若无模型或未命中，毫秒级运行 OpenCV 轮廓与边缘收敛
    image_input: str 路径或 np.ndarray
    click_point: (x, y) 像素坐标
    yolo_model: 可选的 YOLO 模型实例
    返回: ((xmin, ymin, xmax, ymax), cls_name, confidence) 或 None
    """
    import os
    if isinstance(image_input, str):
        if not os.path.exists(image_input):
            return None
        # 支持 Windows 中文路径安全加载
        try:
            img_bgr = cv2.imdecode(np.fromfile(image_input, dtype=np.uint8), cv2.IMREAD_COLOR)
        except Exception:
            img_bgr = cv2.imread(image_input)
    else:
        img_bgr = image_input

    if img_bgr is None or img_bgr.size == 0:
        return None

    px, py = float(click_point[0]), float(click_point[1])

    # 1. 尝试 AI YOLO 模型候选吸附
    if yolo_model is not None:
        try:
            results = yolo_model(img_bgr, verbose=False)
            candidate_boxes = []
            for r in results:
                if hasattr(r, 'boxes') and r.boxes is not None:
                    for box in r.boxes:
                        xyxy = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].cpu().numpy())
                        cls_id = int(box.cls[0].cpu().numpy())
                        cls_name = r.names[cls_id] if hasattr(r, 'names') and cls_id in r.names else str(cls_id)
                        candidate_boxes.append({
                            'box': [float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])],
                            'label': cls_name,
                            'score': conf
                        })
            matched = find_yolo_box_at_point((px, py), candidate_boxes)
            if matched:
                b = matched['box']
                return (int(round(b[0])), int(round(b[1])), int(round(b[2])), int(round(b[3]))), matched['label'], matched['score']
        except Exception:
            pass

    # 2. 边缘与轮廓感知
    contour_box = detect_contour_bbox(img_bgr, (px, py))
    if contour_box:
        xmin, ymin, xmax, ymax = contour_box
        return (int(xmin), int(ymin), int(xmax), int(ymax)), "", 0.0

    return None
