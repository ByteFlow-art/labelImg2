<div align="center">

<img src="img/app.png" width="128" height="128" alt="LabelImg2 Logo" />

# LabelImg2

### Deep Learning Object Detection Annotation & Model Self-Training Workstation
**Advanced Graphical Annotation Suite for Horizontal Bounding Boxes and Oriented Bounding Boxes (OBB)**

[![Release](https://img.shields.io/badge/Release-v1.0.0-0284C7.svg?style=flat-square)](https://github.com/ByteFlow-art/labelImg2/releases)
[![Python](https://img.shields.io/badge/Python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![GUI Framework](https://img.shields.io/badge/GUI-PyQt5%20v5.15+-41CD52.svg?style=flat-square&logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Deep Learning](https://img.shields.io/badge/Engine-PyTorch%20%2F%20CUDA-EE4C2C.svg?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![YOLO Engine](https://img.shields.io/badge/YOLO-v8%20%7C%20v11%20%7C%20v26-8B5CF6.svg?style=flat-square)](https://github.com/ultralytics/ultralytics)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-64748B.svg?style=flat-square)]()
[![License](https://img.shields.io/badge/License-MIT-F59E0B.svg?style=flat-square)](LICENSE)

[Downloads](https://github.com/ByteFlow-art/labelImg2/releases) | [Architectural Comparison](#architectural-comparison) | [Core Capabilities](#core-capabilities) | [Installation & Quickstart](#installation--quickstart) | [Annotation Workflow](#standard-annotation-workflow) | [Hotkeys Cheat Sheet](#keyboard-shortcuts) | [Data Formats](#supported-annotation-formats) | [Roadmap](#project-roadmap)

</div>

---

## 1. Overview & Lineage

**LabelImg2** is an advanced graphical computer vision annotation workstation developed for horizontal bounding box and oriented bounding box (OBB) object detection tasks.

Originating from the widely adopted [chinakook/labelImg2](https://github.com/chinakook/labelImg2) and the foundational [tzutalin/labelImg](https://github.com/heartexlabs/labelImg), this project extends the classic annotation paradigm into a modern, high-throughput machine learning engineering environment. LabelImg2 bridges the gap between manual data labeling and deep learning algorithm training by unifying **interactive manual annotation**, **embedded YOLO deep learning inference**, **single/batch auto-annotation**, and **closed-loop in-app model self-training** into a seamless workflow.

---

## 2. Architectural Comparison

| Capability & Dimension | Baseline `chinakook/labelImg2` / Classic `labelImg` | LabelImg2 (v1.0.0 Production Release) |
| :--- | :--- | :--- |
| **AI Auto-Annotation Engine** | Not supported (100% manual box drawing) | **Integrated YOLO Model Center**: Real-time single-image inference and asynchronous multi-threaded batch annotation with automatic UI and XML synchronization. |
| **Annotation Application Modes** | Static overwrite | **Dual Annotation Modes**: Supports *Full Overwrite Mode* and *Append & Merge Mode* with IoU-based deduplication to preserve existing annotations while overlaying new predictions. |
| **In-App Model Self-Training** | Not supported (Requires manual data slicing and CLI scripts) | **Built-in Training Console**: Zero-code dataset splitting, hyperparameter configuration, live loss/mAP progress metrics streaming, and direct model weight export. |
| **OBB Dynamic Rotation** | Static angular step size | **Dynamic Velocity Acceleration**: Short press rotates by 1.0°; continuous hold dynamically accelerates to 1.5° (reaching peak velocity in 2s) for rapid and precise re-orientation. |
| **OBB Dimension Adjustment** | Whole box scaling | **Independent Axis Scaling**: Adjust length along primary axis (`X`) and width along secondary axis (`C`) independently without angular distortion. |
| **Overlapping Target Hierarchy** | Unordered selection ambiguity | **Area-Adaptive Sorting**: Automatically places smaller bounding boxes on top of larger enclosing boxes to ensure precise click detection and selection. |
| **Negative Sample (Zero Box) Safety** | Vulnerable to deletion or unhandled exceptions | **Standardized Zero-Object Persistence**: Prompts a confirmation dialog when saving empty images to generate validated 0-object XMLs for background/negative sample training. |
| **Runtime Performance & Lag** | Synchronous disk I/O scans during image switching | **Zero-Latency In-Memory Statistics**: Maintains an in-memory box cache for 0ms instant count updates, eliminating UI stutter, input lag, and number jitter during fast navigation. |
| **Session Modification State** | Transient file item indicators | **Persistent State Tracking**: Files modified or saved during the current running session remain persistently highlighted in fluorescent green across directory rescans. |
| **Safety Input Controls** | Unintended parameter switching via mouse wheel | **Safe Widget Controls**: Comboboxes and spinboxes reject mouse-wheel adjustments unless explicitly clicked and opened, preventing accidental setting changes. |
| **Distribution & Deployment** | Manual Python dependency installation | **Dual Packaging**: Provides a standalone graphical installer (`LabelImg2_Setup_v1.0.0.exe`) and a one-click portable launcher (`Start_LabelImg2.bat`). |

---

## 3. Core Capabilities

### 3.1 Integrated YOLO AI Engine & Model Center
- **Multi-Architecture Support**: Native inference compatibility with Ultralytics YOLOv8, YOLOv11, and custom YOLO weights (`.pt`, `.onnx`, `.engine`).
- **Hardware Acceleration**: Automatic runtime detection of NVIDIA CUDA GPU acceleration and CPU fallback execution.
- **Inference Parameter Calibration**: Real-time adjustable sliders for Confidence Threshold (`Conf`) and Non-Maximum Suppression IoU Threshold (`IoU`).
- **Class Filtering & Mapping**: Selectively enable or disable specific object categories and configure category renaming rules prior to saving.
- **Independent Path Management**: Image input directories and annotation output directories are managed independently, with path states saved persistently via `QSettings`.

### 3.2 Dual-Mode Auto-Annotation Architecture
- **Full Overwrite Mode**: Clears existing labels for the target image and writes the full set of YOLO prediction boxes.
- **Append & Merge Mode**: Preserves all existing manual bounding boxes (including rotated boxes, custom tags, and difficult flags) and appends newly detected targets, automatically filtering duplicates using an IoU threshold of 0.85.
- **Batch Processing**: Background multi-threaded processing across entire folders with progress tracking, live console feedback, and instant visual verification in the viewport.

### 3.3 Embedded Model Self-Trainer
- **Zero-Code Training Pipeline**: Specify image and label directories to automatically split datasets into training and validation sets.
- **Hyperparameter Customization**: Configure pre-trained weights, epochs, batch sizes, image resolutions (640–1280), and validation split ratios.
- **Real-Time Visual Metric Streaming**: Live monitoring of training epochs, batch steps, Box Loss, Class Loss, mAP50, and mAP50-95, with immediate export to the auto-annotation engine upon completion.

### 3.4 Precision Oriented Bounding Box (OBB) Controls
- **Dynamic Velocity Rotation (`Z` / `V`)**: Tap for 1.0° fine-tuning; hold to accelerate up to 1.5° per tick for rapid rotation.
- **Independent Axis Resizing (`X` / `C`)**: Fine-tune length along the primary axis (`X`) and width along the orthogonal axis (`C`).
- **Area-Adaptive Sorting**: Layers small targets above large bounding boxes, eliminating interaction conflicts and target masking.

### 3.5 Production-Grade UI & State Ergonomics
- **Zero-Latency In-Memory Counters**: Instantaneous calculation of *Session Added* (`本次`) and *Dataset Total* (`总计`) labels without synchronous disk polling.
- **Session State Highlighting**: Session-modified files remain highlighted in fluorescent green; pre-existing labeled files appear in light gray.
- **Negative Sample Confirmation**: Prompts confirmation when saving images with zero bounding boxes to guarantee clean negative sample datasets.

---

## 4. Installation & Quickstart

### Option 1: Standalone Windows Installer (Recommended for End Users)
1. Download the official installer `LabelImg2_Setup_v1.0.0.exe` from the [GitHub Releases](https://github.com/ByteFlow-art/labelImg2/releases) page.
2. Run the setup wizard to choose your target installation folder and create desktop shortcuts.
3. Launch **LabelImg2** directly via the desktop application icon.

### Option 2: Portable Source Distribution (Recommended for Developers)
1. Clone the repository to your local machine:
   ```bash
   git clone https://github.com/ByteFlow-art/labelImg2.git
   cd labelImg2
   ```
2. Double-click **`Start_LabelImg2.bat`** (or `labelImg.bat`). The script will automatically verify dependencies, configure the environment, and launch the application.
3. (Optional) Run `Create_Desktop_Shortcut.bat` to place a launcher shortcut with the official icon onto your desktop.

### Option 3: Manual Environment Setup (Python / Conda / UV)

```bash
# 1. Create a Python virtual environment (Python 3.8 - 3.11 recommended)
conda create -n labelimg2 python=3.10 -y
conda activate labelimg2

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch LabelImg2
python labelImg.py
```

---

## 5. Standard Annotation Workflow

### Horizontal Bounding Box (Pascal VOC / YOLO)
1. Open the application and configure your default annotation directory via **Change Save Dir (`Ctrl + R`)**.
2. Open your image dataset directory via **Open Dir (`Ctrl + U`)**.
3. Press **`W`** to activate rectangular drawing mode. Click and drag with the left mouse button to define the bounding box.
4. Select or type the target class label and confirm.
5. Press **`Ctrl + S`** to save, or press **`D`** to advance to the next image (with Auto-Save enabled).

### Oriented Bounding Box (OBB / Rotated Box)
1. Press **`E`** to activate OBB creation mode. Click and drag to create an initial rotated box.
2. Select the rotated box and use **`Z`** (clockwise) or **`V`** (counter-clockwise) to adjust the orientation angle.
3. Use **`X`** (length) and **`C`** (width) to adjust dimensions along the box axes.
4. Annotations are exported with complete `<robndbox>` specifications (`cx`, `cy`, `w`, `h`, `angle`).

---

## 6. Keyboard Shortcuts

| Shortcut | Description | Context / Target |
| :--- | :--- | :--- |
| **`W`** | Create Horizontal Rectangular Box | Viewport Canvas |
| **`E`** | Create Oriented Bounding Box (OBB) | Viewport Canvas |
| **`Z`** (Tap / Hold) | Rotate Clockwise (1.0° fine to 1.5° dynamic acceleration) | Selected OBB |
| **`V`** (Tap / Hold) | Rotate Counter-Clockwise (1.0° fine to 1.5° dynamic acceleration) | Selected OBB |
| **`X`** | Increase Box Length along Primary Axis | Selected Bounding Box |
| **`C`** | Increase Box Width along Secondary Axis | Selected Bounding Box |
| **`Q` / `Delete`** | Delete Selected Bounding Box | Selected Bounding Box |
| **`Ctrl + D`** | Duplicate Bounding Box at Current Position | Selected Bounding Box |
| **`R`** | Single-Key Toggle Undo / Redo | History Management |
| **`Ctrl + S`** | Save Current Annotation File | File I/O |
| **`A` / `D`** | Previous Image / Next Image (Auto-saves if enabled) | Dataset Navigation |
| **`Ctrl + U`** | Open Image Directory | Workspace |
| **`Ctrl + R`** | Change Label Save Directory | Workspace |
| **`Ctrl + Scroll`** | Smooth Canvas Zoom (In / Out) | Viewport View |
| **`Alt + Drag`** | Pan Canvas Viewport | Viewport View |

---

## 7. Supported Annotation Formats

- **Pascal VOC XML (`.xml`)**: Comprehensive XML format containing `<bndbox>` (`xmin`, `ymin`, `xmax`, `ymax`) and `<robndbox>` (`cx`, `cy`, `w`, `h`, `angle`).
- **YOLO Normalized TXT (`.txt`)**: Standard normalized center coordinates, width, height, and rotation angles.
- **Create ML JSON (`.json`)**: Apple Create ML object detection structure.
- **COCO JSON (`.json`)**: Microsoft COCO dataset annotations schema.

---

## 8. Project Roadmap

### v1.0.0 (Current Stable Release)
- Full OBB dynamic velocity rotation and axis-independent resizing.
- Integrated YOLO model center with single and batch inference.
- Dual annotation application modes: Full Overwrite vs Append & Merge.
- In-app model self-training console with live metric streaming.
- Zero-latency in-memory session and total label statistics.
- Standalone Windows installer (`.exe`) and portable launcher scripts.

### v2.0.0 (Planned)
- Keypoint and polygon segmentation annotation support (YOLOv8-Pose / YOLOv8-Seg).
- Active learning query strategies for prioritized manual verification.
- Semi-supervised auto-tracking across sequential video frames.
- Cloud storage integration (S3 / MinIO / OSS) with multi-user review workflows.

---

## 9. License & Citations

LabelImg2 is distributed under the [MIT License](LICENSE).

We gratefully acknowledge the foundational open-source projects that made this work possible:
- [chinakook/labelImg2](https://github.com/chinakook/labelImg2)
- [tzutalin/labelImg](https://github.com/heartexlabs/labelImg)
- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)

---

<div align="center">
<b>LabelImg2 Development Team</b> &bull; Open Source Computer Vision Infrastructure
</div>

