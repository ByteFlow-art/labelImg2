#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import

import codecs
import os
import platform
import re
import sys
import subprocess
import math
import yaml, yamlloader
from functools import partial
from collections import defaultdict, OrderedDict

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

from ui.train_dialog import TrainDialog
from ui.auto_annotate_dialog import AutoAnnotateDialog

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
        self.labelDialog = LabelDialog(parent=self, listItem=self.labelHist)

        self.ShapeItemDict = {}
        self.ItemShapeDict = {}

        labellistLayout = QVBoxLayout()
        labellistLayout.setContentsMargins(0, 0, 0, 0)

        self.default_label = self.labelHist[0]

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

        self.prevButton = QToolButton()
        self.nextButton = QToolButton()
        self.playButton = QToolButton()
        self.prevButton.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.nextButton.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.playButton.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.controlButtonsLayout = QHBoxLayout()
        self.controlButtonsLayout.setAlignment(Qt.AlignLeft)
        self.controlButtonsLayout.addWidget(self.prevButton)
        self.controlButtonsLayout.addWidget(self.nextButton)
        self.controlButtonsLayout.addWidget(self.playButton)

        filelistLayout.addLayout(self.controlButtonsLayout)

        filelistLayout.addWidget(self.fileListView)
        fileListContainer = QWidget()
        fileListContainer.setLayout(filelistLayout)

        self.filedock = QDockWidget(u'File List', self)
        self.filedock.setObjectName(u'Files')
        self.filedock.setWidget(fileListContainer)

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

        open = action('&Open', self.openFile,
                      'Ctrl+O', 'icon_open_file.svg', u'Open image file')

        opendir = action('&Images Dir', self.openDirDialog,
                         'Ctrl+u', 'icon_images_dir.svg', u'Select images directory')

        changeSavedir = action('&Labels Dir', self.changeSavedirDialog,
                               'Ctrl+r', 'icon_labels_dir.svg', u'Select labels save directory')



        verify = action('&Verify Image', self.verifyImg,
                        'space', 'downloaded.svg', u'Verify Image')

        save = action('&Save', self.saveFileAndRenderList,
                      'Ctrl+S', 'save.svg', u'Save labels to file', enabled=False)

        saveAs = action('&Save As', self.saveFileAs,
                        'Ctrl+Shift+S', 'save.svg', u'Save labels to a different file', enabled=False)

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
        self.actions = struct(save=save, saveAs=saveAs, open=open, close=close, resetAll = resetAll,
                              create=create, createSo=createSo, createRo=createRo, delete=delete, 
                              labelAsBack=labelAsBack, deleteLabel=deleteLabel, edit=edit, copy=copy,
                              zoom=zoom, zoomIn=zoomIn, zoomOut=zoomOut, zoomOrg=zoomOrg,
                              fitWindow=fitWindow, fitWidth=fitWidth, play=play,
                              zoomActions=zoomActions,
                              fileMenuActions=(
                                  open, opendir, save, saveAs, close, resetAll, quit),
                              beginner=(),
                              editMenu=(edit, copy, delete,
                                        None),
                              beginnerContext=(create, createSo, createRo, copy, delete, labelAsBack, deleteLabel),
                              onLoadActive=(
                                  close, create),
                              onShapesPresent=(saveAs,))

        # 保存文件格式类型子菜单
        saveFormatMenu = QMenu('保存文件格式 (Format)', self)
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

        self.menus = struct(
            file=self.menu('&File'),
            edit=self.menu('&Edit'),
            view=self.menu('&View'),
            help=self.menu('&Help'),
            recentFiles=QMenu('Open &Recent'),
            saveFormat=saveFormatMenu,
            labelList=labelMenu)

        # 子菜单组图标
        self.menus.recentFiles.setIcon(newIcon('icon_open_file.svg'))

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
                   (open, opendir, changeSavedir, self.menus.saveFormat, self.menus.recentFiles, 
                    verify, save, saveAs, resetAll, quit))

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
        self.actions.beginner = (open, opendir, changeSavedir, verify, save, None, create, createSo, createRo, copy, delete, None,
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
        saveDir = settings.get(SETTING_SAVE_DIR, None)
        self.lastOpenDir = settings.get(SETTING_LAST_OPEN_DIR, None)
        if self.defaultSaveDir is None and saveDir is not None and os.path.exists(saveDir):
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

        if last_model and os.path.exists(last_model):
            def restore_last_model():
                if not hasattr(self, 'auto_annotate_dialog') or self.auto_annotate_dialog is None:
                    self.auto_annotate_dialog = AutoAnnotateDialog(main_window_ref=self, parent=self)
                self.auto_annotate_dialog.refresh_model_selector()
                self.auto_annotate_dialog.load_model(last_model)
                log_terminal(f"[Startup State] 已恢复上次加载模型: {os.path.basename(last_model)}")
            self.queueEvent(restore_last_model)

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
        self.canvas.menus[0].clear()
        addActions(self.canvas.menus[0], menu)
        self.menus.edit.clear()
        actions = (self.actions.create, self.actions.createSo, self.actions.createRo) 
        addActions(self.menus.edit, actions + self.actions.editMenu)

    def setDirty(self):
        self.dirty = True
        self.actions.save.setEnabled(True)

    def setBackSample(self):
        self.back_sample = True

    def resetBackSample(self):
        self.back_sample = False

    def set_save_format(self, format_name):
        self.save_format = format_name
        self.settings['save_format'] = format_name
        self.settings.save()
        msg = f"[Save Format Terminal] 标注保存文件格式类型已切换为: {format_name}"
        self.statusBar().showMessage(msg, 3000)
        log_terminal(msg)
        if hasattr(self, 'saveFormatActions'):
            for act in self.saveFormatActions:
                act.setChecked(act.text() == format_name)
        if hasattr(self, 'auto_annotate_dialog') and self.auto_annotate_dialog is not None:
            if hasattr(self.auto_annotate_dialog, 'combo_save_format'):
                idx = self.auto_annotate_dialog.combo_save_format.findText(format_name)
                if idx >= 0:
                    self.auto_annotate_dialog.combo_save_format.blockSignals(True)
                    self.auto_annotate_dialog.combo_save_format.setCurrentIndex(idx)
                    self.auto_annotate_dialog.combo_save_format.blockSignals(False)

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
            self.train_dialog = TrainDialog(default_image_dir=image_dir, default_xml_dir=xml_dir, parent=self)
            self.train_dialog.model_trained_signal.connect(self.onYOLOModelTrained)
        self.train_dialog.show()
        self.train_dialog.raise_()
        self.train_dialog.activateWindow()

    def onYOLOModelTrained(self, best_pt_path):
        if not hasattr(self, 'auto_annotate_dialog') or self.auto_annotate_dialog is None:
            self.auto_annotate_dialog = AutoAnnotateDialog(main_window_ref=self, parent=self)
        self.auto_annotate_dialog.load_model(best_pt_path)
        self.auto_annotate_dialog.show()

    def openYOLOAutoAnnotateDialog(self):
        if not hasattr(self, 'auto_annotate_dialog') or self.auto_annotate_dialog is None:
            self.auto_annotate_dialog = AutoAnnotateDialog(main_window_ref=self, parent=self)
        self.auto_annotate_dialog.sync_paths_from_main_window()
        self.auto_annotate_dialog.show()
        self.auto_annotate_dialog.raise_()
        self.auto_annotate_dialog.activateWindow()

    def auto_annotate_current_image_quick(self):
        """按下快捷键 S 或点击【自动标注当前图 (S)】触发 (无弹窗，终端打印)"""
        if not hasattr(self, 'auto_annotate_dialog') or self.auto_annotate_dialog is None:
            self.auto_annotate_dialog = AutoAnnotateDialog(main_window_ref=self, parent=self)
        # 模型标注前保存完整撤销快照，使 Ctrl+Z 可一步撤销整个模型标注操作
        self.save_undo_state()
        log_terminal("[Shortcut S / Quick Auto-Annotate] 触发当前页面自动标注...")
        self.auto_annotate_dialog.auto_annotate_single_image()

    def auto_annotate_batch_quick(self):
        """点击【一键批量自动标注】触发 (无弹窗，终端打印)"""
        if not hasattr(self, 'auto_annotate_dialog') or self.auto_annotate_dialog is None:
            self.auto_annotate_dialog = AutoAnnotateDialog(main_window_ref=self, parent=self)
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

    def labelDataChanged(self, topLeft, bottomRight):
        item0 = self.labelModel.item(topLeft.row(), 0)
        shape = self.ItemShapeDict[item0]
        if topLeft.column() == 0:
            shape.label = self.labelModel.data(topLeft)
            if sys.version_info < (3, 0, 0):
                shape.label = shape.label.toPyObject()
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
        #print("ExtraEditing", self.sender())
        editindex = self.labelModel.index(index.row(), 1)
        self.labelList.edit(editindex)

    def updateFileMenu(self):
        currFilePath = self.filePath

        def exists(filename):
            return os.path.exists(filename)
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

    def editLabel(self):
        if not self.canvas.editing():
            return
        self.labelDialog.updateListItems(self.labelHist)
        res = self.labelDialog.popUp()

        if res is not None:
            self.labelHist, self.default_label = res
            self.labelList.updateLabelList(self.labelHist)


    def fileCurrentChanged(self, current, previous):
        self.statFile.setText('{0}/{1}'.format(current.row()+1, current.model().rowCount()))
        if self.autoSaving.isChecked():
            if self.defaultSaveDir is not None:
                self.labelList.earlyCommit()
                if self.dirty is True:
                    # 无论是否有标注框，均保存对应的标注文件（空标签则保存 0 个目标的空标注文件与对应文件夹）
                    self.fileModel.setData(previous, len(self.canvas.shapes), Qt.BackgroundRole)
                    self.saveFile()
                elif len(self.canvas.shapes) == 0 and self.filePath:
                    # 对于从未保存过的空标签图片，同样自动保存一个空 XML
                    prev_file = self.fileModel.data(previous, Qt.EditRole)
                    if prev_file:
                        stem = os.path.splitext(os.path.basename(prev_file))[0]
                        if self.dirname is not None:
                            rel = os.path.relpath(prev_file, self.dirname)
                            rel = os.path.splitext(rel)[0]
                            xml_path = os.path.join(self.defaultSaveDir, rel) + '.xml'
                        else:
                            xml_path = os.path.join(os.path.dirname(prev_file), stem) + '.xml'
                        if not os.path.exists(xml_path):
                            self.fileModel.setData(previous, 0, Qt.BackgroundRole)
                            self.saveFile()
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
        self.actions.delete.setEnabled(selected)
        self.actions.copy.setEnabled(selected)

    def auto_expand_label_editor(self):
        """鼠标单次点击(无拖动)选中某个标注框时，右侧标签列表中自动展开 Label 下拉选择框"""
        shape = self.canvas.selectedShape
        if shape and shape in self.ShapeItemDict:
            item0 = self.ShapeItemDict[shape]
            index = self.labelModel.indexFromItem(item0)
            if index.isValid():
                label_idx = self.labelModel.index(index.row(), 0)
                self.labelList.selectRow(index.row())
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

            if new_selected_row >= 0:
                self.labelList.selectRow(new_selected_row)
        finally:
            self._is_reordering_table = False

    def addLabel(self, shape):
        shape.paintLabel = self.paintLabelsOption.isChecked()

        item0 = HashableQStandardItem(shape.label)
        item1 = QStandardItem(shape.extra_label)
        color = generateColorByText(shape.label)
        item0.setBackground(color)
        item1.setBackground(color)

        # 按照 self.labelHist 预设类别的先后顺序插入对应分类区间
        target_sort_idx = self.get_label_sort_index(shape.label)
        insert_row = self.labelModel.rowCount()
        for r in range(self.labelModel.rowCount()):
            r_item = self.labelModel.item(r, 0)
            if r_item and self.get_label_sort_index(r_item.text()) > target_sort_idx:
                insert_row = r
                break

        self.labelModel.insertRow(insert_row, [item0, item1])

        self.ShapeItemDict[shape] = item0
        self.ItemShapeDict[item0] = shape
        self.update_label_list_numbers()

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

    def remAllLabels(self):
        self.canvas.deleteAll()
        self.labelModel.clear()
        self.ShapeItemDict.clear()
        self.ItemShapeDict.clear()
        self.update_label_list_numbers()


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

            if not label in self.labelHist:
                self.labelHist.append(label)
                self.labelList.updateLabelList(self.labelHist)

            self.addLabel(shape)

        self.canvas.loadShapes(s)
        self.canvas.reorderShapesByArea()
        self.reorder_label_table()

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
        # Can add differrent annotation formats here
        try:
            if annotationFilePath[-4:] != ".xml":
                annotationFilePath += XML_EXT
            log_terminal(f"[Shortcut Ctrl+S Terminal] 标注数据已成功保存 XML: {annotationFilePath}")
            self.labelFile.savePascalVocFormat(annotationFilePath, shapes, self.filePath, self.imageData,
                                                self.lineColor.getRgb(), self.fillColor.getRgb())
            return True
        except LabelFileError as e:
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
        extra_text = ""
        if text is not None:
            generate_color = generateColorByText(text)
            shape = self.canvas.setLastLabel(text, generate_color, generate_color, extra_text)
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

            # 默认选中新建的标注框，并自动展开右侧对应的标签下拉选项
            self.canvas.selectShape(shape)
            if shape in self.ShapeItemDict:
                item0 = self.ShapeItemDict[shape]
                index = self.labelModel.indexFromItem(item0)
                if index.isValid():
                    row = index.row()
                    self.labelList.selectRow(row)
                    col0_idx = self.labelModel.index(row, 0)
                    QTimer.singleShot(60, lambda idx=col0_idx: self.labelList.edit(idx))
        else:
            # self.canvas.undoLastLine()
            self.canvas.resetAllLines()

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

            # Label xml file and show bound box according to its filename
            vocReader = None
            if self.defaultSaveDir is not None:
                if self.dirname is not None and os.path.exists(self.dirname):
                    relname = os.path.relpath(self.filePath, self.dirname)
                    relname = os.path.splitext(relname)[0]
                    # TODO: defaultSaveDir changed to another dir need mkdir for subdir
                    xmlPath = os.path.join(self.defaultSaveDir, relname + XML_EXT)
                else:
                    xmlPath = os.path.splitext(filePath)[0] + XML_EXT
            else:
                xmlPath = os.path.splitext(filePath)[0] + XML_EXT

            if os.path.isfile(xmlPath):
                vocReader = self.loadPascalXMLByFilename(xmlPath)

            if vocReader is not None:
                vocWidth, vocHeight, _ = vocReader.getSize()
                if self.image.width() != vocWidth or self.image.height() != vocHeight:
                    #self.errorMessage("Image info not matched", "The width or height of annotation file is not matched with that of the image")
                    self.saveFile()

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

            self.canvas.setFocus(True)
            return True
        return False

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            key = event.key()
            txt = event.text().lower() if event.text() else ""
            mods = event.modifiers()
            focus_widget = QApplication.focusWidget()
            is_typing_text = False
            if focus_widget and isinstance(focus_widget, (QTextEdit, QPlainTextEdit)):
                is_typing_text = True
            elif focus_widget and isinstance(focus_widget, QLineEdit):
                if hasattr(self, 'labelList') and self.labelList:
                    if self.labelList.extra_delegate and self.labelList.extra_delegate.editor == focus_widget:
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

            if (key in (Qt.Key_Q, Qt.Key_Delete, Qt.Key_Backspace) or (txt == 'q' and not mods)) and not is_typing_text:
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
            elif txt == 'x' and not mods and not is_typing_text:
                if self.canvas.selectedShape:
                    self.canvas.selectedShape.increaseLength()
                    self.canvas.shapeMoved.emit()
                    self.canvas.update()
                    self.setDirty()
                    log_terminal("[Shortcut X Terminal] 增大选中标注框的长 (Length +)")
                    return True
            elif txt == 'c' and not mods and not is_typing_text:
                if self.canvas.selectedShape:
                    self.canvas.selectedShape.increaseWidth()
                    self.canvas.shapeMoved.emit()
                    self.canvas.update()
                    self.setDirty()
                    log_terminal("[Shortcut C Terminal] 增大选中标注框的宽 (Width +)")
                    return True
            elif txt == 'z' and not mods and not is_typing_text:
                if self.canvas.selectedShape:
                    self.canvas.selectedShape.isRotated = True
                    angle = self.canvas.get_dynamic_rotation_angle(1)
                    if not self.canvas.rotateOutOfBound(angle):
                        self.canvas.selectedShape.rotate(angle)
                        self.canvas.shapeMoved.emit()
                        self.canvas.update()
                        self.setDirty()
                        deg = abs(angle * 180.0 / math.pi)
                        log_terminal(f"[Shortcut Z Terminal] 顺时针旋转标注框 (+{deg:.1f}° 变速调控)")
                    return True
            elif txt == 'v' and not mods and not is_typing_text:
                if self.canvas.selectedShape:
                    self.canvas.selectedShape.isRotated = True
                    angle = self.canvas.get_dynamic_rotation_angle(-1)
                    if not self.canvas.rotateOutOfBound(angle):
                        self.canvas.selectedShape.rotate(angle)
                        self.canvas.shapeMoved.emit()
                        self.canvas.update()
                        self.setDirty()
                        deg = abs(angle * 180.0 / math.pi)
                        log_terminal(f"[Shortcut V Terminal] 逆时针旋转标注框 (-{deg:.1f}° 变速调控)")
                    return True
            elif txt == 'r' and not mods and not is_typing_text:
                self.toggle_undo_redo()
                return True
        elif event.type() == QEvent.KeyRelease:
            if event.isAutoRepeat():
                return super(MainWindow, self).eventFilter(obj, event)
            key = event.key()
            txt = event.text().lower() if event.text() else ""
            if key in (Qt.Key_Z, Qt.Key_V) or txt in ('z', 'v'):
                if hasattr(self, 'canvas') and self.canvas:
                    self.canvas._rot_start_time = None
                    self.canvas._rot_last_time = 0

        return super(MainWindow, self).eventFilter(obj, event)

    def keyPressEvent(self, event):
        key = event.key()
        txt = event.text().lower() if event.text() else ""
        if key in (Qt.Key_Q, Qt.Key_Delete, Qt.Key_Backspace) or txt == 'q':
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
        elif txt == 'x' and self.canvas.selectedShape:
            self.canvas.selectedShape.increaseLength()
            self.canvas.shapeMoved.emit()
            self.canvas.update()
            self.setDirty()
            log_terminal("[Shortcut X Terminal] 增大选中标注框的长 (Length +)")
            event.accept()
            return
        elif txt == 'c' and self.canvas.selectedShape:
            self.canvas.selectedShape.increaseWidth()
            self.canvas.shapeMoved.emit()
            self.canvas.update()
            self.setDirty()
            log_terminal("[Shortcut C Terminal] 增大选中标注框的宽 (Width +)")
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

        settings[SETTING_AUTO_SAVE] = self.autoSaving.isChecked()
        settings[SETTING_DRAW_CORNER] = self.drawCorner.isChecked()
        settings[SETTING_PAINT_LABEL] = self.paintLabelsOption.isChecked()
        settings.save()
    ## User Dialogs ##

    def loadRecent(self, filename):
        if self.mayContinue():
            self.loadFile(filename)

    def scanAllImages(self, folderPath):
        extensions = ['.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        images = []

        for root, dirs, files in os.walk(folderPath):
            for file in files:
                if file.lower().endswith(tuple(extensions)):
                    relativePath = os.path.join(root, file)
                    path = os.path.abspath(relativePath)
                    images.append(path)
        collator = QCollator()
        locale = QLocale(QLocale.Chinese)
        collator.setLocale(locale)
        def sort_key(s):
            return collator.sortKey(s)
        sorted_images = sorted(images, key=sort_key)
        return sorted_images

    def changeSavedirDialog(self, _value=False):
        log_terminal("[Shortcut Ctrl+R Terminal] 触发修改标注保存路径窗口")
        path = self.defaultSaveDir if (self.defaultSaveDir and os.path.exists(self.defaultSaveDir)) else (self.lastOpenDir if (self.lastOpenDir and os.path.exists(self.lastOpenDir)) else '.')

        dirpath = QFileDialog.getExistingDirectory(self,
                                                       '%s - Save annotations to the directory' % __appname__, path,  QFileDialog.ShowDirsOnly
                                                       | QFileDialog.DontResolveSymlinks)

        if dirpath is not None and len(dirpath) > 1:
            self.defaultSaveDir = dirpath
            self.lastOpenDir = dirpath
            self.settings[SETTING_SAVE_DIR] = dirpath
            self.settings[SETTING_LAST_OPEN_DIR] = dirpath
            self.settings.save()

        imglist = self.scanAllImages(self.dirname)
        self.fileModel.setStringList(imglist, self.dirname, self.defaultSaveDir)

        self.statusBar().showMessage('%s . Annotation will be saved to %s' %
                                     ('Change saved folder', self.defaultSaveDir))
        self.statusBar().show()

    def openAnnotationDialog(self, _value=False):
        if self.filePath is None:
            self.statusBar().showMessage('Please select image first')
            self.statusBar().show()
            return

        path = self.defaultSaveDir if (self.defaultSaveDir and os.path.exists(self.defaultSaveDir)) else (self.lastOpenDir if (self.lastOpenDir and os.path.exists(self.lastOpenDir)) else (os.path.dirname(self.filePath) if self.filePath else '.'))
        filters = "Open Annotation XML file (%s)" % ' '.join(['*.xml'])
        filename = QFileDialog.getOpenFileName(self,'%s - Choose a xml file' % __appname__, path, filters)
        if filename:
            if isinstance(filename, (tuple, list)):
                filename = filename[0]
            if filename and os.path.exists(filename):
                self.lastOpenDir = os.path.dirname(filename)
                self.settings[SETTING_LAST_OPEN_DIR] = self.lastOpenDir
                self.settings.save()
                self.loadPascalXMLByFilename(filename)

    def openDirDialog(self, _value=False, dirpath=None):
        if not self.mayContinue():
            return

        log_terminal("[Shortcut Ctrl+U Terminal] 触发打开图片文件夹选择窗口")
        defaultOpenDirPath = dirpath if dirpath else (self.lastOpenDir if (self.lastOpenDir and os.path.exists(self.lastOpenDir)) else (os.path.dirname(self.filePath) if self.filePath else '.'))

        targetDirPath = QFileDialog.getExistingDirectory(self,
                                                     '%s - Open Directory' % __appname__, defaultOpenDirPath,
                                                     QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        if targetDirPath and os.path.exists(targetDirPath):
            self.lastOpenDir = targetDirPath
            self.settings[SETTING_LAST_OPEN_DIR] = targetDirPath
            self.settings.save()
            self.importDirImages(targetDirPath)

    def on_directory_changed(self, path):
        # 延迟 150ms 刷新，避免外部写文件锁冲突
        QTimer.singleShot(150, self.refreshCurrentDir)

    def refreshCurrentDir(self):
        """外部文件变动或目录内容变动时，实时自动重新扫描并刷新照片列表与对应画面"""
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

    def importDirImages(self, dirpath, target_file=None):
        if not self.mayContinue() or not dirpath or not os.path.exists(dirpath):
            return

        self.lastOpenDir = dirpath
        self.dirname = dirpath
        if not self.defaultSaveDir or not os.path.exists(self.defaultSaveDir):
            self.defaultSaveDir = dirpath
        
        imglist = self.scanAllImages(dirpath)
        self.fileModel.setStringList(imglist, self.dirname, self.defaultSaveDir)

        self.setWindowTitle(__appname__ + ' ' + self.dirname)

        # 挂载/更新目录变动监控
        if hasattr(self, 'dir_watcher'):
            existing_dirs = self.dir_watcher.directories()
            if existing_dirs:
                self.dir_watcher.removePaths(existing_dirs)
            self.dir_watcher.addPath(dirpath)
            if self.defaultSaveDir and os.path.exists(self.defaultSaveDir) and self.defaultSaveDir != dirpath:
                self.dir_watcher.addPath(self.defaultSaveDir)

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
        # Proceding next image without dialog if having any label
         if self.filePath is not None:
            try:
                self.labelFile.toggleVerify()
            except AttributeError:
                # If the labelling file does not exist yet, create if and
                # re-save it with the verified attribute.
                self.saveFile()
                self.labelFile.toggleVerify()

            self.fileModel.setData(self.filesm.currentIndex(), len(self.canvas.shapes), Qt.BackgroundRole)
            self.canvas.verified = self.labelFile.verified
            self.paintCanvas()
            self.saveFile()

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

        return True

    def openFile(self, _value=False):
        if not self.mayContinue():
            return
        log_terminal("[Shortcut Ctrl+O Terminal] 触发打开图片/文件选择窗口")
        path = self.lastOpenDir if (self.lastOpenDir and os.path.exists(self.lastOpenDir)) else (os.path.dirname(self.filePath) if self.filePath else '.')
        formats = ['*.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        filters = "Image & Label files (%s)" % ' '.join(formats + ['*%s' % LabelFile.suffix])
        filename = QFileDialog.getOpenFileName(self, '%s - Choose Image or Label file' % __appname__, path, filters)
        if filename:
            if isinstance(filename, (tuple, list)):
                filename = filename[0]
            if filename and os.path.exists(filename):
                self.lastOpenDir = os.path.dirname(filename)
                self.settings[SETTING_LAST_OPEN_DIR] = self.lastOpenDir
                self.settings.save()
                self.loadFile(filename)

            if self.filePath is not None:
                imglist = [self.filePath]
                self.fileModel.setStringList(imglist)
                if self.fileModel.rowCount() > 0:
                    curIndex = self.fileModel.index(0)
                    self.filesm.blockSignals(True)
                    self.filesm.setCurrentIndex(curIndex, QItemSelectionModel.SelectCurrent)
                    self.filesm.blockSignals(False)

    def saveLocal(self, file_path):
        imgFileDir = os.path.dirname(file_path)
        imgFileName = os.path.basename(file_path)
        savedFileName = os.path.splitext(imgFileName)[0]
        savedPath = os.path.join(imgFileDir, savedFileName)
        if self.labelFile:
            self._saveFile(savedPath)
        else:
            # 无 labelFile 时直接用同目录路径保存（用于空标签自动保存，避免弹出对话框）
            self._saveFile(savedPath)

    def saveFile(self, _value=False):
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
            if self.labelFile is None:
                savedPath = self.saveFileDialog()
        if not savedPath.endswith(XML_EXT):
            savedPath += XML_EXT
        if os.path.exists(savedPath):
            os.remove(savedPath)

    def saveFileAndRenderList(self, _value=False):
        self.saveFile(_value=_value)
        cur = self.filesm.currentIndex()
        self.fileModel.setData(cur, len(self.canvas.shapes), Qt.BackgroundRole)

    def saveFileAs(self, _value=False):
        assert not self.image.isNull(), "cannot save empty image"
        self._saveFile(self.saveFileDialog())

    def saveFileDialog(self):
        caption = '%s - Choose File' % __appname__
        filters = 'File (*%s)' % LabelFile.suffix
        openDialogPath = self.currentPath()
        dlg = QFileDialog(self, caption, openDialogPath, filters)
        dlg.setDefaultSuffix(LabelFile.suffix[1:])
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        filenameWithoutExtension = os.path.splitext(self.filePath)[0]
        dlg.selectFile(filenameWithoutExtension)
        dlg.setOption(QFileDialog.DontUseNativeDialog, False)
        if dlg.exec_():
            fullFilePath = dlg.selectedFiles()[0]
            return os.path.splitext(fullFilePath)[0] # Return file path without the extension.
        return ''

    def _saveFile(self, annotationFilePath):
        if annotationFilePath and self.saveLabels(annotationFilePath):
            self.setClean()
            self.statusBar().showMessage('Saved to  %s' % annotationFilePath)
            self.statusBar().show()
            if hasattr(self, 'filesm') and self.filesm:
                cur = self.filesm.currentIndex()
                if cur.isValid():
                    self.fileModel.setData(cur, len(self.canvas.shapes), Qt.BackgroundRole)
                    self.fileListView.viewport().update()

    def closeFile(self, _value=False):
        if not self.mayContinue():
            return
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)
        self.actions.saveAs.setEnabled(False)

    def resetAll(self):
        self.settings.reset()
        self.close()
        proc = QProcess()
        proc.startDetached(os.path.abspath(__file__))

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
        """保存当前图片标注框状态快照至撤销栈 (最多 50 步)"""
        if not hasattr(self, 'undo_stack'):
            self.undo_stack = []
        if not hasattr(self, 'redo_stack'):
            self.redo_stack = []

        snapshot = [s.copy() for s in self.canvas.shapes]
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def restore_shapes_snapshot(self, snapshot):
        """用快照完全同步重构 Canvas 与 右侧 Label 列表，保证 100% 同步"""
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

    def toggle_undo_redo(self):
        """按下 R 键：点击一次回退到上次操作(Undo)，再次点击取消回退(Redo)，循环往复"""
        last_action = getattr(self, '_last_r_toggle_action', 'redo')
        if last_action == 'undo' and hasattr(self, 'redo_stack') and self.redo_stack:
            self.redo_shape_action()
            self._last_r_toggle_action = 'redo'
            log_terminal("[Shortcut R Terminal] R 快捷键循环切换: 取消回退 (Redo)")
        elif hasattr(self, 'undo_stack') and self.undo_stack:
            self.undo_shape_action()
            self._last_r_toggle_action = 'undo'
            log_terminal("[Shortcut R Terminal] R 快捷键循环切换: 回退到上次操作 (Undo)")
        elif hasattr(self, 'redo_stack') and self.redo_stack:
            self.redo_shape_action()
            self._last_r_toggle_action = 'redo'
            log_terminal("[Shortcut R Terminal] R 快捷键循环切换: 取消回退 (Redo)")
        else:
            log_terminal("[Shortcut R Terminal] 提示: 暂无历史操作记录可供回退/恢复")

    def undo_shape_action(self):
        """按下 Ctrl+Z 撤销上一步框操作"""
        if not hasattr(self, 'undo_stack') or not self.undo_stack:
            self.statusBar().showMessage("提示: 撤销栈为空，无可撤销的操作", 3000)
            log_terminal("[Shortcut Ctrl+Z Terminal] 提示: 当前图片没有可撤销的操作")
            return

        if not hasattr(self, 'redo_stack'):
            self.redo_stack = []

        current_snapshot = [s.copy() for s in self.canvas.shapes]
        self.redo_stack.append(current_snapshot)

        prev_snapshot = self.undo_stack.pop()
        self.restore_shapes_snapshot(prev_snapshot)

        msg = f"[Shortcut Ctrl+Z Terminal] 已成功撤销上一步操作 (可重做步数: {len(self.redo_stack)}, 剩余撤销步数: {len(self.undo_stack)})"
        self.statusBar().showMessage(msg, 3000)
        log_terminal(msg)

    def redo_shape_action(self):
        """按下 Ctrl+Shift+Z 重做上一步撤销的操作"""
        if not hasattr(self, 'redo_stack') or not self.redo_stack:
            self.statusBar().showMessage("提示: 重做栈为空，无可重做的操作", 3000)
            log_terminal("[Shortcut Ctrl+Shift+Z Terminal] 提示: 没有可重做的操作")
            return

        if not hasattr(self, 'undo_stack'):
            self.undo_stack = []

        current_snapshot = [s.copy() for s in self.canvas.shapes]
        self.undo_stack.append(current_snapshot)

        next_snapshot = self.redo_stack.pop()
        self.restore_shapes_snapshot(next_snapshot)

        msg = f"[Shortcut Ctrl+Shift+Z Terminal] 已成功重做操作 (剩余重做步数: {len(self.redo_stack)})"
        self.statusBar().showMessage(msg, 3000)
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
            else:
                log_terminal("[Shortcut Q/Del Terminal] 提示: 当前未选中任何标注框 (请先在画布或列表中点击选中要删除的框)")
        finally:
            self._is_deleting_shape = False

    def labelAsBackground(self):
        self.remAllLabels()
        self.setDirty()
        self.setBackSample()

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

    def loadPredefinedClasses(self, predefClassesFile):
        if os.path.exists(predefClassesFile) is True:
            with codecs.open(predefClassesFile, 'r', 'utf8') as f:
                for line in f:
                    line = line.strip()
                    if self.labelHist is None:
                        self.labelHist = [line]
                    else:
                        self.labelHist.append(line)

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
    win = MainWindow(argv[1] if len(argv) >= 2 else None,
                     argv[2] if len(argv) >= 3 else os.path.join(
                         os.path.dirname(sys.argv[0]),
                         'data', 'predefined_classes.txt'),
                     argv[3] if len(argv) >= 4 else None)
    win.setWindowIcon(app_icon)
    win.show()
    return app, win



def main():
    '''construct main app and run it'''
    app, _win = get_main_app(sys.argv)
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
