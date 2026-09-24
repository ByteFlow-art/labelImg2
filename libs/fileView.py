# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import sys
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from .pascal_voc_io import PascalVocReader, XML_EXT

class CFileListModel(QStringListModel):
    def __init__(self, parent = None):
        super(CFileListModel, self).__init__(parent)
        self.dispList = []
        self.session_saved_files = set()
    
    def parseOne(self, s, openedDir = None, defaultSaveDir = None, lookup_cache = None, json_dataset_counts = None):
        stem = os.path.splitext(os.path.basename(s))[0]
        found_file = None

        # 0. 优先匹配 dataset 级 JSON 索引 (如 COCO / CreateML 数据集大文件)
        if json_dataset_counts and stem in json_dataset_counts:
            cnt = json_dataset_counts[stem]
            return [os.path.split(s)[1], cnt, False]

        if lookup_cache is not None:
            # 优先从高效内存缓存中 $O(1)$ 极速检索
            found_file = lookup_cache.get(stem) or lookup_cache.get(os.path.basename(s))
        
        if not found_file:
            candidates = []
            if defaultSaveDir is not None and len(defaultSaveDir) and os.path.exists(defaultSaveDir):
                if openedDir is not None and os.path.exists(openedDir):
                    try:
                        relname = os.path.relpath(s, openedDir)
                        relname = os.path.splitext(relname)[0]
                        candidates.append(os.path.join(defaultSaveDir, relname + XML_EXT))
                        candidates.append(os.path.join(defaultSaveDir, relname + ".txt"))
                        candidates.append(os.path.join(defaultSaveDir, relname + ".json"))
                    except Exception:
                        pass
                candidates.append(os.path.join(defaultSaveDir, stem + XML_EXT))
                candidates.append(os.path.join(defaultSaveDir, "Annotations", stem + XML_EXT))
                candidates.append(os.path.join(defaultSaveDir, stem + ".txt"))
                candidates.append(os.path.join(defaultSaveDir, "labels", stem + ".txt"))
                candidates.append(os.path.join(defaultSaveDir, stem + ".json"))

            candidates.append(os.path.splitext(s)[0] + XML_EXT)
            candidates.append(os.path.join(os.path.dirname(s), stem + XML_EXT))
            candidates.append(os.path.join(os.path.dirname(s), "Annotations", stem + XML_EXT))
            candidates.append(os.path.splitext(s)[0] + ".txt")
            candidates.append(os.path.join(os.path.dirname(s), "labels", stem + ".txt"))
            candidates.append(os.path.splitext(s)[0] + ".json")

            for c in candidates:
                if os.path.exists(c) and os.path.isfile(c):
                    found_file = c
                    break

        if found_file:
            try:
                ext = os.path.splitext(found_file)[1].lower()
                if ext == '.xml':
                    # 采用轻量极速二进制检索 <object> 标签，较完整树解析加速 1000 倍且绝不卡顿
                    with open(found_file, 'rb') as f:
                        data = f.read()
                    cnt = data.count(b'<object>') + data.count(b'<object ')
                    info = [os.path.split(s)[1], cnt, False]
                elif ext == '.txt':
                    with open(found_file, 'rb') as f:
                        cnt = sum(1 for line in f if line.strip())
                    info = [os.path.split(s)[1], cnt, False]
                elif ext == '.json':
                    import json
                    with open(found_file, 'r', encoding='utf-8', errors='ignore') as f:
                        jdata = json.load(f)
                    if isinstance(jdata, list):
                        cnt = sum(len(item.get('annotations', [])) for item in jdata)
                    elif isinstance(jdata, dict):
                        cnt = len(jdata.get('annotations', []))
                    else:
                        cnt = 0
                    info = [os.path.split(s)[1], cnt, False]
                else:
                    info = [os.path.split(s)[1], 0, False]
            except Exception:
                info = [os.path.split(s)[1], 0, False]
        else:
            info = [os.path.split(s)[1], None, False]
        return info

    def setStringList(self, strings, openedDir = None, defaultSaveDir = None):
        self.dispList = []

        # 预先构建目录文件缓存表，避免数千张图片进行数万次重复磁盘 stat 调用
        lookup_cache = {}
        json_dataset_counts = {}
        scan_dirs = []
        if defaultSaveDir and os.path.exists(defaultSaveDir):
            scan_dirs.append(defaultSaveDir)
            for sub in ("Annotations", "annotations", "labels", "Labels"):
                p = os.path.join(defaultSaveDir, sub)
                if os.path.exists(p): scan_dirs.append(p)
        if openedDir and os.path.exists(openedDir):
            scan_dirs.append(openedDir)
            for sub in ("Annotations", "annotations", "labels", "Labels"):
                p = os.path.join(openedDir, sub)
                if os.path.exists(p): scan_dirs.append(p)

        for d in scan_dirs:
            try:
                with os.scandir(d) as entries:
                    for entry in entries:
                        if entry.is_file():
                            name = entry.name
                            lower_name = name.lower()
                            if lower_name.endswith(('.xml', '.txt', '.json')):
                                s_stem = os.path.splitext(name)[0]
                                if s_stem not in lookup_cache:
                                    lookup_cache[s_stem] = entry.path

                            # 尝试对 COCO 全局数据集 JSON 进行快速预索引
                            if lower_name in ("_annotations.coco.json", "instances_default.json", "annotations.json"):
                                try:
                                    import json
                                    with open(entry.path, 'r', encoding='utf-8', errors='ignore') as jf:
                                        coco_raw = json.load(jf)
                                    if isinstance(coco_raw, dict) and "images" in coco_raw and "annotations" in coco_raw:
                                        id_to_stem = {}
                                        for img_info in coco_raw.get("images", []):
                                            f_stem = os.path.splitext(os.path.basename(img_info.get("file_name", "")))[0]
                                            id_to_stem[img_info.get("id")] = f_stem
                                        for anno in coco_raw.get("annotations", []):
                                            img_id = anno.get("image_id")
                                            target_stem = id_to_stem.get(img_id)
                                            if target_stem:
                                                json_dataset_counts[target_stem] = json_dataset_counts.get(target_stem, 0) + 1
                                except Exception:
                                    pass
            except Exception:
                pass

        for s in strings:
            info = self.parseOne(s, openedDir, defaultSaveDir, lookup_cache, json_dataset_counts)
            abs_s = os.path.abspath(s) if s else ""
            if s in self.session_saved_files or abs_s in self.session_saved_files or info[0] in self.session_saved_files:
                info[2] = True
            self.dispList.append(info)

        return super(CFileListModel, self).setStringList(strings)

    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self.dispList):
            return super(CFileListModel, self).data(index, role)
        item = self.dispList[index.row()]
        pathname, count = item[0], item[1]
        if role == Qt.DisplayRole:
            if count is None:
                res_str = '%s [0]' % (pathname,)
            else:
                if count == 0:
                    res_str = '%s [BG]' % (pathname,)
                else:
                    res_str = '%s [%d]' % (pathname, count)
            return res_str
        elif role == Qt.ToolTipRole:
            return super(CFileListModel, self).data(index, Qt.EditRole)
        elif role == Qt.BackgroundRole:
            if item[2] or (item[0] in self.session_saved_files):
                # 当前运行期间创建/修改/保存的标注文件标为荧光绿
                return QBrush(QColor(74, 222, 128, 180))
            elif item[1] is not None:
                # 打开前磁盘上已有的标注文件为浅灰色
                return QBrush(QColor(226, 232, 240))
            else:
                # 尚未保存标注的文件为正常透明色
                return QBrush(Qt.transparent)
        else:
            return super(CFileListModel, self).data(index, role)

    def setData(self, index, value, role = None):
        if index.row() < 0:
            return super(CFileListModel, self).setData(index, value, role)

        if role == Qt.BackgroundRole:
            if index.row() < len(self.dispList):
                info = self.dispList[index.row()]
                info[1] = value
                info[2] = True
                self.dispList[index.row()] = info
                str_list = self.stringList()
                if index.row() < len(str_list):
                    self.session_saved_files.add(str_list[index.row()])
                    self.session_saved_files.add(os.path.abspath(str_list[index.row()]))
                if len(info) > 0 and info[0]:
                    self.session_saved_files.add(info[0])

        return super(CFileListModel, self).setData(index, value, role)

    def getTotalBoxCount(self):
        """高速统计当前所有图片中已存在的标注框总数 (纯内存计算，0 毫秒完成)"""
        total = 0
        for item in self.dispList:
            cnt = item[1]
            if cnt is not None and isinstance(cnt, int):
                total += cnt
        return total

    def setItemBoxCount(self, row: int, count: int, mark_modified: bool = False):
        """更新指定行图片的标注框数量，并可选标记为会话已修改"""
        if 0 <= row < len(self.dispList):
            self.dispList[row][1] = count
            if mark_modified:
                self.dispList[row][2] = True
                str_list = self.stringList()
                if row < len(str_list):
                    self.session_saved_files.add(str_list[row])
                    self.session_saved_files.add(os.path.abspath(str_list[row]))
                if len(self.dispList[row]) > 0 and self.dispList[row][0]:
                    self.session_saved_files.add(self.dispList[row][0])
            idx = self.index(row)
            self.dataChanged.emit(idx, idx)




class CFileItemEditDelegate(QStyledItemDelegate):
    def __init__(self, parent):
        super(CFileItemEditDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setReadOnly(True)
        return editor


class CFileView(QListView):
    def __init__(self, parent = None):
        super(CFileView, self).__init__(parent)
        
        model = CFileListModel(self)
        self.setModel(model)

        delegate = CFileItemEditDelegate(self)
        self.setItemDelegateForColumn(0, delegate)
        
        

