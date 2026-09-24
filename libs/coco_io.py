# -*- coding: utf-8 -*-
import os
import json

JSON_EXT = '.json'

class COCOReader(object):
    def __init__(self, filepath, imagePath=None):
        self.shapes = []
        self.filepath = filepath
        self.verified = False
        self.parse_coco(imagePath)

    def parse_coco(self, imagePath=None):
        if not os.path.isfile(self.filepath):
            return

        try:
            with open(self.filepath, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
        except Exception:
            return

        if not isinstance(data, dict):
            return

        images = data.get("images", [])
        annotations = data.get("annotations", [])
        categories = data.get("categories", [])

        # Category map: id -> name
        cat_map = {}
        for cat in categories:
            cat_map[cat.get("id")] = cat.get("name", str(cat.get("id")))

        target_name = os.path.basename(imagePath).lower() if imagePath else ""

        # Find matching image_id
        matched_image_ids = set()
        if target_name:
            for img in images:
                fn = img.get("file_name", "")
                if fn and os.path.basename(fn).lower() == target_name:
                    matched_image_ids.add(img.get("id"))
        else:
            if images:
                matched_image_ids.add(images[0].get("id"))

        # If no image record matched by name and only 1 image in file, use that image
        if not matched_image_ids and len(images) == 1:
            matched_image_ids.add(images[0].get("id"))

        for anno in annotations:
            img_id = anno.get("image_id")
            if matched_image_ids and img_id not in matched_image_ids:
                continue

            cat_id = anno.get("category_id")
            label = cat_map.get(cat_id, str(cat_id))

            seg = anno.get("segmentation", [])
            # If segmentation has 8 points: [x1, y1, x2, y2, x3, y3, x4, y4] (rotated)
            if isinstance(seg, list) and len(seg) == 1 and isinstance(seg[0], list) and len(seg[0]) == 8:
                pts_flat = seg[0]
                points = [
                    (float(pts_flat[0]), float(pts_flat[1])),
                    (float(pts_flat[2]), float(pts_flat[3])),
                    (float(pts_flat[4]), float(pts_flat[5])),
                    (float(pts_flat[6]), float(pts_flat[7]))
                ]
                import math
                angle = math.atan2(points[1][1] - points[0][1], points[1][0] - points[0][0])
                self.shapes.append((label, points, None, None, False, True, angle, ''))
            else:
                bbox = anno.get("bbox", [])
                if len(bbox) >= 4:
                    xmin = float(bbox[0])
                    ymin = float(bbox[1])
                    w = float(bbox[2])
                    h = float(bbox[3])
                    xmax = xmin + w
                    ymax = ymin + h
                    points = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
                    self.shapes.append((label, points, None, None, False, False, 0.0, ''))

    def getShapes(self):
        def get_shape_info_area(s):
            try:
                pts = s[1]
                if len(pts) >= 2:
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    return (max(xs) - min(xs)) * (max(ys) - min(ys))
            except Exception:
                pass
            return 0.0
        return sorted(self.shapes, key=get_shape_info_area, reverse=True)


class COCOWriter(object):
    def __init__(self, folderName, filename, imgSize):
        self.folderName = folderName
        self.filename = filename
        self.imgSize = imgSize # (height, width, depth)
        self.boxlist = []

    def addBndBox(self, xmin, ymin, xmax, ymax, name, difficult=0, extra=None):
        self.boxlist.append({
            'name': name,
            'isRotated': False,
            'xmin': xmin,
            'ymin': ymin,
            'xmax': xmax,
            'ymax': ymax
        })

    def addRotatedBndBox(self, cx, cy, w, h, angle, name, difficult=0, extra=None):
        self.boxlist.append({
            'name': name,
            'isRotated': True,
            'cx': cx,
            'cy': cy,
            'w': w,
            'h': h,
            'angle': angle
        })

    def save(self, targetFile):
        out_dir = os.path.dirname(os.path.abspath(targetFile))
        os.makedirs(out_dir, exist_ok=True)

        h, w = int(self.imgSize[0]), int(self.imgSize[1])
        categories = []
        cat_to_id = {}
        annotations = []

        import math

        for idx, b in enumerate(self.boxlist):
            name = b['name']
            if name not in cat_to_id:
                cid = len(categories) + 1
                cat_to_id[name] = cid
                categories.append({"id": cid, "name": name, "supercategory": "none"})
            else:
                cid = cat_to_id[name]

            if not b['isRotated']:
                xmin = float(b['xmin'])
                ymin = float(b['ymin'])
                xmax = float(b['xmax'])
                ymax = float(b['ymax'])
                bw = max(0.0, xmax - xmin)
                bh = max(0.0, ymax - ymin)

                annotations.append({
                    "id": idx + 1,
                    "image_id": 1,
                    "category_id": cid,
                    "bbox": [round(xmin, 2), round(ymin, 2), round(bw, 2), round(bh, 2)],
                    "area": round(bw * bh, 2),
                    "segmentation": [],
                    "iscrowd": 0
                })
            else:
                cx = float(b['cx'])
                cy = float(b['cy'])
                bw = float(b['w'])
                bh = float(b['h'])
                angle = float(b['angle'])

                def rot_pt(xp, yp):
                    xoff = xp - cx
                    yoff = yp - cy
                    cosT = math.cos(-angle)
                    sinT = math.sin(-angle)
                    return (cx + cosT * xoff + sinT * yoff, cy - sinT * xoff + cosT * yoff)

                p0 = rot_pt(cx - bw / 2.0, cy - bh / 2.0)
                p1 = rot_pt(cx + bw / 2.0, cy - bh / 2.0)
                p2 = rot_pt(cx + bw / 2.0, cy + bh / 2.0)
                p3 = rot_pt(cx - bw / 2.0, cy + bh / 2.0)

                seg = [round(p0[0], 2), round(p0[1], 2), round(p1[0], 2), round(p1[1], 2),
                       round(p2[0], 2), round(p2[1], 2), round(p3[0], 2), round(p3[1], 2)]

                xs = [p0[0], p1[0], p2[0], p3[0]]
                ys = [p0[1], p1[1], p2[1], p3[1]]
                xmin, xmax = min(xs), max(xs)
                ymin, ymax = min(ys), max(ys)

                annotations.append({
                    "id": idx + 1,
                    "image_id": 1,
                    "category_id": cid,
                    "bbox": [round(xmin, 2), round(ymin, 2), round(xmax - xmin, 2), round(ymax - ymin, 2)],
                    "area": round(bw * bh, 2),
                    "segmentation": [seg],
                    "iscrowd": 0
                })

        coco_data = {
            "images": [
                {
                    "id": 1,
                    "file_name": self.filename,
                    "width": w,
                    "height": h
                }
            ],
            "annotations": annotations,
            "categories": categories
        }

        with open(targetFile, 'w', encoding='utf-8') as f:
            json.dump(coco_data, f, ensure_ascii=False, indent=2)
