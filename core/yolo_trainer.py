import os
import sys
from typing import Callable, Optional, Dict, Any

class YOLOTrainer:
    """
    YOLO 模型训练封装模块
    """
    def __init__(self):
        self.model = None

    def train_model(
        self,
        base_model: str,
        data_yaml: str,
        epochs: int = 50,
        imgsz: int = 640,
        batch_size: int = 16,
        device: str = "0",
        project_dir: str = "runs/train",
        name: str = "custom_exp",
        epoch_callback: Optional[Callable[[int, int, Dict[str, float]], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        开始训练 YOLO 目标检测模型

        :param base_model: 预训练基础模型名称或 .pt 路径 (如 'yolov8n.pt', 'yolov11n.pt')
        :param data_yaml: 数据集配置文件 data.yaml 路径
        :param epochs: 迭代轮数
        :param imgsz: 图像分辨率大小 (如 640)
        :param batch_size: 批次大小 (如 8, 16)
        :param device: 设备指示 ('0', 'cpu', 'cuda')
        :param project_dir: 训练输出工程目录
        :param name: 实验名称
        :param epoch_callback: 每轮训练结束的回调函数 (epoch, total_epochs, metrics_dict)
        :param log_callback: 日志文本回调函数
        :return: 训练出的 best.pt 完整模型权重路径
        """
        from ultralytics import YOLO

        if log_callback:
            log_callback(f"正在准备加载基础模型: {base_model} ...")

        # 检查是否为相对文件名且本地根目录已存在该权重
        local_root_pt = os.path.abspath(base_model)
        if not os.path.exists(base_model) and os.path.exists(local_root_pt):
            base_model = local_root_pt

        try:
            self.model = YOLO(base_model)
        except Exception as e:
            err_str = str(e)
            if "Download failure" in err_str or "github" in err_str.lower() or "Curl" in err_str:
                raise RuntimeError(
                    f"从 GitHub 下载基础权重 {base_model} 失败（网络连接超时）！\n"
                    f"【解决办法】：\n"
                    f"1. 请在浏览器中直接下载 {base_model} 文件并放到软件根目录下：{os.getcwd()}\n"
                    f"2. 或在界面下拉菜单中选择【自定义 .pt 模型...】指向您电脑本地已有任何 YOLO 权重。"
                ) from e
            raise e

        self.stop_requested = False

        # 挂载回调监控训练进度与安全终止
        def handle_progress(trainer, is_epoch_end=False):
            if self.stop_requested:
                trainer.stop = True
                if log_callback:
                    log_callback("用户已请求取消/终止模型训练...")
                return

            current_epoch = trainer.epoch + 1
            total_epochs = trainer.epochs
            batch_idx = getattr(trainer, 'batch_idx', 0) + 1
            total_batches = getattr(trainer, 'nb', 1) or 1

            if is_epoch_end:
                progress_pct = min(100.0, (current_epoch / total_epochs) * 100.0)
            else:
                progress_pct = min(99.9, ((trainer.epoch + (batch_idx / total_batches)) / max(1, total_epochs)) * 100.0)

            metrics = {
                "box_loss": 0.0,
                "cls_loss": 0.0,
                "mAP50": 0.0,
                "mAP50-95": 0.0,
                "pct": progress_pct,
                "batch": batch_idx,
                "total_batches": total_batches
            }

            try:
                # 安全提取 loss_items
                if hasattr(trainer, 'loss_items') and trainer.loss_items is not None:
                    items = trainer.loss_items
                    if hasattr(items, 'tolist'):
                        items = items.tolist()

                    if isinstance(items, (list, tuple)):
                        if len(items) > 0:
                            metrics["box_loss"] = float(items[0])
                        if len(items) > 1:
                            metrics["cls_loss"] = float(items[1])
                    elif isinstance(items, dict):
                        metrics["box_loss"] = float(items.get("box_loss", items.get(0, 0.0)))
                        metrics["cls_loss"] = float(items.get("cls_loss", items.get(1, 0.0)))

                # 安全提取 mAP 评估指标
                if hasattr(trainer, 'metrics') and trainer.metrics:
                    m = trainer.metrics
                    metrics["mAP50"] = float(m.get("metrics/mAP50(B)", m.get("mAP50", 0.0)))
                    metrics["mAP50-95"] = float(m.get("metrics/mAP50-95(B)", m.get("mAP50-95", 0.0)))

            except Exception:
                pass

            if epoch_callback:
                epoch_callback(current_epoch, total_epochs, metrics)

        if epoch_callback:
            self.model.add_callback("on_train_batch_end", lambda tr: handle_progress(tr, is_epoch_end=False))
            self.model.add_callback("on_fit_epoch_end", lambda tr: handle_progress(tr, is_epoch_end=True))

        if log_callback:
            log_callback(f"开始训练引擎 [Device: {device}, Epochs: {epochs}, ImgSize: {imgsz}, Batch: {batch_size}]...")

        try:
            results = self.model.train(
                data=data_yaml,
                epochs=epochs,
                imgsz=imgsz,
                batch=batch_size,
                device=device,
                project=project_dir,
                name=name,
                exist_ok=True,
                verbose=True,
                workers=0
            )
        except Exception as e:
            err_str = str(e)
            if "CUDA" in err_str or "out of memory" in err_str or "device" in err_str.lower():
                if log_callback:
                    log_callback(f"提示: GPU 设备 ({device}) 出错，降级为 CPU 模式重试...")
                results = self.model.train(
                    data=data_yaml,
                    epochs=epochs,
                    imgsz=imgsz,
                    batch=batch_size,
                    device="cpu",
                    project=project_dir,
                    name=name,
                    exist_ok=True,
                    verbose=True,
                    workers=0
                )
            else:
                raise e

        # 查找保存出的 best.pt 文件路径
        save_dir = str(results.save_dir) if hasattr(results, 'save_dir') else os.path.join(project_dir, name)
        best_pt_path = os.path.join(save_dir, "weights", "best.pt")

        if not os.path.exists(best_pt_path):
            # 兜底查找 last.pt 或 save_dir 下的 pt
            last_pt_path = os.path.join(save_dir, "weights", "last.pt")
            if os.path.exists(last_pt_path):
                best_pt_path = last_pt_path

        if log_callback:
            log_callback(f"模型训练已顺利完成！最优权重导出于: {best_pt_path}")

        return best_pt_path
