# -*- coding: utf-8 -*-
import os
import math

TXT_EXT = '.txt'

class YoloReader(object):
    def __init__(self, filepath, image, classList=None):
        self.shapes = []
        self.filepath = filepath
        self.verified = False
        
        # Determine image dimensions (w, h)
        if hasattr(image, 'width') and hasattr(image, 'height'):
            self.width = image.width()
            self.height = image.height()
        elif isinstance(image, (tuple, list)) and len(image) >= 2:
            self.height = image[0]
            self.width = image[1]
        else:
            self.width = 1
            self.height = 1

        self.classList = self._resolve_class_list(filepath, classList)
        self.parse_yolo()

    def _resolve_class_list(self, filepath, classList=None):
        if classList and len(classList) > 0:
            return list(classList)

        # Check for classes.txt in common directories
        search_dirs = [
            os.path.dirname(filepath),
            os.path.dirname(os.path.dirname(filepath)),
            os.path.join(os.path.dirname(filepath), "..", "labels"),
            os.path.join(os.path.dirname(filepath), "..", "images"),
        ]
        
        for d in search_dirs:
            cf = os.path.join(d, "classes.txt")
            if os.path.isfile(cf):
                try:
                    with open(cf, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = [line.strip() for line in f.readlines() if line.strip()]
                    if lines:
                        return lines
                except Exception:
                    pass

        # Fallback to predefined classes if available
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        predefined = os.path.join(root_dir, "data", "predefined_classes.txt")
        if os.path.isfile(predefined):
            try:
                with open(predefined, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                if lines:
                    return lines
            except Exception:
                pass

        return []

    def parse_yolo(self):
        if not os.path.isfile(self.filepath):
            return

        try:
            with open(self.filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            return

        w = float(self.width)
        h = float(self.height)
        if w <= 0: w = 1.0
        if h <= 0: h = 1.0

        for line in lines:
            parts = line.strip().split()
            if not parts:
                continue

            try:
                class_id = int(float(parts[0]))
            except ValueError:
                continue

            # Resolve label name
            if self.classList and 0 <= class_id < len(self.classList):
                label = self.classList[class_id]
            else:
                label = str(class_id)

            coords = [float(p) for p in parts[1:]]

            # Format 1: 5 values total: class_id cx cy bw bh (normalized or pixel)
            if len(coords) == 4:
                cx, cy, bw, bh = coords
                # If values are <= 1.0, they are normalized; if > 1.0, they might already be pixel values
                if cx <= 1.0 and cy <= 1.0 and bw <= 1.0 and bh <= 1.0:
                    cx *= w
                    cy *= h
                    bw *= w
                    bh *= h

                xmin = max(0.0, cx - bw / 2.0)
                ymin = max(0.0, cy - bh / 2.0)
                xmax = min(w, cx + bw / 2.0)
                ymax = min(h, cy + bh / 2.0)

                points = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
                # (label, points, line_color, fill_color, difficult, isRotated, direction, extra_label)
                self.shapes.append((label, points, None, None, False, False, 0.0, ''))

            # Format 2: 6 values total: class_id cx cy bw bh angle
            elif len(coords) == 5:
                cx, cy, bw, bh, angle = coords
                if cx <= 1.0 and cy <= 1.0 and bw <= 1.0 and bh <= 1.0:
                    cx *= w
                    cy *= h
                    bw *= w
                    bh *= h

                # Calculate 4 rotated points
                p0 = self._rotate_pt(cx, cy, cx - bw / 2.0, cy - bh / 2.0, -angle)
                p1 = self._rotate_pt(cx, cy, cx + bw / 2.0, cy - bh / 2.0, -angle)
                p2 = self._rotate_pt(cx, cy, cx + bw / 2.0, cy + bh / 2.0, -angle)
                p3 = self._rotate_pt(cx, cy, cx - bw / 2.0, cy + bh / 2.0, -angle)
                points = [p0, p1, p2, p3]
                self.shapes.append((label, points, None, None, False, True, angle, ''))

            # Format 3: 9 values total: class_id x1 y1 x2 y2 x3 y3 x4 y4 (YOLO OBB 8-points)
            elif len(coords) == 8:
                x1, y1, x2, y2, x3, y3, x4, y4 = coords
                if max(x1, x2, x3, x4) <= 1.0 and max(y1, y2, y3, y4) <= 1.0:
                    x1 *= w; x2 *= w; x3 *= w; x4 *= w
                    y1 *= h; y2 *= h; y3 *= h; y4 *= h
                points = [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]
                # Calculate angle of edge 0->1
                angle = math.atan2(y2 - y1, x2 - x1)
                self.shapes.append((label, points, None, None, False, True, angle, ''))

    def _rotate_pt(self, xc, yc, xp, yp, theta):
        xoff = xp - xc
        yoff = yp - yc
        cosTheta = math.cos(theta)
        sinTheta = math.sin(theta)
        return (xc + cosTheta * xoff + sinTheta * yoff, yc - sinTheta * xoff + cosTheta * yoff)

    def getShapes(self):
        # Sort by area descending so large boxes are on bottom, small on top
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


class YoloWriter(object):
    def __init__(self, folderName, filename, imgSize, classList=None):
        self.folderName = folderName
        self.filename = filename
        self.imgSize = imgSize # (height, width, depth)
        self.classList = list(classList) if classList else []
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

    def save(self, targetFile, classList=None):
        if classList:
            self.classList = list(classList)

        # Ensure all box classes exist in classList
        for b in self.boxlist:
            if b['name'] not in self.classList:
                self.classList.append(b['name'])

        h, w = float(self.imgSize[0]), float(self.imgSize[1])
        if w <= 0: w = 1.0
        if h <= 0: h = 1.0

        lines = []
        for b in self.boxlist:
            name = b['name']
            class_id = self.classList.index(name) if name in self.classList else 0

            if not b['isRotated']:
                xmin = float(b['xmin'])
                ymin = float(b['ymin'])
                xmax = float(b['xmax'])
                ymax = float(b['ymax'])

                cx = (xmin + xmax) / 2.0 / w
                cy = (ymin + ymax) / 2.0 / h
                bw = (xmax - xmin) / w
                bh = (ymax - ymin) / h

                # Clip normalized values
                cx = max(0.0, min(1.0, cx))
                cy = max(0.0, min(1.0, cy))
                bw = max(0.0, min(1.0, bw))
                bh = max(0.0, min(1.0, bh))

                lines.append(f"{class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")
            else:
                # OBB format: class_id x1 y1 x2 y2 x3 y3 x4 y4
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

                pts_norm = [
                    p0[0] / w, p0[1] / h,
                    p1[0] / w, p1[1] / h,
                    p2[0] / w, p2[1] / h,
                    p3[0] / w, p3[1] / h,
                ]
                pts_str = " ".join([f"{p:.6f}" for p in pts_norm])
                lines.append(f"{class_id} {pts_str}\n")

        # Save target TXT
        out_dir = os.path.dirname(os.path.abspath(targetFile))
        os.makedirs(out_dir, exist_ok=True)
        with open(targetFile, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        # Do not automatically litter/overwrite classes.txt in the dataset label directory on every image save
