# -*- coding: utf-8 -*-
import os
import json

JSON_EXT = '.json'

class CreateMLReader(object):
    def __init__(self, filepath, imagePath=None):
        self.shapes = []
        self.filepath = filepath
        self.verified = False
        self.parse_create_ml(imagePath)

    def parse_create_ml(self, imagePath=None):
        if not os.path.isfile(self.filepath):
            return

        try:
            with open(self.filepath, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
        except Exception:
            return

        target_name = os.path.basename(imagePath) if imagePath else ""

        # Support both array of image dicts and single image dict
        if isinstance(data, dict):
            image_records = [data]
        elif isinstance(data, list):
            image_records = data
        else:
            return

        matched_record = None
        if target_name:
            for rec in image_records:
                rec_img = rec.get("image", "")
                if rec_img and os.path.basename(rec_img).lower() == target_name.lower():
                    matched_record = rec
                    break

        if not matched_record and image_records:
            matched_record = image_records[0]

        if not matched_record:
            return

        annotations = matched_record.get("annotations", [])
        for anno in annotations:
            label = anno.get("label", "unspecified")
            coords = anno.get("coordinates", {})
            cx = float(coords.get("x", 0))
            cy = float(coords.get("y", 0))
            w = float(coords.get("width", 0))
            h = float(coords.get("height", 0))

            xmin = max(0.0, cx - w / 2.0)
            ymin = max(0.0, cy - h / 2.0)
            xmax = cx + w / 2.0
            ymax = cy + h / 2.0

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


class CreateMLWriter(object):
    def __init__(self, folderName, filename, imgSize):
        self.folderName = folderName
        self.filename = filename
        self.imgSize = imgSize # (height, width, depth)
        self.boxlist = []

    def addBndBox(self, xmin, ymin, xmax, ymax, name, difficult=0, extra=None):
        self.boxlist.append({
            'name': name,
            'xmin': xmin,
            'ymin': ymin,
            'xmax': xmax,
            'ymax': ymax
        })

    def addRotatedBndBox(self, cx, cy, w, h, angle, name, difficult=0, extra=None):
        # Convert rotated to axis-aligned bounding box for Create ML
        self.boxlist.append({
            'name': name,
            'xmin': cx - w / 2.0,
            'ymin': cy - h / 2.0,
            'xmax': cx + w / 2.0,
            'ymax': cy + h / 2.0
        })

    def save(self, targetFile):
        out_dir = os.path.dirname(os.path.abspath(targetFile))
        os.makedirs(out_dir, exist_ok=True)

        annotations = []
        for b in self.boxlist:
            xmin = float(b['xmin'])
            ymin = float(b['ymin'])
            xmax = float(b['xmax'])
            ymax = float(b['ymax'])
            w = max(0.0, xmax - xmin)
            h = max(0.0, ymax - ymin)
            cx = (xmin + xmax) / 2.0
            cy = (ymin + ymax) / 2.0

            annotations.append({
                "label": b['name'],
                "coordinates": {
                    "x": round(cx, 2),
                    "y": round(cy, 2),
                    "width": round(w, 2),
                    "height": round(h, 2)
                }
            })

        record = {
            "image": self.filename,
            "annotations": annotations
        }

        # Save single or merged array
        data = [record]
        with open(targetFile, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
