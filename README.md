<div align="center">

<img src="img/app.png" width="128" height="128" alt="LabelImg2 Logo" />

# LabelImg2

### 新一代深度学习目标检测标注与模型自训练一体化工作台
**支持常规水平矩形框（Horizontal Box）与任意角度旋转框（OBB）的高性能计算机视觉标注套件**

[![Release](https://img.shields.io/badge/Release-v1.0.0-0284C7.svg?style=flat-square)](https://github.com/ByteFlow-art/labelImg2/releases)
[![Python](https://img.shields.io/badge/Python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![GUI Framework](https://img.shields.io/badge/GUI-PyQt5%20v5.15+-41CD52.svg?style=flat-square&logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Deep Learning](https://img.shields.io/badge/Engine-PyTorch%20%2F%20CUDA-EE4C2C.svg?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![YOLO Engine](https://img.shields.io/badge/YOLO-v8%20%7C%20v11%20%7C%20v26-8B5CF6.svg?style=flat-square)](https://github.com/ultralytics/ultralytics)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-64748B.svg?style=flat-square)]()
[![License](https://img.shields.io/badge/License-MIT-F59E0B.svg?style=flat-square)](LICENSE)

[软件下载](https://github.com/ByteFlow-art/labelImg2/releases) | [安装指南](#1-软件安装与快速启动) | [架构对比](#3-核心架构与特性升级对比) | [功能详解](#4-核心功能深度解析) | [作业流程](#5-标准标注作业流程) | [快捷键表](#6-常用快捷键速查表) | [数据格式](#7-支持的标注数据格式) | [演进规划](#8-版本演进与路线图)

</div>

---

## 1. 软件安装与快速启动

### 1.1 途径一：独立安装程序 (.exe) [推荐普通用户]
适合无需配置 Python 开发环境的普通用户与标注人员：
1. 前往本项目的 [GitHub Releases 页面](https://github.com/ByteFlow-art/labelImg2/releases)；
2. 下载最新版安装包 `LabelImg2_Setup_v1.0.0.exe`（或 `LabelImg2_Setup_v1.0.0.zip` 并解压）；
3. 运行进入图形化安装向导，按照提示选择安装路径并勾选创建桌面快捷方式；
4. 安装完成后，直接双击桌面上的 **LabelImg2** 专属应用图标即可启动。

### 1.2 途径二：源码便携运行与启动脚本 (.bat) [推荐开发者]
适合需要便携式运行或进行二次开发的科研与工程人员：
1. 克隆或直接下载源码压缩包并解压：
   ```bash
   git clone https://github.com/ByteFlow-art/labelImg2.git
   cd labelImg2
   ```
2. **一键启动**：在项目根目录下，直接双击 **`Start_LabelImg2.bat`**（或 `labelImg.bat`），启动脚本将自动检测依赖环境并秒级拉起工作台；
3. **生成桌面图标**：双击运行 `Create_Desktop_Shortcut.bat`，即可一键在 Windows 桌面上创建带专属高清图标的启动快捷方式。

### 1.3 途径三：手动命令行环境搭建 (Conda / UV / Pip)

```bash
# 1. 创建并激活 Python 虚拟环境 (推荐 Python 3.8 ~ 3.11)
conda create -n labelimg2 python=3.10 -y
conda activate labelimg2

# 2. 安装核心依赖
pip install -r requirements.txt

# 3. 启动 LabelImg2 工作台
python labelImg.py
```

---

## 2. 项目简介与演进背景

**LabelImg2** 是一款面向计算机视觉深度学习目标检测的高性能图形化标注工作台。

本项目在经典标注工具 [tzutalin/labelImg](https://github.com/heartexlabs/labelImg) 以及支持旋转框扩展的知名开源项目 [chinakook/labelImg2](https://github.com/chinakook/labelImg2) 的坚实基础上进行了全面重构与现代化升级。针对传统标注工具“纯手工画框效率低”、“标注工具与深度学习算法脱节”、“重叠目标交互混乱”、“切图卡顿及状态丢失”等核心痛点，LabelImg2 深度打通了**交互式高精度手动标注**、**YOLO 实时推理与自动批注**、**数据集闭环自训练与微调**以及**极速内存级会话响应**，构建了工业级的目标检测标注生产力套件。

---

## 3. 核心架构与特性升级对比

| 功能维度 | 基线 `chinakook/labelImg2` / 经典 `labelImg` | LabelImg2 (v1.0.0 正式稳定版) |
| :--- | :--- | :--- |
| **AI 自动辅助标注** | 不支持（完全依赖人工纯手动标框） | **内置 YOLO 模型中心**：支持单图秒级推断与全文件夹多线程后台批量自动批注，画布与列表实时无缝同步。 |
| **批注应用策略** | 仅支持覆盖写入 | **双模式自由切换**：支持“完全覆盖替换模式”与“追加合并模式”（基于 IoU > 0.85 自动去重，完美保留原图已有标注）。 |
| **模型闭环自训练** | 不支持（需手动切分数据并外部写代码训练） | **内置模型训练控制台**：免写代码，一键划分训练/验证集，可视化流式监控 Loss / mAP50 曲线并即时导出权重。 |
| **OBB 旋转标注体验** | 固定角度步长微调，效率低且操作繁琐 | **长按动态变速加速旋转**：短按 1.0° 精准微调，长按平滑加速至 1.5°（2秒达峰值），松开即刻平稳复位。 |
| **OBB 尺寸独立控制** | 仅能整体等比缩放或拖角 | **主副轴长度独立缩放**：`X` 键沿主轴方向微调长度，`C` 键沿副轴方向微调宽度，不产生角度畸变。 |
| **重叠目标层级渲染** | 大小框重合时底层目标无法选取 | **面积自适应层级排序**：大框自动置底、小框优先置顶，点击拾取与边界判断精准分层。 |
| **负样本 (0目标) 保存** | 易丢失空标签文件或误报异常 | **标准化空标签持久化**：空图片保存时自动弹出负样本确认对话框，生成标准化 0-object XML 标签文件。 |
| **切图响应与性能** | 切图时同步阻塞扫描磁盘，造成卡顿 | **0 毫秒极速内存统计**：内存级维护标注计数缓存，切图、长按快翻极致丝滑无延迟，总数绝不跳动闪烁。 |
| **会话修改状态追踪** | 列表颜色状态易在刷新后丢失 | **永久荧光绿会话标识**：本次运行期间新建、修改或保存的文件始终保持荧光绿高亮，未标注文件浅灰区分。 |
| **误触防篡改保护** | 鼠标滚轮滑动查看界面时易误改参数 | **控件防误触锁定机制**：下拉选择框与微调数值框未展开时自动禁用滚轮切换，防止滑动浏览时改乱参数。 |
| **软件分发与启动** | 仅支持手动配置环境启动 | **双轨分发体系**：提供一键安装向导程序（.exe）与一键自动启动脚本（.bat），开箱即用。 |

---

## 4. 核心功能深度解析

### 4.1 YOLO AI 模型中心与推理引擎
- **全系列模型无缝兼容**：原生支持 Ultralytics YOLOv8、YOLOv11 及自定义 YOLO 系列权重（`.pt`、`.onnx`、`.engine`）。
- **硬件环境自适应检测**：自动识别 NVIDIA CUDA GPU 硬件加速并智能回退至 CPU 推理模式。
- **高精度阈值动态调节**：提供置信度阈值（Confidence）与非极大值抑制（NMS IoU）实时微调滑动条。
- **类别过滤与标签映射**：支持勾选启用指定检测类别，并在保存前直接对目标标签进行重命名映射。
- **相互独立的路径记忆机制**：图片目录与标签保存目录完全解耦并独立持久化存储，每次启动自动恢复上次真实工作路径。

### 4.2 双模式自动批注系统
- **完全覆盖模式 (Full Overwrite)**：清空当前图片旧标签，完全采用模型最新预测结果进行覆盖保存。
- **追加合并模式 (Append & Merge)**：完好保留原图已存在的手动标注（含旋转框角度、属性、颜色等），自动追加模型新检测出的目标，并通过 0.85 IoU 阈值智能过滤重复框。
- **全数据集后台批量处理**：支持对整个文件夹进行多线程并发批注，进度条与日志终端实时可见，处理完成后可在工作台即刻审查微调。

### 4.3 零代码模型闭环自训练控制台
- **免代码一键数据集构建**：指定图像与标签路径，系统全自动完成训练集与验证集的比例划分并生成数据配置文件。
- **丰富超参数自由配置**：支持预训练模型选择、迭代轮次（Epochs）、批次大小（Batch Size）、输入分辨率（640~1280）等调节。
- **流式实时监控看板**：实时流式可视化呈现 Epoch 轮次、Batch 进度、Box Loss、Class Loss、mAP50 及 mAP50-95，训练完成后一键应用至自动标注引擎。

### 4.4 OBB 任意角度旋转框与精准尺寸控制
- **动态变速旋转 (`Z` / `V`)**：短按单步 1.0° 像素级精调，长按平滑加速至 1.5° 实现大角度极速旋转。
- **独立主副轴微调 (`X` / `C`)**：支持沿主轴增加长度（`X`）与沿副轴增加宽度（`C`），大幅提升密集旋转目标框定效率。
- **面积自适应分层机制**：小目标永远浮于大背景目标之上，彻底消除多框重叠时选中混乱与中心红点漂移问题。

### 4.5 工业级交互体验与数据安全保障
- **0 毫秒极速统计系统**：右下角实时统计“本次”（本次打开工具新增的所有标签框数）与“总计”（当前项目全部存量标签框数），纯内存秒级响应，切图不再卡顿。
- **永久荧光绿会话高亮**：本次运行期间处理过的文件保持醒目荧光绿，已存标签文件浅灰呈现，未标注文件透明呈现。
- **负样本保存弹窗确认**：对 0 目标图片保存操作执行弹窗确认，避免误建空文件，确保负样本数据集规范。

---

## 5. 标准标注作业流程

### 5.1 水平矩形框 (Horizontal Box) 标注流程
1. 启动工作台，通过 **修改保存目录 (`Ctrl + R`)** 选定标签输出路径；
2. 通过 **打开目录 (`Ctrl + U`)** 选择图像数据集所在文件夹；
3. 按下 **`W`** 键进入矩形框绘制模式，在画布上按住鼠标左键拖拽选定目标区域；
4. 在弹出的类别列表中选择或输入标签名称并确认；
5. 按下 **`Ctrl + S`** 保存标注，或按 **`D`** 切换至下一张图片（自动触发自动保存）。

### 5.2 任意角度旋转框 (OBB / Rotated Box) 标注流程
1. 按下 **`E`** 键进入旋转框绘制模式，在画布上拖拽生成初始旋转框；
2. 选中旋转框，使用 **`Z`**（顺时针）或 **`V`**（逆时针）旋转微调角度；
3. 使用 **`X`** 调整长度、**`C`** 调整宽度，贴合倾斜目标边界；
4. 标注文件将自动以 `<robndbox>` 格式记录中心坐标 `cx, cy`、尺寸 `w, h` 以及旋转弧度 `angle`。

---

## 6. 常用快捷键速查表

| 快捷键 | 功能说明 | 作用范围 / 上下文 |
| :--- | :--- | :--- |
| **`W`** | 新建常规水平矩形标注框 (Draw Rect Box) | 画布视图 |
| **`E`** | 新建 OBB 任意角度旋转标注框 (Draw Rotated Box) | 画布视图 |
| **`Z`** (单击 / 长按) | 顺时针旋转标注框 (1.0° 微调至 1.5° 动态加速) | 选中的旋转框 |
| **`V`** (单击 / 长按) | 逆时针旋转标注框 (1.0° 微调至 1.5° 动态加速) | 选中的旋转框 |
| **`X`** | 沿主轴方向增大标注框长度 (Length +) | 选中的标注框 |
| **`C`** | 沿副轴方向增大标注框宽度 (Width +) | 选中的标注框 |
| **`Q` / `Delete`** | 立即删除选中的标注框 (支持拖拽中瞬时秒删) | 选中的标注框 |
| **`Ctrl + D`** | 在当前坐标原地复制生成副本标注框 | 选中的标注框 |
| **`R`** | 单键循环切换 撤销 (Undo) 与 恢复 (Redo) | 标注历史管理 |
| **`Ctrl + S`** | 手动保存当前图片标注文件 | 文件存盘 |
| **`A` / `D`** | 切换到 上一张 / 下一张 图片 (支持长按极速快翻) | 数据集浏览 |
| **`Ctrl + U`** | 打开图片所在文件夹 (Open Dir) | 工作区管理 |
| **`Ctrl + R`** | 修改标注保存目标文件夹 (Change Save Dir) | 工作区管理 |
| **`Ctrl + 滚轮`** | 画布无级平滑缩放 (Zoom In / Out) | 画布视图 |
| **`Alt + 鼠标拖拽`** | 自由平移拖动画布视野 (Pan Canvas) | 画布视图 |

---

## 7. 支持的标注数据格式

- **Pascal VOC XML (`.xml`)**：标准 XML 格式，包含 `<bndbox>`（`xmin, ymin, xmax, ymax`）及 `<robndbox>`（`cx, cy, w, h, angle`）。
- **YOLO 归一化 TXT (`.txt`)**：标准化归一化坐标格式，支持标准目标检测框与旋转框角度参数。
- **Create ML JSON (`.json`)**：苹果 Create ML 目标检测标准格式。
- **COCO JSON (`.json`)**：微软 COCO 数据集标准结构。

---

## 8. 版本演进与路线图

### v1.0.0 (当前正式稳定版)
- 完整支持水平框与 OBB 动态变速旋转框标注。
- 内置 YOLO 模型中心，支持单图与全目录双模式自动批注。
- 内置免代码模型闭环自训练与实时监控控制台。
- 0 毫秒极速内存统计系统，杜绝切图卡顿与数字抖动。
- 独立 Windows 图形化安装程序（.exe）与免配置启动脚本（.bat）。

### v2.0.0 (未来演进规划)
- 关键点检测与多边形实例分割标注支持 (YOLOv8-Pose / YOLOv8-Seg)。
- 主动学习 (Active Learning) 样本价值评估与优先标注推荐。
- 视频连续时序帧半监督自动跟踪与批注。
- 云端存储对象存储同步 (S3 / MinIO / OSS) 与多人协作审核流。

---

## 9. 开源协议与鸣谢

LabelImg2 基于 [MIT 开源许可证](LICENSE) 发布。

由衷感谢以下优秀开源项目为计算机视觉社区作出的卓越贡献：
- [chinakook/labelImg2](https://github.com/chinakook/labelImg2)
- [tzutalin/labelImg](https://github.com/heartexlabs/labelImg)
- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)

---

<div align="center">
<b>LabelImg2 开发团队</b> &bull; 打造下一代计算机视觉基础设施
</div>

