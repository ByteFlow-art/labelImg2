#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import

import codecs
import os
import platform
import re
import sys

# Ensure application root directory is at the head of sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import subprocess
import math
import traceback
import xml.etree.ElementTree as ET
from functools import partial
from collections import defaultdict, OrderedDict

# -------------------------------------------------------------
# Global Crash Interceptor (Windows 原生防闪退弹窗拦截网)
# -------------------------------------------------------------
def _native_crash_handler(exc_type, exc_value, exc_tb):
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        sys.stderr.write(tb_str + "\n")
        sys.stderr.flush()
    except Exception:
        pass
    if platform.system() == 'Windows':
        try:
            import ctypes
            err_title = "LabelImg2 启动异常"
            err_content = (
                f"LabelImg2 在启动或运行过程中捕获到异常：\n\n"
                f"【异常类型】{exc_type.__name__}\n"
                f"【错误信息】{exc_value}\n\n"
                f"【可能原因】\n"
                f"1. 缺少核心运行依赖库（如 PyQt5 / OpenCV / Pillow / lxml / pyyaml 等）；\n"
                f"2. 请在软件安装目录下双击运行 'setup_env.bat' 自动配置/修复运行环境。\n\n"
                f"详细异常调用栈 (前 1000 字符)：\n{tb_str[:1000]}"
            )
            ctypes.windll.user32.MessageBoxW(0, err_content, err_title, 0x10)
        except Exception:
            pass

sys.excepthook = _native_crash_handler

try:
    import yaml
except ImportError:
    yaml = None

try:
    import yamlloader
except ImportError:
    yamlloader = None

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QCollator, QLocale

# Add internal libs
from libs.constants import *
from libs.lib import struct, newAction, newIcon, addActions, fmtShortcut, generateColorByText
from libs.settings import Settings
from libs.shape import Shape, DEFAULT_LINE_COLOR, DEFAULT_FILL_COLOR
from libs.canvas import Canvas
from libs.zoomWidget import ZoomWidget
from libs.labelDialog import LabelDialog
from libs.labelFile import LabelFile, LabelFileError
from libs.pascal_voc_io import PascalVocReader, XML_EXT

from libs.labelView import CLabelView, HashableQStandardItem
from libs.fileView import CFileView
from libs.cvtlabels2yolo import cvt_lbidata_rotdet
from libs.toggle_switch import SwitchButton

from utils.folder_sort_sync import sort_images_by_folder_order, natural_sort_key

__appname__ = 'labelImg2'

import time
import collections

class TerminalLogger:
    def __init__(self, max_history=100):
        self.history = collections.deque(maxlen=max_history)
        self.last_msg = ""
        self.last_time = 0.0

    def log(self, msg):
        now = time.time()
        # 避免 100ms 内完全相同的日志重复刷屏
        if msg == self.last_msg and (now - self.last_time) < 0.15:
            return
        self.last_msg = msg
        self.last_time = now
        self.history.append(msg)
        try:
            print(msg, flush=True)
        except Exception:
            pass

terminal_logger = TerminalLogger(max_history=100)

def log_terminal(msg):
    terminal_logger.log(msg)

# Utility functions and classes.

def have_qstring():
    '''p3/qt5 get rid of QString wrapper as py3 has native unicode str type'''
    return not (sys.version_info.major >= 3 or QT_VERSION_STR.startswith('5.'))

def util_qt_strlistclass():
    return QStringList if have_qstring() else list


class WindowMixin(object):

    def menu(self, title, actions=None):
        menu = self.menuBar().addMenu(title)
        if actions:
            addActions(menu, actions)
        return menu

    def toolbar(self, title, actions=None):
        toolbar = QToolBar(title)
        toolbar.setObjectName(u'%sToolBar' % title)
        if actions:
            if isinstance(action, QWidgetAction):
                return super(ToolBar, self).addAction(action)
            btn = QToolButton()
            btn.setDefaultAction(action)
            btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
            toolbar.addWidget(btn)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        return toolbar


def detect_project_folders(project_root):
    """
    智能自动识别项目总文件夹下的图片路径与标签路径 (支持重叠多层子目录嵌套):
    - 图片路径优先识别: images, image, imgs, img, JPEGImages, photos, raw_images 等总目录
      不提前钻入单一子目录 (如 train)，确保全量扫描选中目录下的所有图片
    - 标签路径优先识别: labels, label, Annotations, annotations 等总目录
    - 若无独立子目录，直接以项目根目录为图片路径并自动关联/创建 labels 目录
    返回 (found_images_dir, found_labels_dir)
    """
    if not project_root or not os.path.isdir(project_root):
        return None, None

    project_root = os.path.abspath(project_root)
    img_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff', '.gif'}
    label_exts = {'.xml', '.txt', '.json'}

    image_dir_candidates = [
        'images', 'image', 'imgs', 'img', 'JPEGImages', 'photos', 'raw_images',
        os.path.join('data', 'images')
    ]
    label_dir_candidates = [
        'labels', 'label', 'Annotations', 'annotations', 'Labels', 'xml', 'txt',
        os.path.join('data', 'labels')
    ]

    found_img_dir = None
    found_lbl_dir = None

    # 辅助函数：判断目录树中（含各级子目录）是否包含图片文件
    def folder_has_images(folder_p):
        if not os.path.isdir(folder_p):
            return False
        for _, _, files in os.walk(folder_p):
            if any(os.path.splitext(f)[1].lower() in img_exts for f in files):
                return True
        return False

    # 1. 优先查找专有图片总文件夹 (如 images / img)
    for cand in image_dir_candidates:
        cand_p = os.path.join(project_root, cand)
        if os.path.isdir(cand_p) and folder_has_images(cand_p):
            found_img_dir = cand_p
            break

    # 若未找到专有图片文件夹，检查项目根目录本身及子目录是否包含图片
    if not found_img_dir and folder_has_images(project_root):
        found_img_dir = project_root

    # 2. 查找标签总目录
    for cand in label_dir_candidates:
        cand_p = os.path.join(project_root, cand)
        if os.path.isdir(cand_p):
            found_lbl_dir = cand_p
            break

    if not found_lbl_dir:
        try:
            if any(os.path.splitext(f)[1].lower() in label_exts and f.lower() != 'classes.txt' for f in os.listdir(project_root) if os.path.isfile(os.path.join(project_root, f))):
                found_lbl_dir = project_root
        except Exception:
            pass

    if not found_lbl_dir:
        labels_default = os.path.join(project_root, 'labels')
        try:
            os.makedirs(labels_default, exist_ok=True)
            found_lbl_dir = labels_default
        except Exception:
            found_lbl_dir = found_img_dir or project_root

    if not found_img_dir:
        found_img_dir = project_root

    return found_img_dir, found_lbl_dir


