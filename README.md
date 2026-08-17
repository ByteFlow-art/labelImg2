<div align="center">

<img src="img/labelImg2.png" width="160" height="160" alt="LabelImg2 Logo" />

# LabelImg2 Next-Gen
### ⚡ 新一代 AI 智能计算机视觉标注与模型自训练一体化工作台
**Deep Learning Auto-Annotation & Model Self-Training Workstation for Object Detection (Horizontal & Oriented Bounding Box)**

[![Python](https://img.shields.io/badge/Python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/GUI-PyQt5%20v5.15+-green.svg?logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![PyTorch](https://img.shields.io/badge/Deep%20Learning-PyTorch%20%2F%20CUDA-EE4C2C.svg?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![Ultralytics](https://img.shields.io/badge/YOLO-v8%20%7C%20v11%20%7C%20v26-blueviolet.svg)](https://github.com/ultralytics/ultralytics)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[**📥 立即下载独立绿色版 (.exe)**](https://github.com/ByteFlow-art/labelImg2/releases) • [**⚡ 一键环境自动搭建**](#-模式二下载源码包--一键自动化启动-推荐开发者) • [**📖 功能对标与对比**](#-对标-chinakooklabelimg2-核心特性升级对比) • [**⌨️ 快捷键速查**](#-快捷键速查表-hotkeys-cheat-sheet)

</div>

---

## 📥 软件下载专区 (Quick Download)

| 版本类型 | 操作系统 | 下载链接 | 说明 |
| :--- | :--- | :--- | :--- |
| ⚡ **LabelImg2 官方安装程序 (.exe)** | Windows 10 / 11 (x64) | [**⬇️ GitHub Releases 下载 (Setup)**](https://github.com/ByteFlow-art/labelImg2/releases) | **🌟 普通用户首选**：下载独立安装程序，运行图形化安装向导，全自动搭建环境并在电脑桌面生成专属 App 图标 |
| 📦 **LabelImg2 源码完整包 (Source Code)** | Windows / Linux / macOS | [**⬇️ 下载 Source Code (.zip)**](https://github.com/ByteFlow-art/labelImg2/archive/refs/heads/master.zip) | **🌟 开发者与便携用户首选**：下载源码解压后，直接双击 `Start_LabelImg2.bat` 或 `LabelImg2.lnk` 即可秒启 |

---

## 📖 项目简介与背景 (Introduction)

本项目深度对标并全方位重构升级自知名开源标注工具 **[chinakook/labelImg2](https://github.com/chinakook/labelImg2.git)** 与经典的 **LabelImg**。

在继承原版优秀的水平矩形框（Horizontal Box）、任意角度旋转框（Oriented Bounding Box, OBB）、Pascal VOC XML、YOLO TXT 标注能力的基础上，**LabelImg2 Next-Gen** 全面突破了传统标注软件“纯手工低效画框”、“标注与算法脱节”、“多框重叠交互冲突”等痛点，构建了**集「高精度手动标注 + YOLO 深度学习模型中心 + 单图/批量一键自动批注 + 数据集闭环自训练」于一体的现代化专业标注工作台**。

无论是普通计算机视觉任务、遥感航拍目标检测、工业缺陷质检，还是无人机与自动驾驶场景，LabelImg2 Next-Gen 都能提供极致丝滑的生产力加速体验。

---

## 🚀 对标 `chinakook/labelImg2` 核心特性升级对比

| 功能维度 | 原版 `chinakook/labelImg2` / 经典 LabelImg | 🌟 **LabelImg2 Next-Gen (本项目)** |
| :--- | :--- | :--- |
| **AI 自动辅助标注** | ❌ 无，完全依赖纯手动标框 | ✅ **内置 YOLO 智能标注中心**，支持单图秒级推断与全文件夹批量自动批注，画布无缝实时刷新审查 |
| **模型自训练与迭代** | ❌ 无，需手动导出数据切分并编写训练脚本 | ✅ **内置模型训练控制台**，无需写代码，一键从当前标注数据微调训练专属 YOLO 模型，实时流式监控 Loss / mAP50 |
| **OBB 旋转标注体验** | ⚠️ 固定步长旋转，易手酸卡顿 | ✅ **长按动态变速旋转 (1.0°~1.5° 2秒渐进)**，X/C 键长宽独立微调，松开瞬间平稳重置 |
| **重叠目标层级渲染** | ⚠️ 多个重合框无法精确选取底层/顶层 | ✅ **面积自适应层级排序**：大框自动置底、小框置顶，点击响应与命中判定精准分层 |
| **零目标/空图片处理** | ⚠️ 容易丢失空标签或抛出异常 | ✅ **0 标注自动保存**：自动生成标准化 0-object 空 XML 标签并创建对应文件夹，完美适配负样本训练 |
| **快捷操作与防错机制** | ⚠️ 易误触丢失修改，回退机制单一 | ✅ **全方位数据防丢失保护**（切换/退出智能三态弹窗）；**R 键单键循环回退/重做 (Undo/Redo)**；**Q / Delete 统一秒删** |
| **软件安装与启动** | ⚠️ 依赖本地 Python 与命令行手动配置 | ✅ **双模极速体验**：支持**独立安装程序 (.exe)** 与 **源码一键启动脚本 (`Start_LabelImg2.bat`)** |
| **UI 交互美学** | 传统经典风格 | ✅ **现代化 Workstation 轻量工作台**，高对比度设计，去除冗余杂乱提示，任务栏独立 App 图标 |

---

## 🌟 核心功能深度解析 (Key Features)

### 1. 🤖 YOLO 模型中心 (Model Center)
- **多模型无缝管理**：内置支持 YOLOv8、YOLOv11、YOLO26 等系列权重（`.pt`、`.onnx`、`.engine`），支持本地模型库自动检索与自定义导入。
- **硬件自适应检测**：自动识别 NVIDIA CUDA GPU 加速与 CPU 推理模式。
- **高精度参数调节**：提供置信度（Conf）与 NMS 重叠度（IoU）实时滑动条微调。
- **类别映射与过滤**：支持自定义选择启用检测类别，并可在导出时直接重命名标签映射。
- **模型验证弹窗**：一键测试模型加载，自适应展开类别列表与权重详情。

### 2. ⚡ 单图 / 批量自动标注 (Auto-Annotation)
- **双模式自由切换 (Dual Modes)**：
  - 🔄 **完全覆盖替换模式**：清空当前已有标签，完全以模型检测结果进行覆盖更新；
  - ➕ **追加合并模式**：保留原图已有的全部手动/已有标注，在此基础上追加 YOLO 新检测出的目标，并自动进行 IoU 重复框智能去重。
- **单图一键批注**：快捷键 `S` 或工具栏一键对当前图片进行 AI 推断，实时写出标准 XML/TXT 标注并自动刷新画布。
- **文件夹批量自动批注**：后台多线程批量推断整套数据集，进度条与统计终端实时可见，处理完毕后直接在工作台审查与微调。


### 3. 🏋️‍♂️ 模型自训练控制台 (Custom YOLO Trainer)
- **零代码闭环训练**：指定训练图片目录与标签目录，一键划分训练集/验证集。
- **丰富超参数设置**：支持预训练权重选择、Epochs、Batch Size、输入分辨率（Img Size 640~1280）、验证集比例等。
- **流式实时监控**：可视化看板实时监控总进度、Epoch、Batch、Box Loss、Cls Loss、mAP50、mAP50-95，训练完成后一键应用至自动标注引擎。

### 4. 🎯 OBB 旋转框与矩形标注全维度革新
- **Z / V 键长按动态变速旋转**：短按精细微调（1.0°），长按随时间线性加速至 1.5°（2秒达峰值），松开即刻重置，实现“微调精准、大角度疾旋”。
- **X / C 键长宽独立微调**：`X` 键沿主轴方向增大长度（Length+），`C` 键沿副轴方向增大宽度（Width+）。
- **面积自适应分层排序**：小目标优先显示在顶层，大背景框置于底层，彻底杜绝重叠误选。
- **绘制与选中状态彻底隔离**：修复按 `E` 键新建旋转框与已有模型标注框的交互冲突，彻底消除中心红点与标签跳变 bug。

### 5. 🛡️ 生产级数据安全与撤销系统
- **空标签文件夹与负样本自动持久化**：空图片切换时自动生成 0 目标 XML，右下角图片列表实时标注 `[0]` 徽章。
- **R 键单键循环撤销/恢复**：按一次 `R` 回退（Undo），再按一次恢复（Redo），快速对比修改前后状态。
- **全生命周期防丢保护**：未开启自动保存时，切换图片或关闭程序均弹出「保存 / 放弃更改 / 取消」标准三态对话框。

---

## 🛠️ 两种使用方式指引 (How to Use)

### 🔹 途径一：下载独立安装程序 (.exe) 【推荐普通用户】
1. 前往本项目的 **[GitHub Releases 页面](https://github.com/ByteFlow-art/labelImg2/releases)**；
2. 下载最新的安装程序包（`LabelImg2_Setup_v1.0.0.zip` 或 `LabelImg2_Setup_v1.0.0.exe`）；
3. 运行进入图形化安装向导，按提示完成安装；
4. 安装完成后，直接双击电脑桌面上生成的 **`LabelImg2`** 专属 App 图标即可启动使用！

---

### 🔹 途径二：下载源码包使用 (.bat 启动) 【推荐开发者】
本仓库已对源码包进行了极简化配置，无需每次敲写命令行：
1. 点击 **[⬇️ 下载 Source Code (.zip)]** 并解压到本地；
2. **首次使用**：直接双击根目录下的 **`Start_LabelImg2.bat`**（或带 App 图标的 **`LabelImg2.lnk`**），脚本将全自动检测并配置好 Python 与深度学习依赖环境；
3. **日常启动**：直接双击 **`Start_LabelImg2.bat`** 或 **`LabelImg2.lnk`** 秒级进入工作台；
4. **生成桌面图标**：双击 **`Create_Desktop_Shortcut.bat`** 即可一键在桌面生成专属 App 高清图标。

---



### 🔹 模式三：手动命令行安装 (Manual Installation)

```bash
# 1. 创建并激活 Python 虚拟环境 (推荐 Python 3.8 ~ 3.10)
conda create -n labelimg2 python=3.10 -y
conda activate labelimg2

# 2. 安装核心依赖包 (使用国内清华源极速下载)
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 启动 LabelImg2 工作台
python labelImg.py
```

---

## ⌨️ 快捷键速查表 (Hotkeys Cheat Sheet)

| 快捷键 | 功能说明 | 适用场景 |
| :--- | :--- | :--- |
| **`W`** | 新建常规水平矩形标注框 (Draw Rect Box) | 目标绘制 |
| **`E`** | 新建 OBB 任意角度旋转标注框 (Draw Rotated Box) | 旋转目标绘制 |
| **`Z`** (长按/连按) | 顺时针旋转标注框 (1.0° ~ 1.5° 动态变速加速) | 旋转微调/疾旋 |
| **`V`** (长按/连按) | 逆时针旋转标注框 (1.0° ~ 1.5° 动态变速加速) | 旋转微调/疾旋 |
| **`X`** | 增大选中标注框的长度 (Length +) | 尺寸微调 |
| **`C`** | 增大选中标注框的宽度 (Width +) | 尺寸微调 |
| **`Q` / `Delete`** | 立即删除选中的标注框 (支持鼠标拖拽中瞬时秒删) | 标注清理 |
| **`Ctrl + D`** | 在当前坐标原地复制生成副本标注框 | 密集目标标注 |
| **`R`** | 单键循环切换 撤销 (Undo) 与 恢复 (Redo) | 修改对比 |
| **`Ctrl + S`** | 手动保存当前图片标注 | 数据存盘 |
| **`A` / `D`** | 切换到 上一张 / 下一张 图片 (自动触发自动保存) | 数据集浏览 |
| **`Ctrl + 滑轮`** | 画布自由无极缩放 (Zoom In / Out) | 细节查看 |
| **`Alt + 左键拖拽`** | 自由平移拖动画布视野 (Pan Canvas) | 大图导航 |

---

## 📦 自行打包独立可执行文件 (.exe)

如果您对源码进行了二次开发，并希望自行打包为独立 `.exe` 分发：

```bash
# 执行自动化打包脚本 (基于 PyInstaller)
python build_exe.py

# 或在 Windows 下直接双击运行:
build_exe.bat
```
构建完成后，打包产物将自动生成于 `dist/LabelImg2/` 目录下，包含完整的执行文件、图标、预训练模型与静态依赖。

---

## 📂 标注格式与导出支持 (Annotation Formats)

- **Pascal VOC XML (`.xml`)**：标准 XML 格式，包含 `<robndbox>`（旋转框中心点坐标、长宽与角度）及 `<bndbox>`。
- **YOLO TXT (`.txt`)**：标准化归一化 YOLO 格式。
- **Create ML JSON (`.json`)**
- **COCO JSON (`.json`)**

---

## 🤝 致谢与开源协议 (Acknowledgements & License)

本项目在开源社区众多优秀工作的基础上演进而来，由衷感谢以下开源项目：
- **[chinakook/labelImg2](https://github.com/chinakook/labelImg2.git)**
- **[tzutalin/labelImg](https://github.com/heartexlabs/labelImg)**
- **[Ultralytics YOLO](https://github.com/ultralytics/ultralytics)**

本项目基于 [MIT 开源许可证](LICENSE) 发布。欢迎提交 Issue 与 Pull Request 共同完善！
