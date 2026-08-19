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
    
    def parseOne(self, s, openedDir = None, defaultSaveDir = None):
        candidates = []
        stem = os.path.splitext(os.path.basename(s))[0]
        if defaultSaveDir is not None and len(defaultSaveDir) and os.path.exists(defaultSaveDir):
            if openedDir is not None and os.path.exists(openedDir):
                try:
                    relname = os.path.relpath(s, openedDir)
                    relname = os.path.splitext(relname)[0]
                    candidates.append(os.path.join(defaultSaveDir, relname + XML_EXT))
                except Exception:
                    pass
            candidates.append(os.path.join(defaultSaveDir, stem + XML_EXT))
        candidates.append(os.path.splitext(s)[0] + XML_EXT)
        candidates.append(os.path.join(os.path.dirname(s), stem + XML_EXT))
        candidates.append(os.path.join(os.path.dirname(s), "Annotations", stem + XML_EXT))
        parent_d = os.path.dirname(os.path.dirname(s))
        candidates.append(os.path.join(parent_d, "Annotations", stem + XML_EXT))

        found_xml = None
        for c in candidates:
            if os.path.exists(c) and os.path.isfile(c):
                found_xml = c
                break

        if found_xml:
            try:
                tVocParser = PascalVocReader(found_xml)
                shapes = tVocParser.getShapes()
                info = [os.path.split(s)[1], len(shapes), False]
            except Exception:
                info = [os.path.split(s)[1], 0, False]
        else:
            info = [os.path.split(s)[1], None, False]
        return info

    def setStringList(self, strings, openedDir = None, defaultSaveDir = None):
        self.dispList = []

        for s in strings:
            info = self.parseOne(s, openedDir, defaultSaveDir)
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
        
        

