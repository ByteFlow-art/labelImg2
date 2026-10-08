# -*- coding: utf-8 -*-
"""
LabelImg2 - 视频导入与智能抽帧工作台 (Video Import & Smart Frame Extractor)
借鉴 LabelQuick 视频数据源处理精华并深度超越：
1. 原生支持主流视频格式 (*.mp4, *.avi, *.mov, *.mkv, *.webm, *.flv 等) 直接导入与流式解码；
2. 可视化交互预览器：播放/暂停、逐帧微调步进、时间轴滑块快速跳转定位；
3. 单帧一键快照抓取 (Snapshot)；
4. 强大灵活的抽帧配置：按时间频率 (FPS)、按帧步长 (Interval)、按起止时间区间切片；
5. 后台多线程异步高速抽帧与防爆保护；
6. 一键无缝直连 LabelImg2 工作区，瞬间开启目标标注。
"""

import os
import time
import cv2
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl, QSize
from PyQt5.QtGui import QImage, QPixmap, QIcon, QDesktopServices
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QPushButton, QSlider, QProgressBar, QRadioButton,
    QButtonGroup, QDoubleSpinBox, QSpinBox, QFileDialog, QMessageBox,
    QScrollArea, QFrame, QSizePolicy, QApplication
)

from libs.lib import newIcon
from ui.styles import LIGHT_WORKSTATION_STYLE
from core.safe_widgets import SafeSpinBox, SafeDoubleSpinBox, SafeSlider