class MainWindow(QMainWindow, WindowMixin):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = list(range(3))

    def __init__(self, defaultFilename=None, defaultPrefdefClassFile=None, defaultSaveDir=None):
        super(MainWindow, self).__init__()
        self.setWindowTitle(__appname__)

        # Load setting in the main thread
        self.settings = Settings()
        self.settings.load()
        settings = self.settings

        # Save as Pascal voc xml
        self.defaultSaveDir = defaultSaveDir

        # For loading all image under a directory
        self.dirname = None
        self.labelHist = []
        self.lastOpenDir = None

        # Whether we need to save or not.
        self.dirty = False

        self.back_sample = False

        self._noSelectionSlot = False

        # Load predefined classes to the list
        self.loadPredefinedClasses(defaultPrefdefClassFile)

        # Main widgets and related state.
        self.labelDialog = LabelDialog(parent=self, listItem=self.labelHist, currentFile=getattr(self, 'current_label_file', None))
        self.labelDialog.labels_applied.connect(self.on_labels_applied)

        self.ShapeItemDict = {}
        self.ItemShapeDict = {}

        labellistLayout = QVBoxLayout()
        labellistLayout.setContentsMargins(0, 0, 0, 0)

        self.default_label = self.labelHist[0] if (self.labelHist and len(self.labelHist) > 0) else "object"

        # 标注框旋转与长宽微调按键并发状态管理 (ZV 与 XC 同时启动互不冲突，动态变速调节)
        self._active_adjust_keys = set()
        self._adjust_timer = QTimer(self)
        self._adjust_timer.setInterval(30)
        self._adjust_timer.timeout.connect(self._on_adjust_timer_tick)
        self._size_start_time = None
        self._size_last_time = 0.0

        # Create a widget for edit and diffc button
        self.diffcButton = QCheckBox(u'difficult')
        self.diffcButton.setChecked(False)
        self.diffcButton.stateChanged.connect(self.btnstate)
        self.editButton = QToolButton()
        self.editButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        labellistLayout.addWidget(self.editButton)
        labellistLayout.addWidget(self.diffcButton)

        # Create and add a widget for showing current label items
        labelListContainer = QWidget()
        labelListContainer.setLayout(labellistLayout)

        self.labelList = CLabelView(self.labelHist)
        self.labelModel = self.labelList.model()
        self.labelModel.dataChanged.connect(self.labelDataChanged)
        
        self.labelList.extraEditing.connect(self.updateLabelShowing)

        self.labelsm = self.labelList.selectionModel()
        self.labelsm.currentChanged.connect(self.labelCurrentChanged)

        myHeader = self.labelList.verticalHeader()
        myHeader.clicked.connect(self.labelHeaderClicked)


        labellistLayout.addWidget(self.labelList)

        self.dock = QDockWidget(u'Box Labels', self)
        self.dock.setObjectName(u'Labels')
        self.dock.setWidget(labelListContainer)

        self.labelList.toggleEdit.connect(self.toggleExtraEditing)

        self.fileListView = CFileView()
        self.fileModel = self.fileListView.model()
        self.filesm = self.fileListView.selectionModel()
        self.filesm.currentChanged.connect(self.fileCurrentChanged)

        # 监控文件夹变动，确保外部增删修改图片时自动刷新照片栏与视图
        self.dir_watcher = QFileSystemWatcher(self)
        self.dir_watcher.directoryChanged.connect(self.on_directory_changed)

        filelistLayout = QVBoxLayout()
        filelistLayout.setContentsMargins(0, 0, 0, 0)
        filelistLayout.setSpacing(0)

        self.prevButton = QToolButton()
        self.nextButton = QToolButton()
        self.playButton = QToolButton()
        self.prevButton.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.nextButton.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.playButton.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self.controlButtonsLayout = QHBoxLayout()
        self.controlButtonsLayout.setAlignment(Qt.AlignLeft)
        self.controlButtonsLayout.setContentsMargins(4, 2, 4, 2)
        self.controlButtonsLayout.setSpacing(4)
        self.controlButtonsLayout.addWidget(self.prevButton)
        self.controlButtonsLayout.addWidget(self.nextButton)
        self.controlButtonsLayout.addWidget(self.playButton)

        self.controlButtonsLayout.addStretch()

        # 上方控制栏右侧统计: 本次打开工具新增标签数 与 所有已有标签总数
        self.lbl_session_count = QLabel("本次: +0")
        self.lbl_session_count.setStyleSheet("font-size: 11px; font-weight: bold; color: #15803D; background: #DCFCE7; padding: 2px 5px; border-radius: 3px; border: 1px solid #86EFAC;")
        self.lbl_session_count.setToolTip("本次打开工具期间累计新增的标注框数量")
        self.controlButtonsLayout.addWidget(self.lbl_session_count)

        self.lbl_total_count = QLabel("总计: 0")
        self.lbl_total_count.setStyleSheet("font-size: 11px; font-weight: bold; color: #1D4ED8; background: #DBEAFE; padding: 2px 5px; border-radius: 3px; border: 1px solid #93C5FD;")
        self.lbl_total_count.setToolTip("当前项目所有图片中已存在的标注框总数")
        self.controlButtonsLayout.addWidget(self.lbl_total_count)

        filelistLayout.addLayout(self.controlButtonsLayout)
        filelistLayout.addWidget(self.fileListView)

        fileListContainer = QWidget()
        fileListContainer.setLayout(filelistLayout)

        self.filedock = QDockWidget(u'File List', self)
        self.filedock.setObjectName(u'Files')
        self.filedock.setWidget(fileListContainer)

        # 统计数据缓存与追踪 (支持项目已有标签及每次打开新增计数)
        self._baseline_box_counts = {}
        self._session_added_map = {}
        self._xml_stats_cache = {}



        self.zoomWidget = ZoomWidget()

        scroll = QScrollArea()
        self.canvas = Canvas(parent=scroll)
        self.canvas.zoomRequest.connect(self.zoomRequest)

        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(True)
        self.scrollBars = {
            Qt.Vertical: scroll.verticalScrollBar(),
            Qt.Horizontal: scroll.horizontalScrollBar()
        }
        self.scrollArea = scroll
        self.canvas.scrollRequest.connect(self.scrollRequest)

        self.canvas.newShape.connect(self.newShape)
        self.canvas.beforeShapeModified.connect(self.save_undo_state)
        self.canvas.shapeMoved.connect(self.setDirty)
        self.canvas.selectionChanged.connect(self.shapeSelectionChanged)
        self.canvas.singleClickSelected.connect(self.auto_expand_label_editor)
        self.canvas.drawingPolygon.connect(self.toggleDrawingSensitive)
        self.canvas.cancelDraw.connect(self.createCancel)
        self.canvas.toggleEdit.connect(self.toggleExtraEditing)
        self.canvas.deleteRequested.connect(self.deleteSelectedShape)
        self.canvas.undoRedoRequested.connect(self.toggle_undo_redo)

        self.setCentralWidget(scroll)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.filedock)
        self.dock.setFeatures(QDockWidget.DockWidgetFloatable)
        self.filedock.setFeatures(QDockWidget.DockWidgetFloatable)

        self.displayTimer = QTimer(self)
        self.displayTimer.setInterval(1000)
        self.displayTimer.timeout.connect(self.autoNext)

        self.playing = False

        self.save_format = settings.get('save_format', 'Pascal VOC XML (*.xml)')

        # Actions
        action = partial(newAction, self)
        quit = action('&Quit', self.close,
                      'Ctrl+Q', 'power.svg', u'Quit application')

        openDir = action('&Open Dir', self.openProjectDialog,
                         'Ctrl+O', 'icon_open_file.svg', u'Open project root directory (auto-detect all images and labels recursively)')

        openRecent = action('Open &Recent', self.openRecentProject,
                            'Ctrl+Shift+O', 'icon_open_recent.svg', u'Open last project (auto-detect images and labels)')

        opendir = action('&Images Dir', self.openDirDialog,
                         'Ctrl+u', 'icon_images_dir.svg', u'Select images directory')

        changeSavedir = action('&Labels Dir', self.changeSavedirDialog,
                               'Ctrl+r', 'icon_labels_dir.svg', u'Select labels save directory')

        saveFormat = action('&Save Format', self.popupSaveFormatMenu,
                            None, 'icon_save_format.svg', u'Change annotation save format')

        verify = action('&Verify Image', self.verifyImg,
                        'space', 'downloaded.svg', u'Verify Image')

        save = action('&Save', self.saveFileAndRenderList,
                      'Ctrl+S', 'save.svg', u'Save labels to file', enabled=False)

        close = action('&Close', self.closeFile, 'Ctrl+W', 'close.svg', u'Close current file')

        resetAll = action('&ResetAll', self.resetAll, None, 'reset.svg', u'Reset all')

        create = action('Create\nRectBox', self.createShape,
                        'w', 'rect.png', u'Draw a new Box', enabled=False)

        createSo = action('Create\nSolidRectBox', self.createSoShape,
                          None, 'rect.png', None, enabled=False)
        createSo.setVisible(False)

        createRo = action('Create\nRotatedRBox', self.createRoShape,
                        'e', 'rectRo.png', u'Draw a new RotatedRBox', enabled=False)

        delete = action('Delete\nRectBox', self.deleteSelectedShape,
                        'Delete', 'cancel2.svg', u'Delete (Shortcut: Q / Del)', enabled=False)
        
        labelAsBack = action('Label as background', self.labelAsBackground,
                         None, None, u'Label as background sample for detection training')
        
        deleteLabel = action('No Label', self.deleteLabel,
                              None, None, u'Delete all annotations for current image.S')

        copy = action('&Duplicate\nRectBox', self.copySelectedShape,
                      'Ctrl+D', 'copy.svg', u'Create a duplicate of the selected Box',
                      enabled=False)

        showInfo = action('&About', self.showInfoDialog, None, 'info.svg', u'About')

        zoom = QWidgetAction(self)
        zoom.setDefaultWidget(self.zoomWidget)
        self.zoomWidget.setWhatsThis(
            u"Zoom in or out of the image. Also accessible with"
            " %s and %s from the canvas." % (fmtShortcut("Ctrl+[-+]"),
                                             fmtShortcut("Ctrl+Wheel")))
        self.zoomWidget.setEnabled(False)

        zoomIn = action('Zoom &In', partial(self.addZoom, 10),
                        'Ctrl++', 'zoom-in.svg', u'Increase zoom level', enabled=False)
        zoomOut = action('&Zoom Out', partial(self.addZoom, -10),
                         'Ctrl+-', 'zoom-out.svg', u'Decrease zoom level', enabled=False)
        zoomOrg = action('&Original size', partial(self.setZoom, 100),
                         'Ctrl+=', 'zoom100.svg', u'Zoom to original size', enabled=False)
        fitWindow = action('&Fit Window', self.setFitWindow,
                           'Ctrl+F', 'zoomReset.svg', u'Zoom follows window size',
                           checkable=True, enabled=False)
        fitWidth = action('Fit &Width', self.setFitWidth,
                          'Ctrl+Shift+F', 'fit-width.svg', u'Zoom follows window width',
                          checkable=True, enabled=False)

        openPrevImg = action('&Prev Image', self.openPrevImg,
                             'a', 'previous.svg', u'Open Prev')

        openNextImg = action('&Next Image', self.openNextImg,
                             'd', 'next.svg', u'Open Next')        
        
        play = action('Play', self.playStart,
                    'Ctrl+Shift+P', 'play.svg', u'auto next',
                    checkable=True, enabled=True)
        
        self.prevButton.setDefaultAction(openPrevImg)
        self.nextButton.setDefaultAction(openNextImg)
        self.playButton.setDefaultAction(play)

        # Group zoom controls into a list for easier toggling.
        zoomActions = (self.zoomWidget, zoomIn, zoomOut,
                       zoomOrg, fitWindow, fitWidth)
        self.zoomMode = self.MANUAL_ZOOM
        self.scalers = {
            self.FIT_WINDOW: self.scaleFitWindow,
            self.FIT_WIDTH: self.scaleFitWidth,
            # Set to one to scale to 100% when loading files.
            self.MANUAL_ZOOM: lambda: 1,
        }

        edit = action('&Manage Labels', self.editLabel,
                      'Ctrl+M', 'tags.svg', u'Modify the label of the selected Box',
                      enabled=True)
        self.editButton.setDefaultAction(edit)

        # Lavel list context menu.
        labelMenu = QMenu()
        addActions(labelMenu, (edit, delete))

        # Store actions for further handling.
        self.actions = struct(save=save, open=openDir, openDir=openDir, openRecent=openRecent,
                              saveFormat=saveFormat, close=close, resetAll = resetAll,
                              create=create, createSo=createSo, createRo=createRo, delete=delete, 
                              labelAsBack=labelAsBack, deleteLabel=deleteLabel, edit=edit, copy=copy,
                              zoom=zoom, zoomIn=zoomIn, zoomOut=zoomOut, zoomOrg=zoomOrg,
                              fitWindow=fitWindow, fitWidth=fitWidth, play=play,
                              zoomActions=zoomActions,
                              fileMenuActions=(
                                  openDir, openRecent, opendir, changeSavedir, saveFormat, save, close, resetAll, quit),
                              beginner=(),
                              editMenu=(edit, copy, delete,
                                        None),
                              beginnerContext=(create, createSo, createRo, copy, delete, labelAsBack, deleteLabel),
                              onLoadActive=(
                                  close, create),
                              onShapesPresent=())

        # 保存文件格式类型子菜单 (Save Format)
        saveFormatMenu = QMenu('&Save Format', self)
        saveFormatMenu.setIcon(newIcon('icon_save_format.svg'))
        self.saveFormatActions = []
        formats = [
            "Pascal VOC XML (*.xml)",
            "YOLO TXT (*.txt)",
            "Create ML JSON (*.json)",
            "COCO JSON (*.json)"
        ]
        for fmt in formats:
            fmt_act = QAction(fmt, self, checkable=True)
            fmt_act.setChecked(fmt == self.save_format)
            fmt_act.triggered.connect(partial(self.set_save_format, fmt))
            saveFormatMenu.addAction(fmt_act)
            self.saveFormatActions.append(fmt_act)
        saveFormat.setMenu(saveFormatMenu)
        saveFormat.setToolTip(f"标注保存格式: {self.save_format} (点击切换)")

        # 最近项目菜单 (Open Recent)
        recentProjectsMenu = QMenu('Open &Recent', self)
        recentProjectsMenu.setIcon(newIcon('icon_open_recent.svg'))
        recentProjectsMenu.aboutToShow.connect(self.updateRecentProjectsMenu)
        openRecent.setMenu(recentProjectsMenu)

        self.menus = struct(
            file=self.menu('&File'),
            edit=self.menu('&Edit'),
            view=self.menu('&View'),
            help=self.menu('&Help'),
            recentProjects=recentProjectsMenu,
            saveFormat=saveFormatMenu,
            labelList=labelMenu)

        # Auto saving : Enable auto saving if pressing next (默认开启自动保存)
        self.autoSaving = QAction(newIcon('save.svg'), "Auto Saving", self)
        self.autoSaving.setCheckable(True)
        self.autoSaving.setChecked(settings.get(SETTING_AUTO_SAVE, True))
        
        # Add option to enable/disable labels being painted at the top of bounding boxes
        self.paintLabelsOption = QAction(newIcon('tags.svg'), "Paint Labels", self)
        self.paintLabelsOption.setCheckable(True)
        self.paintLabelsOption.setChecked(settings.get(SETTING_PAINT_LABEL, False))
        self.paintLabelsOption.triggered.connect(self.togglePaintLabelsOption)

        self.drawCorner = QAction(newIcon('sliders.svg'), 'Always Draw Corner', self)
        self.drawCorner.setCheckable(True)
        self.drawCorner.setChecked(settings.get(SETTING_DRAW_CORNER, False))
        self.drawCorner.triggered.connect(self.canvas.setDrawCornerState)
        
        addActions(self.menus.file,
                   (openDir, self.menus.recentProjects, opendir, changeSavedir, self.menus.saveFormat, 
                    verify, save, resetAll, quit))

        addActions(self.menus.help, (showInfo,))
        addActions(self.menus.view, (
            self.autoSaving,
            self.drawCorner,
            None,
            None,
            zoomIn, zoomOut, zoomOrg, None,
            fitWindow, fitWidth))

        self.menus.file.aboutToShow.connect(self.updateFileMenu)

        # Custom context menu for the canvas widget:
        addActions(self.canvas.menus[0], self.actions.beginnerContext)
        addActions(self.canvas.menus[1], (
            action('&Copy here', self.copyShape),
            action('&Move here', self.moveShape)))

        # YOLO Integration Actions & Menu (更新优化为全新专有名称与专有图标)
        yoloAutoSingleAction = action('单图自动批注', self.auto_annotate_current_image_quick, 's', 'auto_single.svg', u'单图自动批注 (快捷键: S)')
        yoloAutoBatchAction = action('批量自动批注', self.auto_annotate_batch_quick, None, 'auto_batch.svg', u'一键批量全自动批注当前文件夹')
        yoloAutoConfigAction = action('YOLO模型中心', self.openYOLOAutoAnnotateDialog, None, 'yolo_center.svg', u'打开 YOLO 模型中心 (模型参数调节与模型推理测试)')
        yoloTrainAction = action('YOLO模型训练', self.openYOLOTrainDialog, None, 'yolo_train.svg', u'打开 YOLO 模型训练面板 (数据训练与权重导出)')

        self.menus.ai = self.menu('Yolo')
        addActions(self.menus.ai, (yoloAutoSingleAction, yoloAutoBatchAction, yoloAutoConfigAction, None, yoloTrainAction))

        self.tools = self.toolbar('Tools')
        self.actions.beginner = (openDir, openRecent, opendir, changeSavedir, saveFormat, verify, save, None,
            create, createSo, createRo, copy, delete, None,
            yoloAutoSingleAction, yoloAutoBatchAction, yoloAutoConfigAction, yoloTrainAction, None,
            zoomIn, zoom, zoomOut, zoomOrg, fitWindow, fitWidth)

        self.statusBar().showMessage('%s started.' % __appname__)
        self.statusBar().show()

        # Application state.
        self.image = QImage()
        self.filePath = defaultFilename
        self.recentFiles = []
        self.maxRecent = 7
        self.lineColor = None
        self.fillColor = None
        self.zoom_level = 100
        self.fit_window = False
        # Add Chris
        self.difficult = False

        ## Fix the compatible issue for qt4 and qt5. Convert the QStringList to python list
        if settings.get(SETTING_RECENT_FILES):
            if have_qstring():
                recentFileQStringList = settings.get(SETTING_RECENT_FILES)
                self.recentFiles = [i for i in recentFileQStringList]
            else:
                self.recentFiles = recentFileQStringList = settings.get(SETTING_RECENT_FILES)

        size = settings.get(SETTING_WIN_SIZE, QSize(600, 500))
        position = settings.get(SETTING_WIN_POSE, QPoint(0, 0))
        self.resize(size)
        self.move(position)
        saveDir = settings.get(SETTING_SAVE_DIR, None) or settings.get('last_save_dir', None)
        self.lastOpenDir = settings.get(SETTING_LAST_OPEN_DIR, None) or settings.get('last_image_dir', None)
        if saveDir and os.path.exists(saveDir):
            self.defaultSaveDir = saveDir
            self.statusBar().showMessage('%s started. Annotation will be saved to %s' %
                                         (__appname__, self.defaultSaveDir))
            self.statusBar().show()

        self.restoreState(settings.get(SETTING_WIN_STATE, QByteArray()))
        Shape.line_color = self.lineColor = QColor(settings.get(SETTING_LINE_COLOR, DEFAULT_LINE_COLOR))
        Shape.fill_color = self.fillColor = QColor(settings.get(SETTING_FILL_COLOR, DEFAULT_FILL_COLOR))
        self.canvas.setDrawingColor(self.lineColor)
        # Add chris
        Shape.difficult = self.difficult

        # Populate the File menu dynamically.
        self.updateFileMenu()

        last_dir = self.lastOpenDir
        last_file = settings.get(SETTING_FILENAME, None)
        last_model = settings.get('last_model_path', None)

        if last_dir and os.path.exists(last_dir) and os.path.isdir(last_dir):
            self.queueEvent(partial(self.importDirImages, last_dir, last_file))
        elif last_file and os.path.exists(last_file) and os.path.isfile(last_file):
            self.queueEvent(partial(self.loadFile, last_file))

        # 记录上次加载的 AI 模型路径 (惰性加载与静默预热架构: 启动阶段绝不阻塞卡死 UI 主线程)
        self._last_model_path = last_model if (last_model and os.path.exists(last_model)) else None
        if not self._last_model_path:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            for c in [os.path.join(base_dir, "yolo26n.pt"), os.path.join(base_dir, "yolov8n.pt")]:
                if os.path.exists(c):
                    self._last_model_path = c
                    break

        if self._last_model_path:
            log_terminal(f"[Startup State] AI 模型已预选: {os.path.basename(self._last_model_path)}")

        self.cached_annotator = None
        self.cached_class_dict = {}
        self.cached_model_path = ""
        self.prewarm_thread = None
        self.auto_annotate_dialog = None

        # 核心极速架构: 启动主界面渲染 800ms 且完全空闲后，在后台静默预热 PyTorch 与 AI 权重
        # 彻底解决点击模型中心需等待转圈的问题，实现点击瞬间 0 毫秒秒开！
        QTimer.singleShot(800, self._start_idle_prewarm)

        # Callbacks:
        self.zoomWidget.valueChanged.connect(self.paintCanvas)

        self.populateModeActions()

        # Display cursor coordinates at the right of status bar
        self.labelCoordinates = QLabel('')
        self.statusBar().addPermanentWidget(self.labelCoordinates)

        self.imageDim = QLabel('')
        self.statusBar().addPermanentWidget(self.imageDim)

        self.statFile = QLabel('')
        self.statusBar().addPermanentWidget(self.statFile)
        
        # 捕获全局按键事件，确保 Q 与 Delete 完全一致且不被多重 QShortcut 冲突屏蔽
        QApplication.instance().installEventFilter(self)

    def noShapes(self):
        return not self.ItemShapeDict

    def populateModeActions(self):
        tool, menu = self.actions.beginner, self.actions.beginnerContext
        self.tools.clear()
        
        addActions(self.tools, tool)

        # 配置 Save Format 与 Open Recent 为直接弹出式历史项目下拉列表
        if hasattr(self.actions, 'saveFormat') and self.actions.saveFormat:
            btn_fmt = self.tools.widgetForAction(self.actions.saveFormat)
            if isinstance(btn_fmt, QToolButton):
                btn_fmt.setPopupMode(QToolButton.InstantPopup)
        if hasattr(self.actions, 'openRecent') and self.actions.openRecent:
            btn_rec = self.tools.widgetForAction(self.actions.openRecent)
            if isinstance(btn_rec, QToolButton):
                btn_rec.setPopupMode(QToolButton.InstantPopup)

        # 增加 Auto Save 专属自适应滑块开关按钮，自包含设计，无需外部文字，自适应水平与垂直工具栏
        if not hasattr(self, 'autoSaveSwitch') or self.autoSaveSwitch is None:
            self.autoSaveSwitch = SwitchButton(self, checked=self.autoSaving.isChecked(), orientation=self.tools.orientation())
            self.autoSaveSwitch.toggled.connect(self.on_auto_save_switch_toggled)
            self.autoSaving.toggled.connect(self.autoSaveSwitch.setChecked)
            self.tools.orientationChanged.connect(self.autoSaveSwitch.setOrientation)

        # 插入到工具栏中 save 按钮之后
        actions_list = self.tools.actions()
        save_idx = -1
        for idx, act in enumerate(actions_list):
            if act == self.actions.save:
                save_idx = idx
                break
        if save_idx >= 0 and save_idx + 1 < len(actions_list):
            self.tools.insertWidget(actions_list[save_idx + 1], self.autoSaveSwitch)
        else:
            self.tools.addWidget(self.autoSaveSwitch)

        self.canvas.menus[0].clear()
        addActions(self.canvas.menus[0], menu)
        self.menus.edit.clear()
        actions = (self.actions.create, self.actions.createSo, self.actions.createRo) 
        addActions(self.menus.edit, actions + self.actions.editMenu)

    def on_auto_save_switch_toggled(self, is_checked):
        self.autoSaving.blockSignals(True)
        self.autoSaving.setChecked(is_checked)
        self.autoSaving.blockSignals(False)
        self.settings[SETTING_AUTO_SAVE] = is_checked
        self.settings.save()
        status_text = "开启" if is_checked else "关闭"
        self.statusBar().showMessage(f"自动保存已{status_text}", 3000)
        log_terminal(f"[设置] 自动保存功能已{status_text}")

    def setDirty(self):
        self.dirty = True
        self.actions.save.setEnabled(True)

    def setBackSample(self):
        self.back_sample = True

    def resetBackSample(self):
        self.back_sample = False

    def set_save_format(self, format_name, *args, **kwargs):
        self.save_format = format_name
        self.settings['save_format'] = format_name
        self.settings.save()

        if hasattr(self, 'saveFormatActions'):
            for act in self.saveFormatActions:
                act.setChecked(act.text() == format_name)
        if hasattr(self.actions, 'saveFormat') and self.actions.saveFormat:
            self.actions.saveFormat.setToolTip(f"当前保存格式: {format_name} (点击切换)")

        if hasattr(self, 'auto_annotate_dialog') and self.auto_annotate_dialog is not None:
            self.auto_annotate_dialog.save_format = format_name
            if hasattr(self.auto_annotate_dialog, 'combo_save_format'):
                idx = self.auto_annotate_dialog.combo_save_format.findText(format_name)
                if idx >= 0:
                    self.auto_annotate_dialog.combo_save_format.blockSignals(True)
                    self.auto_annotate_dialog.combo_save_format.setCurrentIndex(idx)
                    self.auto_annotate_dialog.combo_save_format.blockSignals(False)

        # 切换格式后，如果当前图片已有标注，记录原文件并标记为待保存 (dirty)，启用保存按钮以支持主动保存实现格式替换
        if hasattr(self, 'filePath') and self.filePath and os.path.exists(self.filePath):
            has_existing = (hasattr(self, 'canvas') and self.canvas and len(self.canvas.shapes) > 0) or bool(getattr(self, 'current_annotation_file', None))
            if has_existing:
                self._old_annotation_file = getattr(self, 'current_annotation_file', None)
                if getattr(self, 'current_annotation_format', None) != self.save_format:
                    self.setDirty()
                    msg = f"[Save Format Terminal] 标注保存格式已切换为: {format_name}，点击保存 (Ctrl+S) 即可完成格式替换"
                    self.statusBar().showMessage(msg, 4000)
                    log_terminal(msg)
                    return
            else:
                from libs.annotation_io import find_annotation_file, read_annotations
                anno_file, detected_fmt = find_annotation_file(
                    image_path=self.filePath,
                    preferred_format=self.save_format,
                    save_dir=self.defaultSaveDir,
                    image_dir=self.dirname
                )
                if anno_file and detected_fmt == self.save_format:
                    img_shape = (self.image.height(), self.image.width(), 3) if (hasattr(self, 'image') and self.image) else (1, 1, 3)
                    shapes = read_annotations(anno_file, detected_fmt, img_shape, getattr(self, 'labelHist', None), self.filePath)
                    if shapes:
                        self.remAllLabels()
                        self.loadLabels(shapes)
                        self.setClean()
                        self.current_annotation_file = anno_file
                        self.current_annotation_format = detected_fmt
                        self.canvas.update()
                        self.update_stats()

        msg = f"[Save Format Terminal] 标注保存文件格式类型已切换为: {format_name}"
        self.statusBar().showMessage(msg, 3000)
        log_terminal(msg)

    def markFileSavedInList(self, file_path_or_idx, shape_count=None):
        """将保存/修改过的文件在右下角 File List 中高亮标为荧光绿"""
        if not hasattr(self, 'fileModel') or not self.fileModel:
            return
        if shape_count is None and hasattr(self, 'canvas'):
            shape_count = len(self.canvas.shapes)
        if isinstance(file_path_or_idx, QModelIndex):
            if file_path_or_idx.isValid():
                self.fileModel.setData(file_path_or_idx, shape_count, Qt.BackgroundRole)
                self.fileListView.viewport().update()
        elif isinstance(file_path_or_idx, str) and file_path_or_idx:
            try:
                str_list = self.fileModel.stringList()
                if file_path_or_idx in str_list:
                    row = str_list.index(file_path_or_idx)
                    idx = self.fileModel.index(row)
                    if idx.isValid():
                        self.fileModel.setData(idx, shape_count, Qt.BackgroundRole)
                        self.fileListView.viewport().update()
            except Exception:
                pass


    def setClean(self):
        self.dirty = False
        self.actions.save.setEnabled(False)
        self.actions.create.setEnabled(True)
        self.actions.createSo.setEnabled(True)
        self.actions.createRo.setEnabled(True)

    def openYOLOTrainDialog(self):
        image_dir = self.dirpath if hasattr(self, 'dirpath') and self.dirpath else (getattr(self, 'lastOpenDir', "") or "")
        xml_dir = getattr(self, 'defaultSaveDir', None) or image_dir
        if not hasattr(self, 'train_dialog') or self.train_dialog is None:
            from ui.train_dialog import TrainDialog
            self.train_dialog = TrainDialog(default_image_dir=image_dir, default_xml_dir=xml_dir, parent=self)
            self.train_dialog.model_trained_signal.connect(self.onYOLOModelTrained)
        self.train_dialog.show()
        self.train_dialog.raise_()
        self.train_dialog.activateWindow()

    def _start_idle_prewarm(self):
        """主窗口完全加载呈现后，在后台静默预热 PyTorch/Ultralytics 与默认/上次模型"""
        target_model = getattr(self, '_last_model_path', None)
        if not target_model or not os.path.exists(target_model):
            return

        try:
            from utils.worker_thread import BackgroundPrewarmThread
            self.prewarm_thread = BackgroundPrewarmThread(model_path=target_model, parent=self)
            self.prewarm_thread.prewarmed_signal.connect(self._on_idle_prewarm_finished)
            self.prewarm_thread.start()
        except Exception as e:
            pass

    def _on_idle_prewarm_finished(self, annotator, class_dict, model_path):
        if annotator and model_path:
            self.cached_annotator = annotator
            self.cached_class_dict = class_dict
            self.cached_model_path = model_path
            log_terminal(f"[AI Background Prewarm] 模型后台静默就绪: {os.path.basename(model_path)} (类别数: {len(class_dict)})")

            # 在空闲时段静默轻量预构建模型中心对话框，用户点击时达成 0 毫秒秒开！
            if getattr(self, 'auto_annotate_dialog', None) is None:
                try:
                    from ui.auto_annotate_dialog import AutoAnnotateDialog
                    self.auto_annotate_dialog = AutoAnnotateDialog(main_window_ref=self, parent=self)
                except Exception as e:
                    pass
            elif hasattr(self.auto_annotate_dialog, 'attach_prewarmed_annotator'):
                self.auto_annotate_dialog.attach_prewarmed_annotator(annotator, class_dict, model_path)

    def onYOLOModelTrained(self, best_pt_path):
        if not hasattr(self, 'auto_annotate_dialog') or self.auto_annotate_dialog is None:
            from ui.auto_annotate_dialog import AutoAnnotateDialog
            self.auto_annotate_dialog = AutoAnnotateDialog(main_window_ref=self, parent=self)
        self.auto_annotate_dialog.load_model(best_pt_path)
        self.auto_annotate_dialog.show()

    def openYOLOAutoAnnotateDialog(self):
        if not hasattr(self, 'auto_annotate_dialog') or self.auto_annotate_dialog is None:
            from ui.auto_annotate_dialog import AutoAnnotateDialog
            self.auto_annotate_dialog = AutoAnnotateDialog(main_window_ref=self, parent=self)

        # 若后台预热正在进行中但还未结束，无缝直连
        if hasattr(self, 'prewarm_thread') and self.prewarm_thread and self.prewarm_thread.isRunning():
            self.auto_annotate_dialog.set_status("⚡ 正在后台载入 AI 模型，稍候即可就绪...")
            self.prewarm_thread.prewarmed_signal.connect(
                self.auto_annotate_dialog.attach_prewarmed_annotator
            )

        self.auto_annotate_dialog.sync_paths_from_main_window()
        self.auto_annotate_dialog.show()
        self.auto_annotate_dialog.raise_()
        self.auto_annotate_dialog.activateWindow()

    def auto_annotate_current_image_quick(self):
        """按下快捷键 S 或点击【自动标注当前图 (S)】触发 (无弹窗，终端打印)"""
        if not hasattr(self, 'auto_annotate_dialog') or self.auto_annotate_dialog is None:
            from ui.auto_annotate_dialog import AutoAnnotateDialog
            self.auto_annotate_dialog = AutoAnnotateDialog(main_window_ref=self, parent=self)

        # 若模型中心尚未加载完成，但主窗口已预热完毕，直接挂载
        if (self.auto_annotate_dialog.annotator.model is None and 
            getattr(self, 'cached_annotator', None) and 
            hasattr(self.auto_annotate_dialog, 'attach_prewarmed_annotator')):
            self.auto_annotate_dialog.attach_prewarmed_annotator(
                self.cached_annotator, self.cached_class_dict, self.cached_model_path
            )

        # 模型标注前保存完整撤销快照，使 Ctrl+Z 可一步撤销整个模型标注操作
        self.save_undo_state()
        log_terminal("[Shortcut S / Quick Auto-Annotate] 触发当前页面自动标注...")
        self.auto_annotate_dialog.auto_annotate_single_image()

    def auto_annotate_batch_quick(self):
        """点击【一键批量自动标注】触发 (无弹窗，终端打印)"""
        if not hasattr(self, 'auto_annotate_dialog') or self.auto_annotate_dialog is None:
            from ui.auto_annotate_dialog import AutoAnnotateDialog
            self.auto_annotate_dialog = AutoAnnotateDialog(main_window_ref=self, parent=self)

        if (self.auto_annotate_dialog.annotator.model is None and 
            getattr(self, 'cached_annotator', None) and 
            hasattr(self.auto_annotate_dialog, 'attach_prewarmed_annotator')):
            self.auto_annotate_dialog.attach_prewarmed_annotator(
                self.cached_annotator, self.cached_class_dict, self.cached_model_path
            )

        log_terminal("[Quick Batch Auto-Annotate] 启动批量全自动标注...")
        self.auto_annotate_dialog.start_batch_annotate()

    def autoNext(self):
        if self.playing:
            suc = self.openNextImg()
            if not suc:
                self.actions.play.triggered.emit(False)
                self.actions.play.setChecked(False)

    def playStart(self, value=True):
        if value:
            self.playing = True
            self.displayTimer.start()
        else:
            self.playing = False
            self.displayTimer.stop()

    def toggleActions(self, value=True):
        """Enable/Disable widgets which depend on an opened image."""
        for z in self.actions.zoomActions:
            z.setEnabled(value)
        for action in self.actions.onLoadActive:
            action.setEnabled(value)

    def queueEvent(self, function):
        QTimer.singleShot(0, function)

    def status(self, message, delay=5000):
        self.statusBar().showMessage(message, delay)

    def resetState(self):
        self.labelModel.clear()
        self.labelModel.setHorizontalHeaderLabels(["Label", "Extra Info"])
        self.ShapeItemDict.clear()
        self.ItemShapeDict.clear()
        self.filePath = None
        self.imageData = None
        self.labelFile = None
        self.canvas.resetState()
        self.labelCoordinates.clear()
        self.imageDim.clear()
        self.update_stats()


    def labelDataChanged(self, topLeft, bottomRight):
        item0 = self.labelModel.item(topLeft.row(), 0)
        shape = self.ItemShapeDict[item0]
        if topLeft.column() == 0:
            shape.label = self.labelModel.data(topLeft)
            if sys.version_info < (3, 0, 0):
                shape.label = shape.label.toPyObject()
            if shape.label:
                self.default_label = shape.label
            color = generateColorByText(shape.label)
            item1 = self.labelModel.item(topLeft.row(), 1)
            item0.setBackground(color)
            item1.setBackground(color)
            shape.line_color = color
            shape.fill_color = color
            self.canvas.update()
            QTimer.singleShot(50, self.reorder_label_table)
        else:
            shape.extra_label = self.labelModel.data(topLeft)
            if sys.version_info < (3, 0, 0):
                shape.extra_label = shape.extra_label.toPyObject()
        self.setDirty()
        return

    def updateLabelShowing(self, index, str):
        item0 = self.labelModel.item(index.row(), 0)
        shape = self.ItemShapeDict[item0]
        shape.extra_label = str
        self.canvas.update()

    def addRecentFile(self, filePath):
        if filePath in self.recentFiles:
            self.recentFiles.remove(filePath)
        elif len(self.recentFiles) >= self.maxRecent:
            self.recentFiles.pop()
        self.recentFiles.insert(0, filePath)

    def showInfoDialog(self):
        msg = u'{0} \n©Chinakook 2018. chinakook@msn.com'.format(__appname__)
        QMessageBox.information(self, u'About', msg)

    def createShape(self):
        self.canvas.deSelectShape()
        self.canvas.current = None
        self.canvas.hShape = None
        self.canvas.hVertex = None
        self.canvas.prevPoint = QPointF()
        self.canvas.setEditing(0)
        self.canvas.canDrawRotatedRect = False
        self.actions.create.setEnabled(False)
        self.actions.createSo.setEnabled(False)
        self.actions.createRo.setEnabled(False)
        self.canvas.overrideCursor(Qt.CrossCursor)

    def createSoShape(self):
        self.canvas.deSelectShape()
        self.canvas.current = None
        self.canvas.setEditing(2)
        self.canvas.canDrawRotatedRect = False
        self.actions.create.setEnabled(False)
        self.actions.createSo.setEnabled(False)
        self.actions.createRo.setEnabled(False)
        self.canvas.overrideCursor(Qt.CrossCursor)

    def createRoShape(self):
        self.canvas.deSelectShape()
        self.canvas.current = None
        self.canvas.hShape = None
        self.canvas.hVertex = None
        self.canvas.prevPoint = QPointF()
        self.canvas.setEditing(0)
        self.canvas.canDrawRotatedRect = True
        self.actions.create.setEnabled(False)
        self.actions.createSo.setEnabled(False)
        self.actions.createRo.setEnabled(False)
        self.canvas.overrideCursor(Qt.CrossCursor)
    def createCancel(self):
        self.canvas.setEditing(1)
        self.canvas.restoreCursor()
        self.actions.create.setEnabled(True)
        self.actions.createSo.setEnabled(True)
        self.actions.createRo.setEnabled(True)

    def toggleDrawingSensitive(self, drawing=True):
        if not drawing:
            self.canvas.setEditing(1)
            self.canvas.restoreCursor()
            self.actions.create.setEnabled(True)
            self.actions.createSo.setEnabled(True)
            self.actions.createRo.setEnabled(True)

    def toggleDrawMode(self, edit=1):
        self.canvas.setEditing(edit)

    def toggleExtraEditing(self, state):
        index = self.labelsm.currentIndex()
        if index.isValid() and index.row() >= 0:
            editindex = self.labelModel.index(index.row(), 1)
            if self.labelList.state() != QAbstractItemView.EditingState:
                self.labelList.edit(editindex)

    def updateFileMenu(self):
        self.updateRecentProjectsMenu()
        currFilePath = self.filePath

        def exists(filename):
            return os.path.exists(filename)
        if hasattr(self.menus, 'recentFiles'):
            menu = self.menus.recentFiles
            menu.clear()
            files = [f for f in self.recentFiles if f !=
                     currFilePath and exists(f)]
            for i, f in enumerate(files):
                icon = newIcon('print-setup.svg')
                action = QAction(
                    icon, '&%d %s' % (i + 1, QFileInfo(f).fileName()), self)
                action.triggered.connect(partial(self.loadRecent, f))
                menu.addAction(action)

    def updateRecentProjectsMenu(self):
        if not hasattr(self, 'menus') or not hasattr(self.menus, 'recentProjects'):
            return
        menu = self.menus.recentProjects
        menu.clear()

        recent_list = self.settings.get('recent_projects', [])
        valid_items = []
        if isinstance(recent_list, list):
            for item in recent_list:
                if isinstance(item, dict):
                    img_p = item.get('images')
                    if img_p and os.path.isdir(img_p):
                        if not any(x.get('images') == img_p and x.get('labels') == item.get('labels') for x in valid_items):
                            valid_items.append(item)
                elif isinstance(item, str) and os.path.isdir(item):
                    if not any(x.get('images') == item for x in valid_items):
                        valid_items.append({'root': item, 'images': item, 'labels': os.path.join(item, 'labels')})

        if not valid_items:
            empty_act = QAction('(暂无历史项目记录)', self)
            empty_act.setEnabled(False)
            menu.addAction(empty_act)
            menu.addSeparator()
            browse_act = QAction(newIcon('icon_open_file.svg'), '打开新项目... (Open Dir)', self)
            browse_act.triggered.connect(self.openProjectDialog)
            menu.addAction(browse_act)
            return

        for i, item in enumerate(valid_items[:10]):
            r_path = item.get('root', '')
            img_p = item.get('images', '')
            lbl_p = item.get('labels', '')
            folder_name = os.path.basename(r_path or img_p) or img_p

            rel_img = os.path.basename(img_p) if img_p else "."
            rel_lbl = os.path.basename(lbl_p) if lbl_p else "."

            act_text = f"&{i+1}. {folder_name}   [图片: {rel_img} | 标签: {rel_lbl}]"
            act = QAction(newIcon('icon_open_recent.svg'), act_text, self)
            act.setToolTip(f"项目总目录: {r_path}\n图片路径: {img_p}\n标签保存路径: {lbl_p}")
            act.triggered.connect(partial(self.openRecentCombination, img_p, lbl_p, r_path))
            menu.addAction(act)

        menu.addSeparator()
        clear_act = QAction(newIcon('trash.svg'), '清空历史项目记录 (Clear History)', self)
        clear_act.triggered.connect(self.clearRecentProjects)
        menu.addAction(clear_act)

    def openRecentCombination(self, img_path, lbl_path, root_path=None):
        """精准恢复历史处理过的 (Images, Labels) 路径组合，避免路径猜测冲突"""
        if not self.mayContinue():
            return
        if not img_path or not os.path.exists(img_path):
            QMessageBox.warning(self, "路径不存在", f"历史项目图片路径不存在:\n{img_path}")
            return

        target_root = root_path if (root_path and os.path.exists(root_path)) else os.path.dirname(img_path)
        self.settings['last_project_root'] = target_root
        self.settings['last_image_dir'] = img_path
        self.settings['last_save_dir'] = lbl_path
        self.settings[SETTING_SAVE_DIR] = lbl_path
        self.settings[SETTING_LAST_OPEN_DIR] = img_path
        self.settings.save()

        self.addRecentProject(target_root, img_path, lbl_path)
        self.importDirImages(img_path, labels_dir=lbl_path)

        folder_name = os.path.basename(target_root or img_path) or img_path
        self.statusBar().showMessage(f"已恢复打开历史项目 [{folder_name}] | 图片: [{img_path}] | 标签: [{lbl_path}]", 5000)

    def clearRecentProjects(self):
        self.settings['recent_projects'] = []
        self.settings['last_project_root'] = None
        self.settings.save()
        self.updateRecentProjectsMenu()
        self.statusBar().showMessage("已清空历史项目记录", 3000)

    def popupSaveFormatMenu(self):
        if hasattr(self, 'menus') and hasattr(self.menus, 'saveFormat'):
            self.menus.saveFormat.exec_(QCursor.pos())

    def on_labels_applied(self, labels, default_label, chosen_file=""):
        """响应 Manage Labels 窗口非模态应用/保存事件，平滑同步主窗口状态"""
        if labels is not None:
            self.labelHist = list(labels)
            if default_label:
                self.default_label = default_label
            elif self.labelHist:
                self.default_label = self.labelHist[0]

            if chosen_file and os.path.isfile(chosen_file):
                self.current_label_file = chosen_file
                self.settings['current_label_file'] = chosen_file
                self.settings.save()

            self.labelList.updateLabelList(self.labelHist)
            group_name = os.path.basename(getattr(self, 'current_label_file', '')) if getattr(self, 'current_label_file', None) else "自定义"
            self.statusBar().showMessage(f"已应用标签组 [{group_name}] (共 {len(self.labelHist)} 个类别，当前默认: {self.default_label})", 4000)

    def editLabel(self):
        if hasattr(self, 'canvas') and self.canvas.drawing():
            self.canvas.setEditing()
        self.labelDialog.updateData(
            self.labelHist,
            default_label=getattr(self, 'default_label', None),
            current_file=getattr(self, 'current_label_file', None)
        )
        self.labelDialog.popUp()


    def fileCurrentChanged(self, current, previous):
        self.statFile.setText('{0}/{1}'.format(current.row()+1, current.model().rowCount()))
        if self.autoSaving.isChecked():
            if self.defaultSaveDir is not None:
                self.labelList.earlyCommit()
                format_mismatched = (
                    hasattr(self, 'current_annotation_format') and
                    self.current_annotation_format is not None and
                    self.current_annotation_format != self.save_format and
                    len(self.canvas.shapes) > 0
                )
                prev_file = self.fileModel.data(previous, Qt.EditRole) if previous.isValid() else self.filePath
                prev_name = os.path.basename(prev_file or self.filePath or '')

                if len(self.canvas.shapes) == 0:
                    # 没做任何处理/无标注框时，点击下一张触发自动保存：做出清晰提示并自动保存对应格式的空标签文件
                    if previous.isValid() and self.filePath:
                        self.saveFile(prompt_empty=False)
                        self.markFileSavedInList(previous, 0)
                        self.statusBar().showMessage(f"【自动保存】图片 [{prev_name}] 无标注框，已自动保存空标签文件 (负样本)", 3500)
                        log_terminal(f"[自动保存] 图片 [{prev_name}] 无标注框，已自动生成空标签文件")
                else:
                    if self.dirty is True or format_mismatched:
                        self.markFileSavedInList(previous, len(self.canvas.shapes))
                        self.saveFile(prompt_empty=False)
                        self.statusBar().showMessage(f"【自动保存】已保存图片 [{prev_name}] ({len(self.canvas.shapes)} 个标注框)", 3000)
                        log_terminal(f"[自动保存] 图片 [{prev_name}] 已自动保存 {len(self.canvas.shapes)} 个标注框")
            else:
                self.changeSavedirDialog()
                return

        else:
            # 未开启自动保存时，如果当前图片未保存，提示用户保存/放弃
            if self.dirty is True:
                if not self.mayContinue():
                    self.filesm.blockSignals(True)
                    self.filesm.setCurrentIndex(previous, QItemSelectionModel.ClearAndSelect)
                    self.filesm.blockSignals(False)
                    return
        filename = self.fileModel.data(current, Qt.EditRole)
        if filename:
            self.loadFile(filename)

        if self.canvas.selectedShape:
            self.canvas.selectedShape.selected = False
            self.canvas.selectedShape = None
            self.canvas.setHiding(False)
        self.resetBackSample()


    # Add chris
    def btnstate(self, item= None):
        """ Function to handle difficult examples
        Update on each object """
        if not self.canvas.editing():
            return
        
        item0 = self.labelModel.itemFromIndex(self.labelModel.index(self.labelsm.currentIndex().row(), 0))
        if item0 is None:
            item0 = self.labelModel.item(self.labelModel.rowCount() - 1,0)

        difficult = self.diffcButton.isChecked()

        try:
            shape = self.ItemShapeDict[item0]
        except:
            pass
        # Checked and Update
        try:
            if difficult != shape.difficult:
                shape.difficult = difficult
                self.setDirty()
            else:  # User probably changed item visibility
                #self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)
                pass
        except:
            pass

    def update_label_list_numbers(self):
        """为右侧 CLabelView 的每一行按顺序生成 1-indexed 序号头 (1, 2, 3...)"""
        for r in range(self.labelModel.rowCount()):
            num_item = QStandardItem(str(r + 1))
            num_item.setTextAlignment(Qt.AlignCenter)
            self.labelModel.setVerticalHeaderItem(r, num_item)

    def shapeSelectionChanged(self, selected=False):
        if self._noSelectionSlot:
            self._noSelectionSlot = False
        else:
            shape = self.canvas.selectedShape
            if shape and shape in self.ShapeItemDict:
                if len(self.canvas.selectedShapes) > 1:
                    self._noSelectionSlot = True
                item0 = self.ShapeItemDict[shape]
                index = self.labelModel.indexFromItem(item0)
                self.labelList.selectRow(index.row())
            else:
                self.labelList.clearSelection()

        shape = self.canvas.selectedShape
        if shape and getattr(shape, 'label', None):
            self.default_label = shape.label

        self.actions.delete.setEnabled(selected)
        self.actions.copy.setEnabled(selected)

    def auto_expand_label_editor(self):
        """鼠标单次点击(无拖动)选中某个标注框时，右侧标签列表中自动展开 Label 下拉选择框"""
        shape = self.canvas.selectedShape
        if shape and shape in self.ShapeItemDict:
            item0 = self.ShapeItemDict[shape]
            index = self.labelModel.indexFromItem(item0)
            if index.isValid():
                self.labelsm.blockSignals(True)
                self.labelList.selectRow(index.row())
                self.labelsm.blockSignals(False)
                label_idx = self.labelModel.index(index.row(), 0)
                if self.labelList.state() != QAbstractItemView.EditingState:
                    self.labelList.edit(label_idx)

    def get_label_sort_index(self, label):
        """根据 self.labelHist 预设类别的先后顺序计算类别排序权重"""
        if hasattr(self, 'labelHist') and self.labelHist and label in self.labelHist:
            return self.labelHist.index(label)
        return 999999

    def reorder_label_table(self):
        """始终按照原标签选择栏中的标签从上往下一类一类归类排序"""
        if getattr(self, '_is_reordering_table', False):
            return
        if self.labelModel.rowCount() <= 1:
            self.update_label_list_numbers()
            return

        self._is_reordering_table = True
        try:
            selected_shape = self.canvas.selectedShape

            rows_data = []
            for r in range(self.labelModel.rowCount()):
                item0 = self.labelModel.item(r, 0)
                item1 = self.labelModel.item(r, 1)
                if item0 and item0 in self.ItemShapeDict:
                    shape = self.ItemShapeDict[item0]
                    label = shape.label
                    sort_key = (self.get_label_sort_index(label), r)
                    rows_data.append((sort_key, shape, item0.text(), item1.text() if item1 else "", item0.background()))

            rows_data.sort(key=lambda x: x[0])

            self.labelModel.blockSignals(True)
            self.labelModel.setRowCount(0)
            self.ShapeItemDict.clear()
            self.ItemShapeDict.clear()

            new_selected_row = -1
            for r_idx, (_, shape, text0, text1, bg) in enumerate(rows_data):
                it0 = HashableQStandardItem(text0)
                it1 = QStandardItem(text1)
                it0.setBackground(bg)
                it1.setBackground(bg)
                self.labelModel.appendRow([it0, it1])
                self.ShapeItemDict[shape] = it0
                self.ItemShapeDict[it0] = shape
                if shape == selected_shape:
                    new_selected_row = r_idx

            self.labelModel.blockSignals(False)
            self.update_label_list_numbers()

            if hasattr(self, 'labelList') and self.labelList and hasattr(self.labelList, 'verticalHeader'):
                vh = self.labelList.verticalHeader()
                if hasattr(vh, 'isChecked'):
                    vh.isChecked = [1] * self.labelModel.rowCount()

            if new_selected_row >= 0:
                self.labelsm.blockSignals(True)
                self.labelList.selectRow(new_selected_row)
                self.labelsm.blockSignals(False)
        finally:
            self._is_reordering_table = False

    def addLabel(self, shape):
        shape.paintLabel = self.paintLabelsOption.isChecked()

        item0 = HashableQStandardItem(shape.label)
        item1 = QStandardItem(shape.extra_label)
        color = generateColorByText(shape.label)
        item0.setBackground(color)
        item1.setBackground(color)

        self.labelModel.appendRow([item0, item1])
        self.ShapeItemDict[shape] = item0
        self.ItemShapeDict[item0] = shape

        # 每次创建新标签（含手动绘制 W/E、复制 Ctrl+D、模型标注等），自动执行全量归类排序
        self.reorder_label_table()
        self.update_label_list_numbers()
        self.update_stats()

        for action in self.actions.onShapesPresent:
            action.setEnabled(True)

    def remLabel(self, shape):
        if shape is None:
            return

        if shape in self.ShapeItemDict:
            item0 = self.ShapeItemDict[shape]
            index = self.labelModel.indexFromItem(item0)
            if index.isValid():
                self.labelModel.removeRows(index.row(), 1)
            del self.ShapeItemDict[shape]
            if item0 in self.ItemShapeDict:
                del self.ItemShapeDict[item0]
        self.update_label_list_numbers()
        self.update_stats()

    def remAllLabels(self):
        self.canvas.deleteAll()
        self.labelModel.clear()
        self.labelModel.setHorizontalHeaderLabels(["Label", "Extra Info"])
        self.ShapeItemDict.clear()
        self.ItemShapeDict.clear()
        self.update_label_list_numbers()
        self.update_stats()



    def loadLabels(self, shapes):
        # 面积排序：面积大的置于底层，面积小的置于顶层
        def get_shape_info_area(shape_info):
            try:
                points = shape_info[1]
                if len(points) >= 2:
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    return (max(xs) - min(xs)) * (max(ys) - min(ys))
            except Exception:
                pass
            return 0.0

        shapes = sorted(shapes, key=get_shape_info_area, reverse=True)

        s = []
        for shape_info in shapes:
            if len(shape_info) == 5:
                label, points, line_color, fill_color, difficult = shape_info
                extra_label = ''
                isRotated = False
                direction = 0
            elif len(shape_info) == 6:
                label, points, line_color, fill_color, difficult, extra_label = shape_info
                isRotated = False
                direction = 0
            elif len(shape_info) == 7:
                label, points, line_color, fill_color, difficult, isRotated, direction = shape_info
                extra_label = ''
            elif len(shape_info) == 8:
                label, points, line_color, fill_color, difficult, isRotated, direction, extra_label = shape_info
            else:
                pass
            shape = Shape(label=label)
            for x, y in points:
                shape.addPoint(QPointF(x, y))
            shape.difficult = difficult
            shape.direction = direction
            shape.isRotated = isRotated
            shape.extra_label = extra_label
            shape.close()
            s.append(shape)

            if line_color:
                shape.line_color = QColor(*line_color)
            else:
                shape.line_color = generateColorByText(label)

            if fill_color:
                shape.fill_color = QColor(*fill_color)
            else:
                shape.fill_color = generateColorByText(label)
            
            shape.alwaysShowCorner = self.drawCorner.isChecked()

            self.addLabel(shape)

        self.canvas.loadShapes(s)
        self.canvas.reorderShapesByArea()
        self.reorder_label_table()
        self.update_stats()


    def saveLabels(self, annotationFilePath):
        if self.labelFile is None:
            self.labelFile = LabelFile()
            self.labelFile.verified = self.canvas.verified

        def format_shape(s):
            return dict(label=s.label,
                        line_color=s.line_color.getRgb(),
                        fill_color=s.fill_color.getRgb(),
                        points=[(p.x(), p.y()) for p in s.points],
                       # add chris
                        difficult = s.difficult,
                        direction = s.direction,
                        center = s.center,
                        isRotated = s.isRotated,
                        extra_text = s.extra_label)

        shapes = [format_shape(shape) for shape in self.canvas.shapes]
        from libs.annotation_io import write_annotations, get_format_ext
        try:
            ext = get_format_ext(self.save_format)
            base, _ = os.path.splitext(annotationFilePath)
            final_path = base + ext

            img_shape = (self.image.height(), self.image.width(), 3) if self.image else (1, 1, 3)
            saved_file = write_annotations(
                target_file=final_path,
                format_name=self.save_format,
                shapes=shapes,
                image_path=self.filePath,
                image_shape=img_shape,
                class_list=getattr(self, 'labelHist', None)
            )
            log_terminal(f"[Shortcut Ctrl+S Terminal] 标注数据已成功保存 [{self.save_format}]: {saved_file}")
            return True
        except Exception as e:
            self.errorMessage(u'Error saving label data', u'<b>%s</b>' % e)
            return False

    def copySelectedShape(self):
        if not self.canvas.selectedShape and not self.canvas.selectedShapes:
            if self.canvas.hShape:
                self.canvas.selectShape(self.canvas.hShape)
        self.save_undo_state()
        newShapes = self.canvas.copySelectedShape()
        if not newShapes:
            return
        for shape in newShapes:
            self.addLabel(shape)
        self.setDirty()
        msg = f"[Shortcut Ctrl+D Terminal] 已在原地生成副本标注框 ({len(newShapes)} 个)"
        self.statusBar().showMessage(msg, 3000)
        log_terminal(msg)

    def labelCurrentChanged(self, current, previous):
        if getattr(self, '_is_updating_label', False):
            return
        if current.row() < 0:
            return
        # Don't override multi-selection from canvas when label row changes
        if len(self.canvas.selectedShapes) > 1:
            return
        item0 = self.labelModel.itemFromIndex(self.labelModel.index(current.row(), 0))
        if not item0 or item0 not in self.ItemShapeDict:
            return
        if self.canvas.editing():
            self._is_updating_label = True
            try:
                self._noSelectionSlot = True
                shape = self.ItemShapeDict[item0]
                # 将选中的框提到图层最上层 (仅当不在最顶层时调整，避免频繁修改列表)
                if shape in self.canvas.shapes and len(self.canvas.shapes) > 1 and self.canvas.shapes[-1] != shape:
                    self.canvas.shapes.remove(shape)
                    self.canvas.shapes.append(shape)
                self.canvas.selectShape(shape)
                if shape and getattr(shape, 'label', None):
                    self.default_label = shape.label
                self.diffcButton.setChecked(shape.difficult)
            finally:
                self._is_updating_label = False

    def labelHeaderClicked(self, index, checked):
        item0 = self.labelModel.item(index, 0)
        if item0 and item0 in self.ItemShapeDict:
            shape = self.ItemShapeDict[item0]
            self.canvas.setShapeVisible(shape, checked)

    # Callback functions:
    def newShape(self, continous):
        text = self.default_label
        if not text:
            if hasattr(self, 'labelHist') and self.labelHist:
                text = self.labelHist[0]
            else:
                text = "object"
            self.default_label = text
        extra_text = ""
        generate_color = generateColorByText(text)
        shape = self.canvas.setLastLabel(text, generate_color, generate_color, extra_text)
        if shape is None:
            self.canvas.resetAllLines()
            return
        shape.alwaysShowCorner=self.drawCorner.isChecked()

        self.addLabel(shape)
        if continous:
            pass
        else:
            self.canvas.setEditing(1)
            self.actions.create.setEnabled(True)
            self.actions.createSo.setEnabled(True)
            self.actions.createRo.setEnabled(True)

        self.setDirty()

        # 默认选中新建的标注框，并在归类完成后安全展开右侧对应的标签下拉选项
        self.canvas.selectShape(shape)
        def expand_new_shape_label():
            if shape in self.ShapeItemDict:
                item0 = self.ShapeItemDict[shape]
                index = self.labelModel.indexFromItem(item0)
                if index.isValid():
                    row = index.row()
                    self.labelsm.blockSignals(True)
                    self.labelList.selectRow(row)
                    self.labelsm.blockSignals(False)
                    col0_idx = self.labelModel.index(row, 0)
                    if self.labelList.state() != QAbstractItemView.EditingState:
                        self.labelList.edit(col0_idx)
        QTimer.singleShot(60, expand_new_shape_label)

    def scrollRequest(self, delta, orientation):
        #units = - delta / (8 * 15)
        units = - delta / (2 * 15)
        bar = self.scrollBars[orientation]
        # bar.setValue(bar.value() + bar.singleStep() * units)
        bar.setValue(int(bar.value() + bar.singleStep() * delta))

    def setZoom(self, value):
        self.actions.fitWidth.setChecked(False)
        self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.MANUAL_ZOOM
        self.zoomWidget.setValue(value)

    def addZoom(self, increment=10):
        self.setZoom(self.zoomWidget.value() + increment)

    def zoomRequest(self, delta):
        # get the current scrollbar positions
        # calculate the percentages ~ coordinates
        h_bar = self.scrollBars[Qt.Horizontal]
        v_bar = self.scrollBars[Qt.Vertical]

        # get the current maximum, to know the difference after zooming
        h_bar_max = h_bar.maximum()
        v_bar_max = v_bar.maximum()

        # get the cursor position and canvas size
        # calculate the desired movement from 0 to 1
        # where 0 = move left
        #       1 = move right
        # up and down analogous
        cursor = QCursor()
        pos = cursor.pos()
        relative_pos = QWidget.mapFromGlobal(self, pos)

        cursor_x = relative_pos.x()
        cursor_y = relative_pos.y()

        w = self.scrollArea.width()
        h = self.scrollArea.height()

        # the scaling from 0 to 1 has some padding
        # you don't have to hit the very leftmost pixel for a maximum-left movement
        margin = 0.1
        move_x = (cursor_x - margin * w) / (w - 2 * margin * w)
        move_y = (cursor_y - margin * h) / (h - 2 * margin * h)

        # clamp the values from 0 to 1
        move_x = min(max(move_x, 0), 1)
        move_y = min(max(move_y, 0), 1)

        # zoom in
        units = delta / (8 * 15)
        scale = 10
        self.addZoom(scale * units)

        # get the difference in scrollbar values
        # this is how far we can move
        d_h_bar_max = h_bar.maximum() - h_bar_max
        d_v_bar_max = v_bar.maximum() - v_bar_max

        # get the new scrollbar values
        new_h_bar_value = h_bar.value() + move_x * d_h_bar_max
        new_v_bar_value = v_bar.value() + move_y * d_v_bar_max

        h_bar.setValue(new_h_bar_value)
        v_bar.setValue(new_v_bar_value)

    def setFitWindow(self, value=True):
        if value:
            self.actions.fitWidth.setChecked(False)
        self.zoomMode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjustScale()

    def setFitWidth(self, value=True):
        if value:
            self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjustScale()

    def loadFile(self, filePath=None):
        """Load the specified file, or the last opened file if None."""
        self.resetState()
        self.canvas.setEnabled(False)
        if filePath is None:
            filePath = self.settings.get(SETTING_FILENAME)

        # Make sure that filePath is a regular python string, rather than QString

        unicodeFilePath = filePath
        
        if unicodeFilePath and os.path.exists(unicodeFilePath):
            if LabelFile.isLabelFile(unicodeFilePath):
                try:
                    self.labelFile = LabelFile(unicodeFilePath)
                except LabelFileError as e:
                    self.errorMessage(u'Error opening file',
                                      (u"<p><b>%s</b></p>"
                                       u"<p>Make sure <i>%s</i> is a valid label file.")
                                      % (e, unicodeFilePath))
                    self.status("Error reading %s" % unicodeFilePath)
                    return False
                self.imageData = self.labelFile.imageData
                self.lineColor = QColor(*self.labelFile.lineColor)
                self.fillColor = QColor(*self.labelFile.fillColor)
                self.canvas.verified = self.labelFile.verified
            else:
                # Load image:
                # read data first and store for saving into label file.
                # self.imageData = read(unicodeFilePath, None)
                self.labelFile = None
                self.canvas.verified = False

            # image = QImage.fromData(self.imageData)
            # if image.isNull():
            #     self.errorMessage(u'Error opening file',
            #                       u"<p>Make sure <i>%s</i> is a valid image file." % unicodeFilePath)
            #     self.status("Error reading %s" % unicodeFilePath)
            #     return False
            #self.status("Loaded %s" % os.path.basename(unicodeFilePath))

            reader0 = QImageReader(unicodeFilePath)
            reader0.setAutoTransform(True)
            # transformation = reader0.transformation()
            # print(transformation)
            image = reader0.read()

            self.image = image
            self.filePath = unicodeFilePath
            self.canvas.loadPixmap(QPixmap.fromImage(image))
            self.imageDim.setText('%d x %d' % (self.image.width(), self.image.height()))
            if self.labelFile is not None:
                self.loadLabels(self.labelFile.shapes)
            self.setClean()
            self.canvas.setEnabled(True)
            self.adjustScale(initial=True)
            self.paintCanvas()
            self.addRecentFile(self.filePath)
            self.toggleActions(True)

            # 多格式兼容检索与载入标注 (支持 Pascal VOC XML, YOLO TXT, Create ML JSON, COCO JSON)
            from libs.annotation_io import find_annotation_file, read_annotations
            img_shape = (self.image.height(), self.image.width(), 3) if (hasattr(self, 'image') and self.image) else (1, 1, 3)
            anno_file, detected_fmt = find_annotation_file(
                image_path=self.filePath,
                preferred_format=self.save_format,
                save_dir=self.defaultSaveDir,
                image_dir=self.dirname
            )

            if anno_file and os.path.isfile(anno_file):
                loaded_shapes = read_annotations(
                    file_path=anno_file,
                    format_name=detected_fmt,
                    image_shape=img_shape,
                    class_list=getattr(self, 'labelHist', None),
                    image_path=self.filePath
                )
                if loaded_shapes:
                    self.loadLabels(loaded_shapes)
                self.current_annotation_file = anno_file
                self.current_annotation_format = detected_fmt
            else:
                self.current_annotation_file = None
                self.current_annotation_format = None

            # 实时同步并高亮刷新右下侧照片列表中的选中状态与序号统计
            if hasattr(self, 'fileModel') and self.fileModel and self.fileModel.rowCount() > 0:
                try:
                    str_list = self.fileModel.stringList()
                    if self.filePath in str_list:
                        row = str_list.index(self.filePath)
                        cur_idx = self.fileModel.index(row)
                        self.filesm.blockSignals(True)
                        self.filesm.setCurrentIndex(cur_idx, QItemSelectionModel.ClearAndSelect)
                        self.filesm.blockSignals(False)
                        self.fileListView.scrollTo(cur_idx)
                        self.statFile.setText(f'{row + 1}/{len(str_list)}')
                        self.fileListView.viewport().update()
                except Exception:
                    pass

            # 记录历史访问图片路径，支持跨图撤销返回上一张图片
            if not hasattr(self, 'image_navigation_history'):
                self.image_navigation_history = []
            if not self.image_navigation_history or self.image_navigation_history[-1] != unicodeFilePath:
                self.image_navigation_history.append(unicodeFilePath)

            self.canvas.setFocus(True)
            self.update_stats()
            return True
        self.update_stats()
        return False


    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            key = event.key()
            txt = event.text().lower() if event.text() else ""
            mods = event.modifiers()
            focus_widget = QApplication.focusWidget()
            is_typing_text = False
            for w in (focus_widget, obj):
                if not w:
                    continue
                from PyQt5.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox, QComboBox, QAbstractItemView
                if isinstance(w, (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox, QComboBox)):
                    is_typing_text = True
                    break
                elif w.parent() and isinstance(w.parent(), (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox, QComboBox)):
                    is_typing_text = True
                    break
            if not is_typing_text and hasattr(self, 'labelList') and self.labelList:
                from PyQt5.QtWidgets import QAbstractItemView
                if self.labelList.state() == QAbstractItemView.EditingState:
                    is_typing_text = True
                elif self.labelList.extra_delegate and self.labelList.extra_delegate.editor in (focus_widget, obj):
                    is_typing_text = True

            if (mods & Qt.ControlModifier):
                if (mods & Qt.ShiftModifier) and (key == Qt.Key_Z or txt == 'z'):
                    self.redo_shape_action()
                    return True
                elif key == Qt.Key_Z or txt == 'z':
                    self.undo_shape_action()
                    return True
                elif key == Qt.Key_C or txt == 'c':
                    self.copySelectedShapeToClipboard()
                    return True
                elif key == Qt.Key_X or txt == 'x':
                    self.cutSelectedShapeToClipboard()
                    return True
                elif key == Qt.Key_V or txt == 'v':
                    self.pasteShapeFromClipboard()
                    return True
                elif key == Qt.Key_D or txt == 'd':
                    self.copySelectedShape()
                    return True
                elif (mods & Qt.ShiftModifier) and (key == Qt.Key_L or txt == 'l'):
                    self.togglePaintLabelsOption()
                    log_terminal("[Shortcut Ctrl+Shift+L Terminal] 切换标注框标签文字显示/隐藏")
                    return True

            if (key in (Qt.Key_Q, Qt.Key_Delete) or (txt == 'q' and not mods)) and not is_typing_text:
                if hasattr(self, 'canvas') and self.canvas:
                    self.canvas.dragIgnoreUntilMouseUp = True
                    self.canvas.prevPoint = QPointF()
                    self.canvas.pressPos = None
                    self.canvas.wasDragged = False
                    self.canvas.restoreCursor()
                    self.canvas.overrideCursor(Qt.ArrowCursor)
                self.deleteSelectedShape()
                return True
            elif txt == 'e' and not mods and not is_typing_text:
                log_terminal("[Shortcut E Terminal] 切换 OBB 旋转框绘制模式")
                self.createRoShape()
                return True
            elif txt == 'w' and not mods and not is_typing_text:
                log_terminal("[Shortcut W Terminal] 触发新建矩形框标注模式 (Draw Box)")
                self.createShape()
                return True
            elif txt in ('z', 'v', 'x', 'c') and not mods and not is_typing_text:
                if self.canvas.selectedShape:
                    if not event.isAutoRepeat():
                        if not self._active_adjust_keys:
                            self.save_undo_state()
                        self._active_adjust_keys.add(txt)
                        self._apply_adjust_key_step(txt)
                        if not self._adjust_timer.isActive():
                            self._adjust_timer.start(30)
                    return True
            elif txt == 'r' and not mods and not is_typing_text:
                self.toggle_undo_redo()
                return True
        elif event.type() == QEvent.KeyRelease:
            if event.isAutoRepeat():
                return super(MainWindow, self).eventFilter(obj, event)
            key = event.key()
            txt = event.text().lower() if event.text() else ""
            if key == Qt.Key_Z: txt = 'z'
            elif key == Qt.Key_V: txt = 'v'
            elif key == Qt.Key_X: txt = 'x'
            elif key == Qt.Key_C: txt = 'c'
            if txt in ('z', 'v', 'x', 'c'):
                self._active_adjust_keys.discard(txt)
                if txt in ('z', 'v'):
                    if hasattr(self, 'canvas') and self.canvas:
                        self.canvas._rot_start_time = None
                        self.canvas._rot_last_time = 0
                if not self._active_adjust_keys:
                    self._adjust_timer.stop()
                return True

        return super(MainWindow, self).eventFilter(obj, event)

    def _apply_adjust_key_step(self, key_char):
        shape = self.canvas.selectedShape
        if not shape:
            return
        if key_char == 'x':
            shape.increaseLength(factor=1.02, delta=2.0)
            self.canvas.shapeMoved.emit()
            self.canvas.update()
            self.setDirty()
            box_type = "旋转框(E)" if getattr(shape, 'isRotated', False) else "普通框(W)"
            log_terminal(f"[Shortcut X Terminal] 增大选中{box_type}的长 (Length +)")
        elif key_char == 'c':
            shape.increaseWidth(factor=1.02, delta=2.0)
            self.canvas.shapeMoved.emit()
            self.canvas.update()
            self.setDirty()
            box_type = "旋转框(E)" if getattr(shape, 'isRotated', False) else "普通框(W)"
            log_terminal(f"[Shortcut C Terminal] 增大选中{box_type}的宽 (Width +)")
        elif key_char in ('z', 'v'):
            if not getattr(shape, 'isRotated', False):
                self.statusBar().showMessage("当前为不可旋转矩形框(W)，无法旋转；仅旋转框(E)支持旋转", 3000)
                log_terminal("[提示] 当前选中的标注框为标准矩形框(W)，不可旋转。如需旋转请使用 E 键创建旋转框。")
                return
            rot_dir = 1 if key_char == 'z' else -1
            angle = self.canvas.get_dynamic_rotation_angle(rot_dir)
            if not self.canvas.rotateOutOfBound(angle):
                shape.rotate(angle)
                self.canvas.shapeMoved.emit()
                self.canvas.update()
                self.setDirty()
                deg = abs(angle * 180.0 / math.pi)
                dir_str = "顺时针" if rot_dir == 1 else "逆时针"
                sign_str = "+" if rot_dir == 1 else "-"
                log_terminal(f"[Shortcut {key_char.upper()} Terminal] {dir_str}旋转标注框 ({sign_str}{deg:.1f}° 变速调控)")

    def _on_adjust_timer_tick(self):
        if not self._active_adjust_keys or not self.canvas.selectedShape:
            self._adjust_timer.stop()
            self._active_adjust_keys.clear()
            self._size_start_time = None
            return

        shape = self.canvas.selectedShape
        has_changes = False
        now = time.time()

        # 1. 旋转处理 (Z / V 互不冲突且仅限可旋转框 E，动态平滑加速上限至 4.2°)
        rot_dir = 0
        if 'z' in self._active_adjust_keys and 'v' not in self._active_adjust_keys:
            rot_dir = 1
        elif 'v' in self._active_adjust_keys and 'z' not in self._active_adjust_keys:
            rot_dir = -1

        if rot_dir != 0:
            if getattr(shape, 'isRotated', False):
                angle = self.canvas.get_dynamic_rotation_angle(rot_dir)
                if not self.canvas.rotateOutOfBound(angle):
                    shape.rotate(angle)
                    has_changes = True

        # 2. 尺寸动态调节处理 (X / C，动态速度平滑扩充，固定框 W 与旋转框 E 均完美支持)
        if 'x' in self._active_adjust_keys or 'c' in self._active_adjust_keys:
            if getattr(self, '_size_start_time', None) is None:
                self._size_start_time = now
            elapsed = now - self._size_start_time
            t_ratio = min(1.0, elapsed / 1.5)
            # 动态 factor 从 1.015 加速至 1.045，delta 从 1.5 加速至 4.5
            dyn_factor = 1.015 + (1.045 - 1.015) * t_ratio
            dyn_delta = 1.5 + (4.5 - 1.5) * t_ratio

            if 'x' in self._active_adjust_keys:
                shape.increaseLength(factor=dyn_factor, delta=dyn_delta)
                has_changes = True

            if 'c' in self._active_adjust_keys:
                shape.increaseWidth(factor=dyn_factor, delta=dyn_delta)
                has_changes = True
        else:
            self._size_start_time = None

        if has_changes:
            self.canvas.shapeMoved.emit()
            self.canvas.update()
            self.setDirty()

    def keyPressEvent(self, event):
        key = event.key()
        txt = event.text().lower() if event.text() else ""
        if (key in (Qt.Key_Q, Qt.Key_Delete) or txt == 'q'):
            self.deleteSelectedShape()
            event.accept()
            return
        elif txt == 'e':
            log_terminal("[Shortcut E Terminal] 切换 OBB 旋转框绘制模式")
            self.createRoShape()
            event.accept()
            return
        elif txt == 'w':
            log_terminal("[Shortcut W Terminal] 触发新建矩形框标注模式 (Draw Box)")
            self.createShape()
            event.accept()
            return
        elif txt in ('z', 'v', 'x', 'c') and self.canvas.selectedShape:
            if not self._active_adjust_keys:
                self.save_undo_state()
            self._active_adjust_keys.add(txt)
            self._apply_adjust_key_step(txt)
            if not self._adjust_timer.isActive():
                self._adjust_timer.start(30)
            event.accept()
            return
        elif txt == 'r':
            self.toggle_undo_redo()
            event.accept()
            return
        elif txt == 'a':
            self.openPrevImg()
            event.accept()
            return
        elif txt == 'd':
            self.openNextImg()
            event.accept()
            return
        super(MainWindow, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return super(MainWindow, self).keyReleaseEvent(event)
        key = event.key()
        txt = event.text().lower() if event.text() else ""
        if key == Qt.Key_Z: txt = 'z'
        elif key == Qt.Key_V: txt = 'v'
        elif key == Qt.Key_X: txt = 'x'
        elif key == Qt.Key_C: txt = 'c'
        if txt in ('z', 'v', 'x', 'c'):
            self._active_adjust_keys.discard(txt)
            if txt in ('z', 'v'):
                if hasattr(self, 'canvas') and self.canvas:
                    self.canvas._rot_start_time = None
                    self.canvas._rot_last_time = 0
            if 'x' not in self._active_adjust_keys and 'c' not in self._active_adjust_keys:
                self._size_start_time = None
            if not self._active_adjust_keys:
                self._adjust_timer.stop()
            event.accept()
            return
        super(MainWindow, self).keyReleaseEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.ActivationChange and not self.isActiveWindow():
            self._active_adjust_keys.clear()
            self._size_start_time = None
            if hasattr(self, '_adjust_timer'):
                self._adjust_timer.stop()
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas._rot_start_time = None
                self.canvas._rot_last_time = 0
        super(MainWindow, self).changeEvent(event)

    def resizeEvent(self, event):
        if self.canvas and not self.image.isNull()\
           and self.zoomMode != self.MANUAL_ZOOM:
            self.adjustScale()
        super(MainWindow, self).resizeEvent(event)

    def paintCanvas(self):
        if self.image.isNull():
            return
        self.canvas.scale = 0.01 * self.zoomWidget.value()
        self.canvas.adjustSize()
        self.canvas.update()

    def adjustScale(self, initial=False):
        value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
        self.zoomWidget.setValue(int(100 * value))

    def scaleFitWindow(self):
        """Figure out the size of the pixmap in order to fit the main widget."""
        e = 2.0  # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() - 0.0
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scaleFitWidth(self):
        # The epsilon does not seem to work too well here.
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    def closeEvent(self, event):
        if not self.mayContinue():
            event.ignore()
        settings = self.settings

        save_dir = self.defaultSaveDir if (self.defaultSaveDir and os.path.exists(self.defaultSaveDir)) else ""
        cur_dir = self.dirname or self.dirpath or self.lastOpenDir
        if not cur_dir or not os.path.exists(cur_dir):
            cur_dir = ""

        settings[SETTING_FILENAME] = self.filePath if (self.filePath and os.path.exists(self.filePath)) else ''
        settings[SETTING_LAST_OPEN_DIR] = cur_dir
        settings[SETTING_SAVE_DIR] = save_dir
        settings[SETTING_WIN_SIZE] = self.size()
        settings[SETTING_WIN_POSE] = self.pos()
        settings[SETTING_WIN_STATE] = self.saveState()
        settings[SETTING_LINE_COLOR] = self.lineColor
        settings[SETTING_FILL_COLOR] = self.fillColor
        settings[SETTING_RECENT_FILES] = self.recentFiles

        if hasattr(self, 'auto_annotate_dialog') and self.auto_annotate_dialog and self.auto_annotate_dialog.annotator.model_path:
            settings['last_model_path'] = self.auto_annotate_dialog.annotator.model_path
        elif getattr(self, '_last_model_path', None):
            settings['last_model_path'] = self._last_model_path

        settings[SETTING_AUTO_SAVE] = self.autoSaving.isChecked()
        settings[SETTING_DRAW_CORNER] = self.drawCorner.isChecked()
        settings[SETTING_PAINT_LABEL] = self.paintLabelsOption.isChecked()
        if hasattr(self, 'combo_file_sort'):
            settings['file_sort_mode'] = self.combo_file_sort.currentIndex()
        settings['save_format'] = self.save_format
        settings.save()
    ## User Dialogs ##

    def loadRecent(self, filename):
        if self.mayContinue():
            self.loadFile(filename)

    @staticmethod
    def natural_sort_key(path_str):
        """标准操作系统自然排序键 (数值递增、字母不区分大小写，与 Windows 文件夹完全一致)"""
        filename = os.path.basename(path_str)
        parts = [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', filename)]
        dir_part = os.path.dirname(path_str).lower()
        return (dir_part, parts)

    def scanAllImages(self, folderPath):
        extensions = ['.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        images = []

        for root, dirs, files in os.walk(folderPath):
            for file in files:
                if file.lower().endswith(tuple(extensions)):
                    relativePath = os.path.join(root, file)
                    path = os.path.abspath(relativePath)
                    images.append(path)

        sorted_images = sort_images_by_folder_order(images, folderPath)
        return sorted_images

    def forceRefreshCurrentDir(self):
        """强制重新扫描当前图片目录并按系统所选文件夹实时排序规则立即更新列表"""
        if not hasattr(self, 'dirname') or not self.dirname or not os.path.exists(self.dirname):
            return
        imglist = self.scanAllImages(self.dirname)
        cur_file = self.filePath
        self.fileModel.setStringList(imglist, self.dirname, self.defaultSaveDir)
        if cur_file and cur_file in imglist:
            row = imglist.index(cur_file)
            idx = self.fileModel.index(row)
            self.filesm.blockSignals(True)
            self.filesm.setCurrentIndex(idx, QItemSelectionModel.ClearAndSelect)
            self.filesm.blockSignals(False)
            self.fileListView.scrollTo(idx)
            self.statFile.setText(f'{row + 1}/{len(imglist)}')
        elif imglist:
            self.loadFile(imglist[0])
        self.fileListView.viewport().update()
        self.update_stats()

    def changeSavedirDialog(self, _value=False):
        log_terminal("[Shortcut Ctrl+R Terminal] 触发修改标注保存路径窗口")
        path = self.defaultSaveDir if (self.defaultSaveDir and os.path.exists(self.defaultSaveDir)) else (self.settings.get('last_save_dir', '') if (self.settings.get('last_save_dir', '') and os.path.exists(self.settings.get('last_save_dir', ''))) else (self.dirname if (self.dirname and os.path.exists(self.dirname)) else '.'))

        dirpath = QFileDialog.getExistingDirectory(self,
                                                       '%s - Save annotations to the directory' % __appname__, path,  QFileDialog.ShowDirsOnly
                                                       | QFileDialog.DontResolveSymlinks)

        if dirpath is not None and len(dirpath) > 1 and os.path.exists(dirpath):
            self.defaultSaveDir = dirpath
            self.settings[SETTING_SAVE_DIR] = dirpath
            self.settings['last_save_dir'] = dirpath
            self.settings.save()
            self.statusBar().showMessage('%s . Annotation will be saved to %s' %
                                         ('Change saved folder', self.defaultSaveDir))
            self.statusBar().show()

            # 修改保存路径后，立即全量重新检索对应路径下的所有标签并刷新右下角文件列表与数字统计
            if hasattr(self, 'fileModel') and self.fileModel and hasattr(self, 'dirname') and self.dirname:
                imglist = self.fileModel.stringList()
                self.fileModel.setStringList(imglist, self.dirname, self.defaultSaveDir)
                self.calculate_initial_stats()
                self.fileListView.viewport().update()

            # 重新载入当前正在标注的图片标签
            if getattr(self, 'filePath', None) and os.path.exists(self.filePath):
                self.loadFile(self.filePath)

    def openAnnotationDialog(self, _value=False):
        if self.filePath is None:
            self.errorMessage(u'Image not loaded', u'Open image first, then load the annotation file.')
            return

        path = self.defaultSaveDir if (self.defaultSaveDir and os.path.exists(self.defaultSaveDir)) else (self.dirname if (self.dirname and os.path.exists(self.dirname)) else '.')
        targetFilePath = QFileDialog.getOpenFileName(self,
                                                    '%s - Choose Annotation file' % __appname__,
                                                    path,  'Pascal XML (*.xml)')
        if targetFilePath is not None and len(targetFilePath[0]) > 0 and os.path.exists(targetFilePath[0]):
            self.loadPascalXMLByFilename(targetFilePath[0])

    def openDirDialog(self, _value=False, dirpath=None):
        if not self.mayContinue():
            return

        log_terminal("[Shortcut Ctrl+U Terminal] 触发打开图片文件夹选择窗口")
        defaultOpenDirPath = dirpath if dirpath else (self.dirname if (self.dirname and os.path.exists(self.dirname)) else (self.settings.get('last_image_dir', '') if (self.settings.get('last_image_dir', '') and os.path.exists(self.settings.get('last_image_dir', ''))) else '.'))

        targetDirPath = QFileDialog.getExistingDirectory(self,
                                                     '%s - Open Directory' % __appname__, defaultOpenDirPath,
                                                     QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        if targetDirPath and os.path.exists(targetDirPath):
            self.settings['last_image_dir'] = targetDirPath
            self.settings.save()
            self.importDirImages(targetDirPath)

    def check_folder_sort_update(self):
        """实时检测所选文件夹在 Windows 资源管理器中的排序是否被用户调整，如有变动即刻自动重新排序刷新"""
        if not hasattr(self, 'dirname') or not self.dirname or not os.path.exists(self.dirname):
            return
        from utils.folder_sort_sync import get_live_explorer_sort_columns
        cur_sort = get_live_explorer_sort_columns(self.dirname)
        if not hasattr(self, '_last_detected_explorer_sort'):
            self._last_detected_explorer_sort = cur_sort
            return
        if cur_sort != self._last_detected_explorer_sort:
            self._last_detected_explorer_sort = cur_sort
            self.refreshCurrentDir(force=True)

    def changeEvent(self, e):
        if e.type() == QEvent.ActivationChange and self.isActiveWindow():
            self.check_folder_sort_update()
        super(MainWindow, self).changeEvent(e)

    def on_directory_changed(self, path):
        # 延迟 150ms 刷新，避免外部写文件锁冲突
        QTimer.singleShot(150, self.refreshCurrentDir)

    def refreshCurrentDir(self, force=False):
        """外部图片增删或系统文件夹排序变更时，自动重新扫描并刷新列表"""
        if not hasattr(self, 'dirname') or not self.dirname or not os.path.exists(self.dirname):
            return
        imglist = self.scanAllImages(self.dirname)
        old_list = self.fileModel.stringList() if hasattr(self, 'fileModel') and self.fileModel else []
        if not force and imglist == old_list:
            return
        cur_file = self.filePath
        self.fileModel.setStringList(imglist, self.dirname, self.defaultSaveDir)
        if cur_file and cur_file in imglist:
            row = imglist.index(cur_file)
            idx = self.fileModel.index(row)
            self.filesm.blockSignals(True)
            self.filesm.setCurrentIndex(idx, QItemSelectionModel.ClearAndSelect)
            self.filesm.blockSignals(False)
            self.fileListView.scrollTo(idx)
            self.statFile.setText(f'{row + 1}/{len(imglist)}')
        elif imglist:
            self.loadFile(imglist[0])
        self.fileListView.viewport().update()
        self.update_stats()

    def importDirImages(self, dirpath, target_file=None, labels_dir=None):
        if not self.mayContinue() or not dirpath or not os.path.exists(dirpath):
            return

        self.dirname = dirpath
        self.settings['last_image_dir'] = dirpath
        self.settings[SETTING_LAST_OPEN_DIR] = dirpath

        if labels_dir and os.path.exists(labels_dir):
            self.defaultSaveDir = labels_dir
        else:
            parent = os.path.dirname(dirpath)
            candidate_labels = os.path.join(parent, 'labels')
            candidate_annos = os.path.join(parent, 'Annotations')
            if os.path.isdir(candidate_labels):
                self.defaultSaveDir = candidate_labels
            elif os.path.isdir(candidate_annos):
                self.defaultSaveDir = candidate_annos
            elif os.path.isdir(os.path.join(dirpath, 'labels')):
                self.defaultSaveDir = os.path.join(dirpath, 'labels')
            else:
                self.defaultSaveDir = dirpath
        self.settings[SETTING_SAVE_DIR] = self.defaultSaveDir
        self.settings['last_save_dir'] = self.defaultSaveDir
        self.settings.save()

        imglist = self.scanAllImages(dirpath)
        self.fileModel.setStringList(imglist, self.dirname, self.defaultSaveDir)

        self.setWindowTitle(__appname__ + ' ' + self.dirname)
        self.calculate_initial_stats()

        # 挂载/更新目录变动监控
        if hasattr(self, 'dir_watcher'):
            existing_dirs = self.dir_watcher.directories()
            if existing_dirs:
                self.dir_watcher.removePaths(existing_dirs)
            self.dir_watcher.addPath(dirpath)

        target_to_load = None
        if target_file and target_file in imglist:
            target_to_load = target_file
        elif imglist:
            target_to_load = imglist[0]

        if target_to_load:
            self.loadFile(target_to_load)
        else:
            self.resetState()
            self.canvas.setEnabled(False)
            self.fileListView.viewport().update()

    def verifyImg(self, _value=False):
         if self.filePath is not None:
            try:
                self.labelFile.toggleVerify()
            except AttributeError:
                self.saveFile()
                self.labelFile.toggleVerify()

            self.fileModel.setData(self.filesm.currentIndex(), len(self.canvas.shapes), Qt.BackgroundRole)
            self.canvas.verified = self.labelFile.verified
            self.paintCanvas()
            self.saveFile()

    def calculate_initial_stats(self):
        """打开项目时建立初始基准总标签数"""
        if hasattr(self, 'fileModel') and self.fileModel:
            self._session_initial_total = self.fileModel.getTotalBoxCount()
        else:
            self._session_initial_total = 0
        self.update_stats()

    def update_stats(self):
        """毫秒级极速更新右下角 File List 上方控制栏的数字统计 (0 毫秒纯内存计算，不读取磁盘，不发生跳动与卡顿)"""
        if not hasattr(self, 'lbl_session_count') or not hasattr(self, 'lbl_total_count'):
            return

        if not hasattr(self, 'fileModel') or not self.fileModel or self.fileModel.rowCount() == 0:
            self.lbl_session_count.setText("本次: 0")
            self.lbl_session_count.setStyleSheet("font-size: 11px; font-weight: bold; color: #15803D; background: #DCFCE7; padding: 2px 5px; border-radius: 3px; border: 1px solid #86EFAC;")
            self.lbl_total_count.setText("总计: 0")
            return

        # 同步当前打开图片在 fileModel 内存模型中的最新框数
        if hasattr(self, 'canvas') and getattr(self, 'filePath', None) and hasattr(self, 'filesm'):
            cur_idx = self.filesm.currentIndex()
            if cur_idx.isValid() and cur_idx.row() < len(self.fileModel.dispList):
                self.fileModel.dispList[cur_idx.row()][1] = len(self.canvas.shapes)

        current_total = self.fileModel.getTotalBoxCount()
        initial_total = getattr(self, '_session_initial_total', 0)
        session_delta = current_total - initial_total

        if session_delta > 0:
            self.lbl_session_count.setText(f"本次: +{session_delta}")
            self.lbl_session_count.setStyleSheet("font-size: 11px; font-weight: bold; color: #15803D; background: #DCFCE7; padding: 2px 5px; border-radius: 3px; border: 1px solid #86EFAC;")
            self.lbl_session_count.setToolTip(f"本次打开工具期间累计净新增标签框: +{session_delta} 个 (当前总计: {current_total} - 初始总计: {initial_total})")
        elif session_delta < 0:
            self.lbl_session_count.setText(f"本次: {session_delta}")
            self.lbl_session_count.setStyleSheet("font-size: 11px; font-weight: bold; color: #B91C1C; background: #FEE2E2; padding: 2px 5px; border-radius: 3px; border: 1px solid #EF4444;")
            self.lbl_session_count.setToolTip(f"本次打开工具期间累计净减少标签框: {session_delta} 个 (当前总计: {current_total} - 初始总计: {initial_total})")
        else:
            self.lbl_session_count.setText("本次: 0")
            self.lbl_session_count.setStyleSheet("font-size: 11px; font-weight: bold; color: #15803D; background: #DCFCE7; padding: 2px 5px; border-radius: 3px; border: 1px solid #86EFAC;")
            self.lbl_session_count.setToolTip(f"本次打开工具期间标签框数量与初始一致 (总计: {current_total})")

        self.lbl_total_count.setText(f"总计: {current_total}")
        self.lbl_total_count.setToolTip(f"当前项目所有已有标签框总数: {current_total} 个 (共 {self.fileModel.rowCount()} 张图片)")





    def openPrevImg(self, _value=False):
        currIndex = self.filesm.currentIndex()
        if currIndex.row() - 1 < 0:
            return False
        
        prevIndex = self.fileModel.index(currIndex.row() - 1)
      
        self.filesm.setCurrentIndex(prevIndex, QItemSelectionModel.SelectCurrent)
        log_terminal(f"[Shortcut A Terminal] 切换至上一张图片: {os.path.basename(self.filePath or '')}")

        return True

    def openNextImg(self, _value=False):
        currIndex = self.filesm.currentIndex()
        if currIndex.row() + 1 >= self.fileModel.rowCount():
            return False

        nextIndex = self.fileModel.index(currIndex.row() + 1)      
        self.filesm.setCurrentIndex(nextIndex, QItemSelectionModel.SelectCurrent)
        log_terminal(f"[Shortcut D Terminal] 切换至下一张图片: {os.path.basename(self.filePath or '')}")

    def openProjectDialog(self):
        if not self.mayContinue():
            return
        log_terminal("[Shortcut Ctrl+O Terminal] 触发打开项目总文件夹 (Open Dir)")
        default_open_dir_path = (
            self.settings.get('last_project_root', None)
            or self.settings.get('last_image_dir', None)
            or self.lastOpenDir
            or '.'
        )
        if not os.path.exists(default_open_dir_path):
            default_open_dir_path = '.'

        target_dir = QFileDialog.getExistingDirectory(
            self,
            "打开项目总文件夹 (Open Dir)",
            default_open_dir_path,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if not target_dir:
            return

        self.openProject(target_dir)

    def openProject(self, target_dir):
        if not target_dir or not os.path.isdir(target_dir):
            return

        target_dir = os.path.abspath(target_dir)
        img_dir, lbl_dir = detect_project_folders(target_dir)

        # 递归扫描选中文件夹下的所有包含图片 (全面兼顾多层子目录嵌套)
        all_imgs = self.scanAllImages(img_dir) if (img_dir and os.path.isdir(img_dir)) else []

        if not all_imgs:
            reply = QMessageBox.question(
                self,
                "未发现图片",
                f"在识别到的图片目录及子目录中:\n{img_dir}\n未发现常见格式的图片文件。\n是否仍要载入该项目？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply != QMessageBox.Yes:
                return

        # 记录项目信息与最近记录 (长期在同一位置保存不重复记录)
        self.settings['last_project_root'] = target_dir
        self.settings['last_image_dir'] = img_dir
        self.settings['last_save_dir'] = lbl_dir
        self.settings[SETTING_SAVE_DIR] = lbl_dir
        self.settings[SETTING_LAST_OPEN_DIR] = img_dir
        self.settings.save()

        self.addRecentProject(target_dir, img_dir, lbl_dir)

        # 载入图片与标签目录
        self.importDirImages(img_dir, labels_dir=lbl_dir)

        rel_img = os.path.relpath(img_dir, target_dir) if img_dir != target_dir else "."
        rel_lbl = os.path.relpath(lbl_dir, target_dir) if lbl_dir != target_dir else "."
        self.statusBar().showMessage(
            f"已打开项目 [{os.path.basename(target_dir)}] | 图片包含: [{rel_img}] (共 {len(all_imgs)} 张) | 标签关联: [{rel_lbl}]",
            8000
        )

    def openRecentProject(self):
        if not self.mayContinue():
            return
        log_terminal("[Shortcut Ctrl+Shift+O Terminal] 触发打开历史项目选择列表")
        self.updateRecentProjectsMenu()

        recent_list = self.settings.get('recent_projects', [])
        valid_items = [
            (item.get('root') if isinstance(item, dict) else item)
            for item in recent_list
            if os.path.isdir(item.get('root') if isinstance(item, dict) else item)
        ]

        if not valid_items:
            QMessageBox.information(
                self,
                "Open Recent",
                "暂无历史项目记录。\n请先使用 [Open] 打开一个项目总文件夹，后续即可在此快速选择。"
            )
            return

        btn_pos = None
        if hasattr(self, 'tools') and hasattr(self.actions, 'openRecent'):
            btn = self.tools.widgetForAction(self.actions.openRecent)
            if btn and btn.isVisible():
                btn_pos = btn.mapToGlobal(QPoint(btn.width(), 0))

        if btn_pos:
            self.menus.recentProjects.exec_(btn_pos)
        else:
            self.menus.recentProjects.exec_(QCursor.pos())

    def addRecentProject(self, root, images, labels):
        """记录项目正确处理过的 Images 和 Labels 路径组合，长期在同一位置保存不重复记录"""
        if not images or not os.path.exists(images):
            return
        recent_list = self.settings.get('recent_projects', [])
        if not isinstance(recent_list, list):
            recent_list = []

        abs_root = os.path.abspath(root) if root else os.path.abspath(images)
        abs_img = os.path.abspath(images)
        abs_lbl = os.path.abspath(labels) if labels else abs_img

        new_entry = {'root': abs_root, 'images': abs_img, 'labels': abs_lbl}

        def is_match(item):
            if not isinstance(item, dict):
                return item == abs_root or item == abs_img
            return (item.get('images') == abs_img and item.get('labels') == abs_lbl) or (item.get('root') == abs_root and item.get('images') == abs_img)

        # 若首项已经是当前位置（同一位置长期保存），更新后无需重复重载菜单
        if recent_list and is_match(recent_list[0]):
            recent_list[0] = new_entry
            return

        recent_list = [item for item in recent_list if not is_match(item)]
        recent_list.insert(0, new_entry)
        if len(recent_list) > 10:
            recent_list = recent_list[:10]
        self.settings['recent_projects'] = recent_list
        self.settings.save()
        self.updateRecentProjectsMenu()

    def openFile(self, _value=False):
        if not self.mayContinue():
            return
        log_terminal("[Shortcut Ctrl+O Terminal] 触发打开图片/文件选择窗口")
        path = self.dirname if (self.dirname and os.path.exists(self.dirname)) else (self.settings.get('last_image_dir', '') if (self.settings.get('last_image_dir', '') and os.path.exists(self.settings.get('last_image_dir', ''))) else (os.path.dirname(self.filePath) if self.filePath else '.'))
        formats = ['*.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        filters = "Image & Label files (%s)" % ' '.join(formats + ['*%s' % LabelFile.suffix])
        filename = QFileDialog.getOpenFileName(self, '%s - Choose Image or Label file' % __appname__, path, filters)
        if filename:
            if isinstance(filename, (tuple, list)):
                filename = filename[0]
            if filename and os.path.exists(filename):
                # 只有通过 Open 打开单张文件时，才默认将 image dir 与 label dir 设在同一路径下
                f_dir = os.path.dirname(filename)
                self.dirname = f_dir
                self.defaultSaveDir = f_dir
                self.settings['last_image_dir'] = f_dir
                self.settings[SETTING_SAVE_DIR] = f_dir
                self.settings.save()
                self.loadFile(filename)

            if self.filePath is not None:
                imglist = [self.filePath]
                self.fileModel.setStringList(imglist, self.dirname, self.defaultSaveDir)
                if self.fileModel.rowCount() > 0:
                    curIndex = self.fileModel.index(0)
                    self.filesm.blockSignals(True)
                    self.filesm.setCurrentIndex(curIndex, QItemSelectionModel.SelectCurrent)
                    self.filesm.blockSignals(False)
                self.calculate_initial_stats()

    def saveLocal(self, file_path):
        imgFileDir = os.path.dirname(file_path)
        imgFileName = os.path.basename(file_path)
        savedFileName = os.path.splitext(imgFileName)[0]
        savedPath = os.path.join(imgFileDir, savedFileName)
        self._saveFile(savedPath)

    def saveFile(self, _value=False, prompt_empty=False):
        if hasattr(self, 'canvas') and len(self.canvas.shapes) == 0 and getattr(self, 'filePath', None) and prompt_empty:
            reply = QMessageBox.question(
                self,
                "保存空标注确认",
                f"当前图片 [{os.path.basename(self.filePath)}] 未绘制任何标注框。\n是否确认保存为空标注（负样本/背景图）文件？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply != QMessageBox.Yes:
                return False

        if self.defaultSaveDir is not None and len(self.defaultSaveDir):
            if self.filePath:
                if self.dirname is not None and os.path.exists(self.dirname):
                    relname = os.path.relpath(self.filePath, self.dirname)
                    relname = os.path.splitext(relname)[0]
                    savedPath = os.path.join(self.defaultSaveDir, relname)
                    # 确保目标目录存在（支持空标签文件夹自动创建）
                    saved_dir = os.path.dirname(savedPath)
                    if saved_dir and not os.path.exists(saved_dir):
                        try:
                            os.makedirs(saved_dir, exist_ok=True)
                        except Exception:
                            pass
                    self._saveFile(savedPath)
                else:
                    self.saveLocal(self.filePath)
        else:
            self.saveLocal(self.filePath)
        return True

    def removeFile(self):
        if self.defaultSaveDir is not None and len(self.defaultSaveDir):
            if self.filePath:
                relname = os.path.relpath(self.filePath, self.dirname)
                relname = os.path.splitext(relname)[0]
                savedPath = os.path.join(self.defaultSaveDir, relname)
        else:
            imgFileDir = os.path.dirname(self.filePath)
            imgFileName = os.path.basename(self.filePath)
            savedFileName = os.path.splitext(imgFileName)[0]
            savedPath = os.path.join(imgFileDir, savedFileName)
        base_path = os.path.splitext(savedPath)[0]
        for ext in ('.xml', '.txt', '.json'):
            target_p = base_path + ext
            if os.path.exists(target_p):
                try:
                    os.remove(target_p)
                except Exception:
                    pass

    def saveFileAndRenderList(self, _value=False):
        """Save功能直接保存当前做的所有任务，不弹另存为对话框"""
        self.saveFile(_value=_value, prompt_empty=False)
        cur = self.filesm.currentIndex()
        if cur.isValid():
            self.fileModel.setData(cur, len(self.canvas.shapes), Qt.BackgroundRole)
        self.statusBar().showMessage(f"已成功保存当前标注: {os.path.basename(self.filePath or '')}", 3000)
        log_terminal(f"[Shortcut Ctrl+S] 已保存标注: {os.path.basename(self.filePath or '')}")

    def _saveFile(self, annotationFilePath):
        if annotationFilePath and self.saveLabels(annotationFilePath):
            self.setClean()
            self.current_annotation_format = self.save_format
            from libs.annotation_io import get_format_ext
            ext = get_format_ext(self.save_format)
            saved_final_path = os.path.splitext(annotationFilePath)[0] + ext
            self.current_annotation_file = saved_final_path

            # 实现标签格式的替换：清理并替换同名其他旧格式标注文件（如 .xml / .txt / .json），避免格式冗余和读取冲突
            base_stem = os.path.splitext(annotationFilePath)[0]
            for old_ext in ('.xml', '.txt', '.json'):
                if old_ext.lower() != ext.lower():
                    old_cand = base_stem + old_ext
                    if os.path.isfile(old_cand):
                        try:
                            os.remove(old_cand)
                            log_terminal(f"[Format Replace Terminal] 已替换并移除旧格式标注文件: {old_cand}")
                        except Exception as e:
                            log_terminal(f"[Format Replace Error] 移除旧格式标注文件失败: {e}")

            # 若曾记录跨目录原格式标注文件，一并清理
            if hasattr(self, '_old_annotation_file') and self._old_annotation_file:
                if os.path.isfile(self._old_annotation_file) and os.path.abspath(self._old_annotation_file) != os.path.abspath(saved_final_path):
                    try:
                        os.remove(self._old_annotation_file)
                        log_terminal(f"[Format Replace Terminal] 已替换并移除原格式文件: {self._old_annotation_file}")
                    except Exception:
                        pass
                self._old_annotation_file = None

            self.statusBar().showMessage(f"已成功替换并保存为 [{self.save_format}]: {saved_final_path}", 3000)
            self.statusBar().show()
            self.markFileSavedInList(self.filePath, len(self.canvas.shapes))
            if hasattr(self, '_xml_stats_cache'):
                self._xml_stats_cache.pop(annotationFilePath, None)
                self._xml_stats_cache.pop(annotationFilePath + XML_EXT, None)
                if self.filePath:
                    self._xml_stats_cache.pop(self.filePath, None)
            self.update_stats()

            # 记录正确处理保存过的图片与标签路径组合 (长期在同一位置保存不重复记录)
            if hasattr(self, 'dirname') and self.dirname and hasattr(self, 'defaultSaveDir') and self.defaultSaveDir:
                root_cand = self.settings.get('last_project_root', self.dirname)
                self.addRecentProject(root_cand, self.dirname, self.defaultSaveDir)



    def closeFile(self, _value=False):
        if not self.mayContinue():
            return
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)

    def resetAll(self):
        self.settings.reset()
        self.close()
        proc = QProcess()
        proc.startDetached(sys.executable, [os.path.abspath(__file__)])

    def mayContinue(self):
        return not (self.dirty and not self.discardChangesDialog())

    def discardChangesDialog(self):
        """文件未保存时提供【保存】、【放弃更改】与【取消】"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("未保存提醒 (Unsaved Changes)")
        msg_box.setText("当前图片有尚未保存的标注修改，请选择操作：")
        btn_save = msg_box.addButton("保存 (Save)", QMessageBox.AcceptRole)
        btn_discard = msg_box.addButton("放弃更改 (Discard)", QMessageBox.DestructiveRole)
        btn_cancel = msg_box.addButton("取消 (Cancel)", QMessageBox.RejectRole)
        msg_box.setDefaultButton(btn_save)
        msg_box.exec_()

        clicked = msg_box.clickedButton()
        if clicked == btn_save:
            self.saveFile()
            return True
        elif clicked == btn_discard:
            self.setClean()
            return True
        else:
            return False

    def errorMessage(self, title, message):
        return QMessageBox.critical(self, title,
                                    '<p><b>%s</b></p>%s' % (title, message))

    def currentPath(self):
        return os.path.dirname(self.filePath) if self.filePath else '.'

    def save_undo_state(self):
        """保存当前图片标注框状态快照至撤销栈 (每张图片独立维护，最多 50 步)"""
        if getattr(self, '_is_restoring_undo', False):
            return
        if not hasattr(self, 'image_undo_stacks'):
            self.image_undo_stacks = {}
        if not hasattr(self, 'image_redo_stacks'):
            self.image_redo_stacks = {}

        cur_file = self.filePath if self.filePath else "__default__"
        if cur_file not in self.image_undo_stacks:
            self.image_undo_stacks[cur_file] = []
        if cur_file not in self.image_redo_stacks:
            self.image_redo_stacks[cur_file] = []

        snapshot = [s.copy() for s in self.canvas.shapes]
        self.image_undo_stacks[cur_file].append(snapshot)
        if len(self.image_undo_stacks[cur_file]) > 50:
            self.image_undo_stacks[cur_file].pop(0)
        self.image_redo_stacks[cur_file].clear()

    def restore_shapes_snapshot(self, snapshot):
        """用快照完全同步重构 Canvas 与 右侧 Label 列表，保证 100% 同步"""
        self._is_restoring_undo = True
        try:
            self.canvas.deleteAll()
            self.labelModel.clear()
            self.ShapeItemDict.clear()
            self.ItemShapeDict.clear()

            restored_shapes = [s.copy() for s in snapshot]
            self.canvas.loadShapes(restored_shapes)

            for shape in restored_shapes:
                shape.paintLabel = self.paintLabelsOption.isChecked()
                item0 = HashableQStandardItem(shape.label)
                item1 = QStandardItem(shape.extra_label)
                color = generateColorByText(shape.label)
                item0.setBackground(color)
                item1.setBackground(color)
                self.labelModel.appendRow([item0, item1])
                self.ShapeItemDict[shape] = item0
                self.ItemShapeDict[item0] = shape

            self.update_label_list_numbers()

            if restored_shapes:
                self.canvas.selectShape(restored_shapes[-1])
                self.shapeSelectionChanged(True)
            else:
                self.shapeSelectionChanged(False)

            self.canvas.update()
            self.setDirty()
        finally:
            self._is_restoring_undo = False

    def toggle_undo_redo(self):
        """按下 R 键：点击一次回退到上次操作(Undo)，再次点击取消回退(Redo)，循环往复"""
        cur_file = self.filePath if self.filePath else "__default__"
        undo_st = self.image_undo_stacks.get(cur_file, []) if hasattr(self, 'image_undo_stacks') else []
        redo_st = self.image_redo_stacks.get(cur_file, []) if hasattr(self, 'image_redo_stacks') else []

        last_action = getattr(self, '_last_r_toggle_action', 'redo')
        if last_action == 'undo' and redo_st:
            self.redo_shape_action()
            self._last_r_toggle_action = 'redo'
            log_terminal("[Shortcut R Terminal] R 快捷键循环切换: 取消回退 (Redo)")
        elif undo_st:
            self.undo_shape_action()
            self._last_r_toggle_action = 'undo'
            log_terminal("[Shortcut R Terminal] R 快捷键循环切换: 回退到上次操作 (Undo)")
        elif redo_st:
            self.redo_shape_action()
            self._last_r_toggle_action = 'redo'
            log_terminal("[Shortcut R Terminal] R 快捷键循环切换: 取消回退 (Redo)")
        else:
            # 当前图片无操作，尝试触发返回上一张图片
            self.undo_shape_action()

    def undo_shape_action(self):
        """
        按下 Ctrl+Z 撤销操作:
        1. 若当前图片有操作历史，回退到当前图片上次操作前的状态
        2. 若当前图片未进行任何操作（或撤销栈已空），自动返回上一张图片并回退其最后一次操作
        """
        if not hasattr(self, 'image_undo_stacks'):
            self.image_undo_stacks = {}
        if not hasattr(self, 'image_redo_stacks'):
            self.image_redo_stacks = {}
        if not hasattr(self, 'image_navigation_history'):
            self.image_navigation_history = []

        cur_file = self.filePath if self.filePath else "__default__"
        current_stack = self.image_undo_stacks.get(cur_file, [])

        # 分支 1: 当前图片撤销栈非空，回退当前图片的操作
        if current_stack:
            if cur_file not in self.image_redo_stacks:
                self.image_redo_stacks[cur_file] = []

            current_snapshot = [s.copy() for s in self.canvas.shapes]
            self.image_redo_stacks[cur_file].append(current_snapshot)

            prev_snapshot = current_stack.pop()
            self.restore_shapes_snapshot(prev_snapshot)

            msg = f"[Shortcut Ctrl+Z] 已撤销当前图片的操作 (剩余撤销步数: {len(current_stack)})"
            self.statusBar().showMessage(msg, 3000)
            log_terminal(msg)
            return

        # 分支 2: 当前图片未进行任何操作，或者当前图片的撤销栈已撤完 -> 自动返回上一张图片
        while self.image_navigation_history and self.image_navigation_history[-1] == self.filePath:
            self.image_navigation_history.pop()

        if not self.image_navigation_history:
            msg = "[Shortcut Ctrl+Z] 提示: 当前图片与历史图片均无可撤销的操作"
            self.statusBar().showMessage(msg, 3000)
            log_terminal(msg)
            return

        prev_file = self.image_navigation_history.pop()
        if not os.path.exists(prev_file):
            msg = f"[Shortcut Ctrl+Z] 提示: 历史图片路径不存在: {prev_file}"
            self.statusBar().showMessage(msg, 3000)
            log_terminal(msg)
            return

        # 加载上一张图片
        log_terminal(f"[Shortcut Ctrl+Z] 当前图片无操作，正在返回上一张图片: {os.path.basename(prev_file)} ...")
        self.loadFile(prev_file)

        # 检查上一张图片是否有操作历史
        prev_stack = self.image_undo_stacks.get(prev_file, [])
        if prev_stack:
            if prev_file not in self.image_redo_stacks:
                self.image_redo_stacks[prev_file] = []
            self.image_redo_stacks[prev_file].append([s.copy() for s in self.canvas.shapes])
            prev_snapshot = prev_stack.pop()
            self.restore_shapes_snapshot(prev_snapshot)
            msg = f"[Shortcut Ctrl+Z] 已返回上一张图片 [{os.path.basename(prev_file)}] 并回退到其上次操作前的状态"
        else:
            msg = f"[Shortcut Ctrl+Z] 已返回上一张图片 [{os.path.basename(prev_file)}]"

        self.statusBar().showMessage(msg, 3000)
        log_terminal(msg)

    def redo_shape_action(self):
        """按下 Ctrl+Shift+Z 重做上一步撤销的操作"""
        if not hasattr(self, 'image_redo_stacks'):
            self.image_redo_stacks = {}
        if not hasattr(self, 'image_undo_stacks'):
            self.image_undo_stacks = {}

        cur_file = self.filePath if self.filePath else "__default__"
        current_redo = self.image_redo_stacks.get(cur_file, [])

        if not current_redo:
            self.statusBar().showMessage("提示: 当前图片重做栈为空，无可重做操作", 3000)
            log_terminal("[Shortcut Ctrl+Shift+Z] 提示: 当前图片没有可重做的操作")
            return

        if cur_file not in self.image_undo_stacks:
            self.image_undo_stacks[cur_file] = []

        current_snapshot = [s.copy() for s in self.canvas.shapes]
        self.image_undo_stacks[cur_file].append(current_snapshot)

        next_snapshot = current_redo.pop()
        self.restore_shapes_snapshot(next_snapshot)

        msg = f"[Shortcut Ctrl+Shift+Z] 已成功重做操作 (剩余重做步数: {len(current_redo)})"
        self.statusBar().showMessage(msg, 3000)
        log_terminal(msg)
        log_terminal(msg)

    def copySelectedShapeToClipboard(self):
        """按下 Ctrl+C 复制选中标注框到剪贴板"""
        if self.canvas.selectedShapes:
            self.clipboard_shapes = [s.copy() for s in self.canvas.selectedShapes]
        elif self.canvas.selectedShape:
            self.clipboard_shapes = [self.canvas.selectedShape.copy()]
        else:
            self.clipboard_shapes = []
        if self.clipboard_shapes:
            msg = f"[Shortcut Ctrl+C Terminal] 已成功复制 {len(self.clipboard_shapes)} 个标注框到剪贴板"
            self.statusBar().showMessage(msg, 3000)
            log_terminal(msg)
        else:
            log_terminal("[Shortcut Ctrl+C Terminal] 提示: 当前未选中任何标注框进行复制")

    def cutSelectedShapeToClipboard(self):
        """按下 Ctrl+X 剪切选中标注框"""
        self.copySelectedShapeToClipboard()
        if hasattr(self, 'clipboard_shapes') and self.clipboard_shapes:
            self.save_undo_state()
            self.deleteSelectedShape()
            log_terminal("[Shortcut Ctrl+X Terminal] 已成功剪切选中的标注框")

    def pasteShapeFromClipboard(self):
        """按下 Ctrl+V 粘贴剪贴板中的标注框 (支持跨图粘贴)"""
        if not hasattr(self, 'clipboard_shapes') or not self.clipboard_shapes:
            log_terminal("[Shortcut Ctrl+V Terminal] 提示: 剪贴板为空")
            return
        self.save_undo_state()
        pasted = []
        for s in self.clipboard_shapes:
            new_shape = s.copy()
            new_shape.moveBy(QPointF(10, 10))
            self.addLabel(new_shape)
            self.canvas.shapes.append(new_shape)
            pasted.append(new_shape)
        if pasted:
            self.canvas.selectedShapes = pasted
            self.canvas.selectedShape = pasted[-1]
            self.canvas.update()
            self.setDirty()
            msg = f"[Shortcut Ctrl+V Terminal] 已成功粘贴 {len(pasted)} 个标注框"
            self.statusBar().showMessage(msg, 3000)
            log_terminal(msg)

    def deleteSelectedShape(self):
        if getattr(self, '_is_deleting_shape', False):
            return
        self._is_deleting_shape = True
        try:
            # 1. 安全关闭右侧正在编辑的任何下拉框/输入框，避免 C++ 析构异常
            if hasattr(self, 'labelList') and self.labelList:
                try:
                    cur = self.labelList.currentIndex()
                    if cur.isValid():
                        self.labelList.closePersistentEditor(cur)
                        col0 = self.labelModel.index(cur.row(), 0)
                        self.labelList.closePersistentEditor(col0)
                    self.labelList.clearFocus()
                except Exception:
                    pass
            self.canvas.setFocus(True)

            # 2. 如果 canvas 尚未选定 shape，优先选用画布当前预选/悬停框 (hShape) 直接删除
            if not self.canvas.selectedShape and not self.canvas.selectedShapes:
                if self.canvas.hShape:
                    self.canvas.selectShape(self.canvas.hShape)
                else:
                    selected_indexes = self.labelList.selectedIndexes()
                    if selected_indexes:
                        for idx in selected_indexes:
                            item0 = self.labelModel.itemFromIndex(self.labelModel.index(idx.row(), 0))
                            if item0 and item0 in self.ItemShapeDict:
                                shape = self.ItemShapeDict[item0]
                                self.canvas.selectShape(shape)
                                break
                    else:
                        curr = self.labelsm.currentIndex() if hasattr(self, 'labelsm') else self.labelList.currentIndex()
                        if curr.isValid() and curr.row() >= 0:
                            item0 = self.labelModel.itemFromIndex(self.labelModel.index(curr.row(), 0))
                            if item0 and item0 in self.ItemShapeDict:
                                shape = self.ItemShapeDict[item0]
                                self.canvas.selectShape(shape)

            self.save_undo_state()
            # 记录删除前的行号，便于删除后自动选中下一个
            pre_delete_row = -1
            if self.canvas.selectedShape and self.canvas.selectedShape in self.ShapeItemDict:
                item0 = self.ShapeItemDict[self.canvas.selectedShape]
                idx = self.labelModel.indexFromItem(item0)
                if idx.isValid():
                    pre_delete_row = idx.row()

            deleted = self.canvas.deleteSelected()
            if deleted:
                for shape in deleted:
                    self.remLabel(shape)
                self.setDirty()
                if self.noShapes():
                    for action in self.actions.onShapesPresent:
                        action.setEnabled(False)
                    self.resetBackSample()
                else:
                    # 删除后自动选中下一个标签框
                    total_rows = self.labelModel.rowCount()
                    if total_rows > 0:
                        next_row = min(pre_delete_row, total_rows - 1)
                        if next_row < 0:
                            next_row = 0
                        next_idx = self.labelModel.index(next_row, 0)
                        next_item = self.labelModel.itemFromIndex(next_idx)
                        if next_item and next_item in self.ItemShapeDict:
                            next_shape = self.ItemShapeDict[next_item]
                            mouse_is_down = (QApplication.mouseButtons() != Qt.NoButton)
                            if not mouse_is_down:
                                self.canvas.selectShape(next_shape)
                            else:
                                self.canvas.deSelectShape()
                            self.labelList.selectRow(next_row)
                            self.shapeSelectionChanged(not mouse_is_down)
                if hasattr(self, 'filesm') and self.filesm:
                    cur = self.filesm.currentIndex()
                    if cur.isValid():
                        self.fileModel.setData(cur, len(self.canvas.shapes), Qt.BackgroundRole)
                        self.fileListView.viewport().update()
                msg = f"[Shortcut Q/Del Terminal] 已成功删除当前选中标注框 ({len(deleted)} 个)"
                self.statusBar().showMessage(msg, 3000)
                log_terminal(msg)
                self.update_stats()
            else:
                log_terminal("[Shortcut Q/Del Terminal] 提示: 当前未选中任何标注框 (请先在画布或列表中点击选中要删除的框)")
        finally:
            self._is_deleting_shape = False

    def labelAsBackground(self):
        self.remAllLabels()
        self.setDirty()
        self.setBackSample()
        self.update_stats()


    def deleteLabel(self):
        self.remAllLabels()
        self.setDirty()
        self.resetBackSample()

    def copyShape(self):
        self.canvas.endMove(copy=True)
        self.addLabel(self.canvas.selectedShape)
        self.setDirty()

    def moveShape(self):
        self.canvas.endMove(copy=False)
        self.setDirty()

    def loadPredefinedClasses(self, predefClassesFile=None):
        if not hasattr(self, 'labelHist') or self.labelHist is None:
            self.labelHist = []

        candidates = []
        if predefClassesFile and isinstance(predefClassesFile, str) and os.path.isfile(predefClassesFile):
            candidates.append(predefClassesFile)
        elif hasattr(self, 'settings') and self.settings:
            saved_file = self.settings.get('current_label_file', None)
            if saved_file and os.path.isfile(saved_file):
                candidates.append(saved_file)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(base_dir, "data", "predefined_classes.txt"))
        candidates.append(os.path.join(base_dir, "data", "predefined_classes1.txt"))
        candidates.append(os.path.join(base_dir, "data", "predefined_classes2.txt"))
        candidates.append(os.path.join(os.getcwd(), "data", "predefined_classes.txt"))
        if hasattr(sys, '_MEIPASS'):
            candidates.append(os.path.join(sys._MEIPASS, "data", "predefined_classes.txt"))

        found_path = None
        for p in candidates:
            if p and os.path.exists(p) and os.path.isfile(p):
                found_path = p
                break

        if not found_path:
            data_dir = os.path.join(base_dir, "data")
            if os.path.isdir(data_dir):
                for f in sorted(os.listdir(data_dir)):
                    if f.lower().endswith(".txt"):
                        fp = os.path.join(data_dir, f)
                        if os.path.isfile(fp):
                            found_path = fp
                            break

        if found_path:
            self.current_label_file = found_path
            self.labelHist = []
            with codecs.open(found_path, 'r', 'utf8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and line not in self.labelHist:
                        self.labelHist.append(line)

        if self.labelHist:
            self.default_label = self.labelHist[0]

        if hasattr(self, 'labelDialog') and self.labelDialog:
            self.labelDialog.updateData(
                self.labelHist,
                default_label=getattr(self, 'default_label', None),
                current_file=getattr(self, 'current_label_file', None)
            )
        if hasattr(self, 'labelList') and self.labelList:
            self.labelList.updateLabelList(self.labelHist)

    def loadPascalXMLByFilename(self, xmlPath):
        if self.filePath is None:
            return None
        if os.path.isfile(xmlPath) is False:
            return None

        tVocParseReader = PascalVocReader(xmlPath)
        shapes = tVocParseReader.getShapes()
        self.loadLabels(shapes)
        self.canvas.verified = tVocParseReader.verified
        return tVocParseReader

    def togglePaintLabelsOption(self):
        paintLabelsOptionChecked = self.paintLabelsOption.isChecked()
        for shape in self.canvas.shapes:
            shape.paintLabel = paintLabelsOptionChecked

    def exportAsYOLOImpl(self, obb=False):
        xml_files = find_matching_files(self.defaultSaveDir, self.dirname)

        label_map = {}
        all_shapes_map = {}
        label_count = 0
        for xfn in xml_files:
            xfn_full = os.path.join(self.defaultSaveDir, xfn)
            tVocParseReader = PascalVocReader(xfn_full)
            shapes = tVocParseReader.getShapes()
            imgw, imgh, imgdepth = tVocParseReader.getSize()
            img_fn = tVocParseReader.getImageFileName()

            all_shapes_map[img_fn] = {
                "height": imgh,
                "width": imgw,
                "bboxes": []
            }
            for si in shapes:
                if si[0] not in label_map:
                    label_map[si[0]] = label_count
                    label_count += 1
                is_rot = 0 if len(si) < 7 else int(si[5])
                if obb:
                    si_dict = {
                        "class": si[0],
                        "is_rot": is_rot,
                        "x0": si[1][0][0],
                        "y0": si[1][0][1],
                        "x1": si[1][1][0],
                        "y1": si[1][1][1],
                        "x2": si[1][2][0],
                        "y2": si[1][2][1],
                        "x3": si[1][3][0],
                        "y3": si[1][3][1],
                    }
                else:
                    if is_rot:
                        xmin = int(min(si[1][0][0], si[1][1][0], si[1][2][0], si[1][3][0]))
                        ymin = int(min(si[1][0][1], si[1][1][1], si[1][2][1], si[1][3][1]))
                        xmax = int(max(si[1][0][0], si[1][1][0], si[1][2][0], si[1][3][0]))
                        ymax = int(max(si[1][0][1], si[1][1][1], si[1][2][1], si[1][3][1]))
                        si_dict = {
                            "class": si[0],
                            "is_rot": is_rot,
                            "x0": xmin,
                            "y0": ymin,
                            "x1": 0,
                            "y1": 0,
                            "x2": xmax,
                            "y2": ymax,
                            "x3": 0,
                            "y3": 0,
                        }
                    else:
                        si_dict = {
                            "class": si[0],
                            "is_rot": is_rot,
                            "x0": si[1][0][0],
                            "y0": si[1][0][1],
                            "x1": si[1][1][0], # 0
                            "y1": si[1][1][1], # 0
                            "x2": si[1][2][0],
                            "y2": si[1][2][1],
                            "x3": si[1][3][0], # 0
                            "y3": si[1][3][1], # 0
                        }

                all_shapes_map[img_fn]["bboxes"].append(si_dict)

        defaultOpenDirPath = '.'
        save_dir_path = QFileDialog.getExistingDirectory(self,
                                                     '%s - Open Directory' % __appname__, defaultOpenDirPath,
                                                     QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        if save_dir_path is None:
            return

        cvt_lbidata_rotdet(self.dirname, all_shapes_map, label_map,
                           save_dir_path, tag='train', format='rotbox' if obb else 'box')
        cvt_lbidata_rotdet(self.dirname, all_shapes_map, label_map,
                           save_dir_path, tag='val', format='rotbox' if obb else 'box')

        yml_fn = os.path.join(save_dir_path, 'train.yaml')

        ydat = OrderedDict(path=save_dir_path,
                        train='train_list.txt',
                        val='val_list.txt',
                        nc=len(label_map),
                        names=[k for k in label_map.keys()])

        with open(yml_fn, 'w') as fy:
            yaml.dump(ydat, fy,
                    Dumper=yamlloader.ordereddict.CDumper)
    def exportAsYOLO(self, _value=False):
        self.exportAsYOLOImpl(obb=False)


    def exportAsYOLOOBB(self, _value=False):
        self.exportAsYOLOImpl(obb=True)


def find_matching_files(dir_a, dir_b):
    supported_extensions = tuple(['.%s' % fmt.data().decode("ascii").lower() for fmt 
                                  in QImageReader.supportedImageFormats()])
    xml_files = set()
    for file in os.listdir(dir_b):
        if file.endswith(".xml"):
            xml_files.add(os.path.splitext(file)[0])

    result = []
    for file in os.listdir(dir_a):
        if os.path.splitext(file)[0] in xml_files and file.lower().endswith(supported_extensions):
            result.append(os.path.splitext(file)[0] + ".xml")  # 添加对应的xml文件名到结果列表

    return result

def inverted(color):
    return QColor(*[255 - v for v in color.getRgb()])


def read(filename, default=None):
    try:
        with open(filename, 'rb') as f:
            return f.read()
    except:
        return default


def get_main_app(argv=[]):
    """
    Standard boilerplate Qt application code.
    Do everything but app.exec_() -- so that we can test the application in one thread
    """
    app = QApplication(argv)
    
    app.setApplicationName(__appname__)
    
    # 启用 Windows 独立任务栏图标 AppID
    if platform.system() == 'Windows':
        try:
            import ctypes
            myappid = 'chinakook.labelimg2.workstation.2.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app_icon = newIcon("app.ico")
    if app_icon.isNull():
        app_icon = newIcon("app.png")
    if app_icon.isNull():
        app_icon = newIcon("labelImg2.ico")
    if app_icon.isNull():
        app_icon = newIcon("labelImg2.png")
    app.setWindowIcon(app_icon)

    
    # Usage : labelImg.py image predefClassFile saveDir
    img_arg = None
    class_arg = os.path.join(os.path.dirname(sys.argv[0]), 'data', 'predefined_classes.txt')
    save_arg = None

    if len(argv) >= 2:
        cand = argv[1]
        if cand and not cand.startswith(('-', '/')) and os.path.exists(cand):
            img_arg = cand
    if len(argv) >= 3:
        cand = argv[2]
        if cand and not cand.startswith(('-', '/')) and os.path.exists(cand):
            class_arg = cand
    if len(argv) >= 4:
        cand = argv[3]
        if cand and not cand.startswith(('-', '/')) and os.path.exists(cand):
            save_arg = cand

    win = MainWindow(img_arg, class_arg, save_arg)
    win.setWindowIcon(app_icon)
    win.show()
    return app, win



def main():
    '''construct main app and run it'''
    app, _win = get_main_app(sys.argv)
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