class VideoExtractThread(QThread):
    """视频异步抽帧工作线程"""
    progress_signal = pyqtSignal(int, int, str)  # (percent, saved_count, status_text)
    finished_signal = pyqtSignal(str, int)       # (output_dir, total_saved)
    error_signal = pyqtSignal(str)

    def __init__(self, video_path: str, output_dir: str, mode: str,
                 fps_val: float, interval_val: int, start_sec: float,
                 end_sec: float, max_frames: int = 5000):
        super(VideoExtractThread, self).__init__()
        self.video_path = video_path
        self.output_dir = output_dir
        self.mode = mode                     # 'fps', 'interval', 'all'
        self.fps_val = max(0.1, fps_val)
        self.interval_val = max(1, interval_val)
        self.start_sec = max(0.0, start_sec)
        self.end_sec = end_sec
        self.max_frames = max_frames
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.error_signal.emit(f"无法打开视频文件: {self.video_path}")
            return

        try:
            native_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            duration_sec = total_frames / native_fps if native_fps > 0 else 0.0

            start_frame = max(0, int(self.start_sec * native_fps))
            end_frame = int(self.end_sec * native_fps)
            if total_frames > 0:
                end_frame = min(total_frames, end_frame)

            if start_frame >= end_frame:
                self.error_signal.emit(f"截取起止时间区间无效: 起始时间 ({self.start_sec:.2f}s) >= 截止时间 ({self.end_sec:.2f}s)")
                return

            if start_frame > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

            curr_frame_idx = start_frame
            saved_count = 0

            # 计算跳帧步长
            if self.mode == 'fps':
                step = max(1, int(round(native_fps / self.fps_val)))
            elif self.mode == 'interval':
                step = self.interval_val
            else:
                step = 1

            total_target = max(1, (end_frame - start_frame) // step)

            while self._is_running and (curr_frame_idx <= end_frame or end_frame <= 0):
                ret, frame = cap.read()
                if not ret:
                    break

                if (curr_frame_idx - start_frame) % step == 0:
                    saved_count += 1
                    out_name = f"frame_{saved_count:06d}.jpg"
                    out_path = os.path.join(self.output_dir, out_name)
                    cv2.imwrite(out_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

                    pct = min(100, int((saved_count / total_target) * 100))
                    msg = f"正在抽帧: 已保存 {saved_count} 帧 ({out_name})"
                    self.progress_signal.emit(pct, saved_count, msg)

                    if saved_count >= self.max_frames:
                        break

                curr_frame_idx += 1

            self.progress_signal.emit(100, saved_count, f"抽帧完成！共提取 {saved_count} 张图片")
            self.finished_signal.emit(self.output_dir, saved_count)

        except Exception as e:
            self.error_signal.emit(f"抽帧过程出现异常: {e}")
        finally:
            cap.release()


class VideoExtractDialog(QDialog):
    """
    视频导入与智能抽帧工作台对话框
    """
    frames_imported = pyqtSignal(str)  # 信号：直接将提取的图片目录导入主窗口

    def __init__(self, parent=None, default_output_dir: str = ""):
        super(VideoExtractDialog, self).__init__(parent)
        self.setWindowTitle("视频导入与智能抽帧工作台 (Video Import & Frame Extractor)")

        ico = newIcon("app.ico")
        if ico.isNull():
            ico = newIcon("app.png")
        if ico.isNull():
            ico = newIcon("labelImg2.ico")
        self.setWindowIcon(ico)

        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            w = min(960, int(avail.width() * 0.85))
            h = min(860, int(avail.height() * 0.92))
            self.resize(w, h)
        else:
            self.resize(960, 860)

        self.setMinimumSize(860, 720)
        self.setStyleSheet(LIGHT_WORKSTATION_STYLE)

        # 启用非模态窗口与窗口控制按钮
        non_modal_val = getattr(Qt, 'NonModal', None) or getattr(getattr(Qt, 'WindowModality', None), 'NonModal', 0)
        self.setWindowModality(non_modal_val)
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint
        )

        # 解析初始默认输出目录（优先默认使用项目图片文件夹目录）
        proj_dir = ""
        if parent and hasattr(parent, 'get_project_image_dir'):
            proj_dir = parent.get_project_image_dir()
        elif parent:
            if hasattr(parent, 'dirname') and parent.dirname and os.path.isdir(parent.dirname):
                proj_dir = os.path.abspath(parent.dirname)
            elif hasattr(parent, 'lastOpenDir') and parent.lastOpenDir and os.path.isdir(parent.lastOpenDir):
                proj_dir = os.path.abspath(parent.lastOpenDir)
            elif hasattr(parent, 'filePath') and parent.filePath and os.path.exists(parent.filePath):
                proj_dir = os.path.abspath(os.path.dirname(parent.filePath))

        self.default_output_dir = default_output_dir or proj_dir or os.path.abspath("data/video_frames")
        self.video_path = ""
        self.cap: Optional[cv2.VideoCapture] = None
        self.total_frames = 0
        self.native_fps = 25.0
        self.duration_sec = 0.0
        self.current_frame_idx = 0
        self.current_frame_img = None
        self.is_playing = False
        self._slider_pressed = False

        self.extract_thread: Optional[VideoExtractThread] = None

        self.timer_player = QTimer(self)
        self.timer_player.timeout.connect(self._on_play_timer)

        self._init_ui()

    def set_default_output_dir(self, out_dir: str):
        """设置默认输出目录（保持与项目图片目录同步，后面用户亦可自行选择修改）"""
        if out_dir:
            self.default_output_dir = os.path.abspath(out_dir)
            if hasattr(self, 'txt_output'):
                self.txt_output.setText(self.default_output_dir)

    def create_section_header(self, title_text: str) -> QLabel:
        lbl = QLabel(title_text)
        lbl.setObjectName("section_header")
        return lbl

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        # ---------------- 1. 视频源与输出目录设置 ----------------
        layout.addWidget(self.create_section_header("1. 视频数据源与输出目录配置"))

        box_src = QVBoxLayout()
        box_src.setSpacing(8)

        # 视频路径选择行
        row_vid = QHBoxLayout()
        lbl_vid = QLabel("视频源文件:")
        lbl_vid.setMinimumWidth(100)
        lbl_vid.setStyleSheet("font-weight: 600;")
        self.txt_video = QLineEdit()
        self.txt_video.setPlaceholderText("选择或拖入视频文件 (*.mp4, *.avi, *.mov, *.mkv, *.webm 等)...")
        btn_browse_vid = QPushButton(" 浏览视频...")
        btn_browse_vid.setIcon(newIcon("video.svg") if not newIcon("video.svg").isNull() else newIcon("open.svg"))
        btn_browse_vid.setObjectName("btn_secondary")
        btn_browse_vid.clicked.connect(self.browse_video_file)

        row_vid.addWidget(lbl_vid)
        row_vid.addWidget(self.txt_video, 1)
        row_vid.addWidget(btn_browse_vid)
        box_src.addLayout(row_vid)

        # 输出目录选择行
        row_out = QHBoxLayout()
        lbl_out = QLabel("抽帧输出目录:")
        lbl_out.setMinimumWidth(100)
        lbl_out.setStyleSheet("font-weight: 600;")
        self.txt_output = QLineEdit(self.default_output_dir)
        self.txt_output.setPlaceholderText("选择抽取图片保存的文件夹...")
        btn_browse_out = QPushButton(" 浏览目录...")
        btn_browse_out.setIcon(newIcon("dir.svg") if not newIcon("dir.svg").isNull() else newIcon("open.svg"))
        btn_browse_out.setObjectName("btn_secondary")
        btn_browse_out.clicked.connect(self.browse_output_dir)

        row_out.addWidget(lbl_out)
        row_out.addWidget(self.txt_output, 1)
        row_out.addWidget(btn_browse_out)
        box_src.addLayout(row_out)

        # 视频信息指标卡
        meta_box = QHBoxLayout()
        self.card_res = QLabel("分辨率: --")
        self.card_fps = QLabel("帧率: -- fps")
        self.card_dur = QLabel("时长: 00:00")
        self.card_cnt = QLabel("总帧数: 0 帧")

        for card in [self.card_res, self.card_fps, self.card_dur, self.card_cnt]:
            card.setObjectName("metric_card")
            card.setAlignment(Qt.AlignCenter)
            meta_box.addWidget(card)
        box_src.addLayout(meta_box)

        layout.addLayout(box_src)

        # ---------------- 2. 视频可视化交互与画面预览 ----------------
        layout.addWidget(self.create_section_header("2. 视频播放预览与单帧截取"))

        box_player = QVBoxLayout()
        box_player.setSpacing(8)

        # 视频播放预览视口 (居中固定比例)
        self.view_frame = QLabel("请选择并加载视频文件以开启预览")
        self.view_frame.setAlignment(Qt.AlignCenter)
        self.view_frame.setStyleSheet("""
            QLabel {
                background-color: #0F172A;
                color: #94A3B8;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        self.view_frame.setMinimumHeight(320)
        self.view_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        box_player.addWidget(self.view_frame)

        # 时间轴滑块与进度标签
        time_bar = QHBoxLayout()
        self.lbl_cur_time = QLabel("00:00 / 00:00")
        self.lbl_cur_time.setStyleSheet("font-weight: 600; color: #475569;")
        self.slider_timeline = SafeSlider(Qt.Horizontal)
        self.slider_timeline.setRange(0, 100)
        self.slider_timeline.setValue(0)
        self.slider_timeline.sliderPressed.connect(self._on_slider_pressed)
        self.slider_timeline.sliderMoved.connect(self._on_slider_moved)
        self.slider_timeline.sliderReleased.connect(self._on_slider_released)

        time_bar.addWidget(self.slider_timeline, 1)
        time_bar.addWidget(self.lbl_cur_time)
        box_player.addLayout(time_bar)

        # 播放交互控制行
        ctrl_bar = QHBoxLayout()
        self.btn_step_prev = QPushButton("◀ 上一帧")
        self.btn_step_prev.setObjectName("btn_secondary")
        self.btn_step_prev.clicked.connect(self.step_prev_frame)

        self.btn_play = QPushButton()
        self.btn_play.setObjectName("btn_primary")
        self.btn_play.setIcon(newIcon("media_play.svg"))
        self.btn_play.setIconSize(QSize(20, 20))
        self.btn_play.setFixedWidth(54)
        self.btn_play.setToolTip("播放 / 暂停 (Space)")
        self.btn_play.clicked.connect(self.toggle_play)

        self.btn_step_next = QPushButton("下一帧 ▶")
        self.btn_step_next.setObjectName("btn_secondary")
        self.btn_step_next.clicked.connect(self.step_next_frame)

        self.btn_replay = QPushButton()
        self.btn_replay.setObjectName("btn_secondary")
        self.btn_replay.setIcon(newIcon("media_replay.svg"))
        self.btn_replay.setIconSize(QSize(20, 20))
        self.btn_replay.setFixedWidth(54)
        self.btn_replay.setToolTip("重新播放")
        self.btn_replay.clicked.connect(self.replay_video)

        self.btn_snapshot = QPushButton("📸 抓取当前帧至输出目录")
        self.btn_snapshot.setObjectName("btn_success")
        self.btn_snapshot.setToolTip("将当前视频画面立即保存为一张高清图片并准备标注")
        self.btn_snapshot.clicked.connect(self.capture_snapshot)

        ctrl_bar.addWidget(self.btn_step_prev)
        ctrl_bar.addWidget(self.btn_play)
        ctrl_bar.addWidget(self.btn_step_next)
        ctrl_bar.addWidget(self.btn_replay)
        ctrl_bar.addStretch()
        ctrl_bar.addWidget(self.btn_snapshot)
        box_player.addLayout(ctrl_bar)

        layout.addLayout(box_player)

        # ---------------- 3. 抽帧参数与模式配置 ----------------
        layout.addWidget(self.create_section_header("3. 抽帧采样模式与参数配置"))

        grid_mode = QGridLayout()
        grid_mode.setHorizontalSpacing(16)
        grid_mode.setVerticalSpacing(10)

        self.rb_fps = QRadioButton("按时间频率采样 (每秒抽取指定帧)")
        self.rb_interval = QRadioButton("按帧间隔采样 (每隔指定帧抽取 1 帧)")
        self.rb_all = QRadioButton("全量提取所有帧 (完整序列)")
        self.rb_fps.setChecked(True)

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.rb_fps, 1)
        self.mode_group.addButton(self.rb_interval, 2)
        self.mode_group.addButton(self.rb_all, 3)

        # FPS 设置
        self.spin_fps = SafeDoubleSpinBox()
        self.spin_fps.setRange(0.1, 60.0)
        self.spin_fps.setSingleStep(0.5)
        self.spin_fps.setValue(2.0)
        self.spin_fps.setSuffix(" fps (帧/秒)")

        # 帧间隔设置
        self.spin_interval = SafeSpinBox()
        self.spin_interval.setRange(1, 1000)
        self.spin_interval.setValue(10)
        self.spin_interval.setSuffix(" 帧/次")

        # 起止时间切片设置
        self.spin_start_sec = SafeDoubleSpinBox()
        self.spin_start_sec.setRange(0.0, 99999.0)
        self.spin_start_sec.setDecimals(2)
        self.spin_start_sec.setSingleStep(0.5)
        self.spin_start_sec.setValue(0.0)
        self.spin_start_sec.setSuffix(" 秒")
        self.spin_start_sec.valueChanged.connect(self._on_start_sec_changed)

        self.spin_end_sec = SafeDoubleSpinBox()
        self.spin_end_sec.setRange(0.0, 99999.0)
        self.spin_end_sec.setDecimals(2)
        self.spin_end_sec.setSingleStep(0.5)
        self.spin_end_sec.setValue(0.0)
        self.spin_end_sec.setSuffix(" 秒")
        self.spin_end_sec.valueChanged.connect(self._on_end_sec_changed)

        grid_mode.addWidget(self.rb_fps, 0, 0)
        grid_mode.addWidget(self.spin_fps, 0, 1)

        grid_mode.addWidget(self.rb_interval, 1, 0)
        grid_mode.addWidget(self.spin_interval, 1, 1)

        grid_mode.addWidget(self.rb_all, 2, 0)

        grid_mode.addWidget(QLabel("截取起始时间:"), 3, 0)
        grid_mode.addWidget(self.spin_start_sec, 3, 1)

        grid_mode.addWidget(QLabel("截取截止时间:"), 4, 0)
        grid_mode.addWidget(self.spin_end_sec, 4, 1)

        layout.addLayout(grid_mode)

        # ---------------- 4. 提取进度与状态 ----------------
        layout.addWidget(self.create_section_header("4. 抽帧执行状态与进度反馈"))

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("等待开始抽帧...")
        layout.addWidget(self.progress_bar)

        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)

        # ---------------- 5. 底部固定状态指示与全局控制栏 ----------------
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 4, 0, 0)
        bottom_bar.setSpacing(12)

        self.lbl_status = QLabel("就绪")
        self.lbl_status.setObjectName("status_indicator")
        bottom_bar.addWidget(self.lbl_status)
        bottom_bar.addStretch()

        self.btn_open_folder = QPushButton("打开输出目录")
        self.btn_open_folder.setObjectName("btn_secondary")
        self.btn_open_folder.clicked.connect(self.open_output_folder)
        bottom_bar.addWidget(self.btn_open_folder)

        self.btn_import_workspace = QPushButton("导入当前工作区并开始打标")
        self.btn_import_workspace.setObjectName("btn_success")
        self.btn_import_workspace.setIcon(newIcon("export.svg"))
        self.btn_import_workspace.setEnabled(False)
        self.btn_import_workspace.clicked.connect(self.import_to_workspace)
        bottom_bar.addWidget(self.btn_import_workspace)

        self.btn_start = QPushButton("开始提取视频帧")
        self.btn_start.setObjectName("btn_primary")
        self.btn_start.clicked.connect(self.start_extraction)
        bottom_bar.addWidget(self.btn_start)

        main_layout.addLayout(bottom_bar)

    # ---------------- 视频加载与播放逻辑 ----------------
    def browse_video_file(self):
        fpath, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm *.mpg *.mpeg);;所有文件 (*.*)"
        )
        if fpath:
            self.load_video(fpath)

    def load_video(self, fpath: str):
        if not os.path.isfile(fpath):
            QMessageBox.warning(self, "提示", f"视频文件不存在:\n{fpath}")
            return

        self.video_path = os.path.abspath(fpath)
        self.txt_video.setText(self.video_path)

        # 抽帧输出目录默认保持为项目图片文件夹目录，绝不随意篡改；若当前为空则填入默认输出目录
        if not self.txt_output.text().strip():
            self.txt_output.setText(self.default_output_dir)

        if self.cap:
            self.cap.release()

        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "打开失败", f"无法解码视频文件:\n{self.video_path}")
            return

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.native_fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 25.0)
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        self.duration_sec = self.total_frames / self.native_fps if self.native_fps > 0 else 0.0

        # 更新卡片指标
        self.card_res.setText(f"分辨率: {width} × {height}")
        self.card_fps.setText(f"帧率: {self.native_fps:.1f} fps")
        self.card_dur.setText(f"时长: {self._format_time(self.duration_sec)}")
        self.card_cnt.setText(f"总帧数: {self.total_frames} 帧")

        self.slider_timeline.setRange(0, max(0, self.total_frames - 1))
        self.slider_timeline.setValue(0)

        # 动态绑定视频时长区间：起止时间最大值受限于总时长，截止时间默认设置为全视频总时长
        max_sec = round(self.duration_sec, 2)
        self.spin_start_sec.blockSignals(True)
        self.spin_end_sec.blockSignals(True)
        self.spin_start_sec.setRange(0.0, max(0.0, max_sec))
        self.spin_start_sec.setValue(0.0)
        self.spin_end_sec.setRange(0.0, max(0.0, max_sec))
        self.spin_end_sec.setValue(max_sec)
        self.spin_start_sec.blockSignals(False)
        self.spin_end_sec.blockSignals(False)

        self.seek_frame(0)
        self.lbl_status.setText(f"已成功加载视频: {os.path.basename(self.video_path)}")

    def _on_start_sec_changed(self, val: float):
        """起始时间调节联动与最大最小边界检测"""
        if hasattr(self, 'spin_end_sec'):
            end_val = self.spin_end_sec.value()
            max_sec = round(getattr(self, 'duration_sec', 0.0), 2)
            upper_bound = max_sec if max_sec > 0 else 99999.0
            if max_sec > 0 and val >= max_sec:
                val = max(0.0, max_sec - 0.1)
                self.spin_start_sec.blockSignals(True)
                self.spin_start_sec.setValue(round(val, 2))
                self.spin_start_sec.blockSignals(False)
            if val >= end_val:
                new_end = min(upper_bound, val + 0.1)
                self.spin_end_sec.blockSignals(True)
                self.spin_end_sec.setValue(round(new_end, 2))
                self.spin_end_sec.blockSignals(False)

    def _on_end_sec_changed(self, val: float):
        """截止时间调节联动与最大最小边界检测"""
        if hasattr(self, 'spin_start_sec'):
            start_val = self.spin_start_sec.value()
            if val <= start_val:
                new_start = max(0.0, val - 0.1)
                self.spin_start_sec.blockSignals(True)
                self.spin_start_sec.setValue(round(new_start, 2))
                self.spin_start_sec.blockSignals(False)

    def browse_output_dir(self):
        dpath = QFileDialog.getExistingDirectory(self, "选择抽帧输出保存目录", self.txt_output.text())
        if dpath:
            self.txt_output.setText(os.path.abspath(dpath))

    def _format_time(self, seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def seek_frame(self, frame_idx: int):
        if not self.cap or not self.cap.isOpened():
            return

        frame_idx = max(0, min(self.total_frames - 1, frame_idx))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if ret:
            self.current_frame_idx = frame_idx
            self.current_frame_img = frame.copy()
            self._render_preview(frame)

            cur_sec = self.current_frame_idx / self.native_fps if self.native_fps > 0 else 0.0
            self.lbl_cur_time.setText(f"{self._format_time(cur_sec)} / {self._format_time(self.duration_sec)}")
            if not self._slider_pressed:
                self.slider_timeline.blockSignals(True)
                self.slider_timeline.setValue(self.current_frame_idx)
                self.slider_timeline.blockSignals(False)

    def _render_preview(self, frame_bgr):
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        # 自适应居中等比缩放
        vw = max(300, self.view_frame.width() - 8)
        vh = max(240, self.view_frame.height() - 8)
        scaled = pixmap.scaled(vw, vh, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.view_frame.setPixmap(scaled)

    def toggle_play(self):
        if not self.cap or not self.cap.isOpened():
            return

        if self.is_playing:
            self.timer_player.stop()
            self.is_playing = False
            self.btn_play.setText("")
            self.btn_play.setIcon(newIcon("media_play.svg"))
            self.btn_play.setToolTip("播放 / 暂停 (Space)")
        else:
            interval_ms = int(max(15, 1000.0 / self.native_fps))
            self.timer_player.start(interval_ms)
            self.is_playing = True
            self.btn_play.setText("")
            self.btn_play.setIcon(newIcon("media_pause.svg"))
            self.btn_play.setToolTip("暂停 (Space)")

    def _on_play_timer(self):
        if not self.cap or not self.cap.isOpened():
            return

        next_idx = self.current_frame_idx + 1
        if next_idx >= self.total_frames:
            self.toggle_play()
            return
        self.seek_frame(next_idx)

    def step_next_frame(self):
        if self.is_playing:
            self.toggle_play()
        self.seek_frame(self.current_frame_idx + 1)

    def step_prev_frame(self):
        if self.is_playing:
            self.toggle_play()
        self.seek_frame(self.current_frame_idx - 1)

    def replay_video(self):
        if self.is_playing:
            self.toggle_play()
        self.seek_frame(0)
        self.toggle_play()

    def _on_slider_pressed(self):
        self._slider_pressed = True

    def _on_slider_moved(self, val):
        self.seek_frame(val)

    def _on_slider_released(self):
        self._slider_pressed = False
        self.seek_frame(self.slider_timeline.value())

    def capture_snapshot(self):
        """一键抓取当前视频画面并存为样本图片"""
        if self.current_frame_img is None:
            QMessageBox.information(self, "提示", "当前无有效视频画面！")
            return

        out_dir = self.txt_output.text().strip()
        if not out_dir:
            out_dir = os.path.abspath("data/video_frames")
        os.makedirs(out_dir, exist_ok=True)

        snap_name = f"snapshot_{int(time.time())}_{self.current_frame_idx:05d}.jpg"
        snap_path = os.path.join(out_dir, snap_name)
        cv2.imwrite(snap_path, self.current_frame_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

        self.btn_import_workspace.setEnabled(True)
        self.lbl_status.setText(f"已成功捕获快照: {snap_name}")
        QMessageBox.information(self, "快照成功", f"当前画面已成功保存至:\n{snap_path}")

    # ---------------- 抽帧执行与多线程逻辑 ----------------
    def start_extraction(self):
        if not self.video_path or not os.path.isfile(self.video_path):
            QMessageBox.warning(self, "提示", "请先选择有效的视频源文件！")
            return

        out_dir = self.txt_output.text().strip()
        if not out_dir:
            QMessageBox.warning(self, "提示", "请选择抽帧输出保存目录！")
            return

        if self.is_playing:
            self.toggle_play()

        mode_id = self.mode_group.checkedId()
        mode = 'fps' if mode_id == 1 else ('interval' if mode_id == 2 else 'all')

        start_sec = self.spin_start_sec.value()
        end_sec = self.spin_end_sec.value()
        if start_sec >= end_sec:
            QMessageBox.warning(self, "时间区间错误", f"截取起始时间 ({start_sec:.2f}秒) 必须小于截止时间 ({end_sec:.2f}秒)！")
            return
        if self.duration_sec > 0 and end_sec > self.duration_sec + 0.05:
            QMessageBox.warning(self, "时间超限", f"截取截止时间 ({end_sec:.2f}秒) 超出了视频总时长 ({self.duration_sec:.2f}秒)！")
            return

        self.btn_start.setEnabled(False)
        self.btn_start.setText("正在抽帧中...")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("准备开始抽帧...")

        self.extract_thread = VideoExtractThread(
            video_path=self.video_path,
            output_dir=out_dir,
            mode=mode,
            fps_val=self.spin_fps.value(),
            interval_val=self.spin_interval.value(),
            start_sec=self.spin_start_sec.value(),
            end_sec=self.spin_end_sec.value()
        )
        self.extract_thread.progress_signal.connect(self._on_extract_progress)
        self.extract_thread.finished_signal.connect(self._on_extract_finished)
        self.extract_thread.error_signal.connect(self._on_extract_error)
        self.extract_thread.start()

    def _on_extract_progress(self, percent: int, saved_count: int, msg: str):
        self.progress_bar.setValue(percent)
        self.progress_bar.setFormat(f"{percent}% ({saved_count} 帧)")
        self.lbl_status.setText(msg)

    def _on_extract_finished(self, output_dir: str, total_saved: int):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("开始提取视频帧")
        self.btn_import_workspace.setEnabled(total_saved > 0)
        self.lbl_status.setText(f"抽帧完成！共提取 {total_saved} 帧图片")

        reply = QMessageBox.question(
            self,
            "抽帧完成",
            f"视频帧提取完成！共保存 {total_saved} 张图片至:\n{output_dir}\n\n是否立即导入 LabelImg2 工作区开始标注？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self.import_to_workspace()

    def _on_extract_error(self, err_msg: str):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("开始提取视频帧")
        self.lbl_status.setText("抽帧失败")
        QMessageBox.critical(self, "错误", f"抽帧过程失败:\n{err_msg}")

    def open_output_folder(self):
        out_dir = self.txt_output.text().strip()
        if os.path.exists(out_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(out_dir))
        else:
            QMessageBox.warning(self, "提示", f"输出目录尚未创建:\n{out_dir}")

    def import_to_workspace(self):
        out_dir = self.txt_output.text().strip()
        if not out_dir or not os.path.isdir(out_dir):
            QMessageBox.warning(self, "提示", "输出目录不存在或无图片！")
            return

        self.frames_imported.emit(out_dir)
        self.close()

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Space:
            self.toggle_play()
            ev.accept()
            return
        super(VideoExtractDialog, self).keyPressEvent(ev)

    def closeEvent(self, ev):
        if self.timer_player.isActive():
            self.timer_player.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.extract_thread and self.extract_thread.isRunning():
            self.extract_thread.stop()
            self.extract_thread.wait(1000)
        super(VideoExtractDialog, self).closeEvent(ev)
