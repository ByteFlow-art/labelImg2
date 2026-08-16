import os
import traceback
from typing import Dict, Any, Optional
from core.qt_compat import QThread, pyqtSignal
from core.dataset_converter import DatasetConverter
from core.yolo_trainer import YOLOTrainer

class ModelTrainerThread(QThread):
    """
    后台模型训练与数据集转换 QThread 线程
    """
    log_signal = pyqtSignal(str)                                         # 日志输出文本
    epoch_progress_signal = pyqtSignal(int, int, float, float, float, float) # (epoch, total, box_loss, cls_loss, mAP50, mAP95)
    detailed_progress_signal = pyqtSignal(int, int, int, int, float, float, float, float, float) # (epoch, total, batch, total_batches, pct, box_loss, cls_loss, mAP50, mAP95)
    train_finished_signal = pyqtSignal(str, str)                         # (best_pt_path, data_yaml_path)
    train_error_signal = pyqtSignal(str)                                 # (error_message)

    def __init__(
        self,
        image_dir: str = "",
        dataset_path: str = "",
        xml_dir: Optional[str] = None,
        base_model: str = "yolov8n.pt",
        epochs: int = 50,
        imgsz: int = 640,
        batch_size: int = 16,
        val_ratio: float = 0.2,
        device: str = "0",
        output_name: str = "custom_yolo"
    ):
        super().__init__()
        self.image_dir = image_dir or dataset_path
        self.xml_dir = xml_dir
        self.base_model = base_model
        self.epochs = epochs
        self.imgsz = imgsz
        self.batch_size = batch_size
        self.val_ratio = val_ratio
        self.device = device
        self.output_name = output_name
        self.trainer = YOLOTrainer()
        self.is_stopped = False

    def stop(self):
        self.is_stopped = True
        if hasattr(self, 'trainer') and self.trainer:
            self.trainer.stop_requested = True
        try:
            self.terminate()
        except Exception:
            pass

    def run(self):
        try:
            self.log_signal.emit("=== 正在准备数据集 ===")
            
            # 判断 image_dir 是已有的 data.yaml 还是包含图片的文件夹
            if os.path.isfile(self.image_dir) and self.image_dir.endswith(".yaml"):
                data_yaml_path = self.image_dir
                self.log_signal.emit(f"检测到用户指定的 data.yaml: {data_yaml_path}")
            else:
                output_dataset_dir = os.path.join(os.path.dirname(self.image_dir), "yolo_converted_dataset")
                self.log_signal.emit(f"正在读取【图片目录: {self.image_dir}】与【XML 标注目录: {self.xml_dir}】...")
                self.log_signal.emit(f"自动转换为 YOLO 规范数据集 (输出至: {output_dataset_dir})...")
                
                data_yaml_path, class_list, total_imgs = DatasetConverter.voc_to_yolo_dataset(
                    image_dir=self.image_dir,
                    xml_dir=self.xml_dir,
                    output_dataset_dir=output_dataset_dir,
                    val_ratio=self.val_ratio
                )
                
                self.log_signal.emit(f"数据集转换成功！检测到类别数: {len(class_list)} {class_list}，有效图像: {total_imgs} 张")
                self.log_signal.emit(f"生成 dataset.yaml 路径: {data_yaml_path}")

            self.log_signal.emit("\n=== 正在启动 YOLO 模型训练引擎 ===")

            def on_epoch_end(epoch: int, total: int, metrics: Dict[str, float]):
                b_loss = metrics.get("box_loss", 0.0)
                c_loss = metrics.get("cls_loss", 0.0)
                map50 = metrics.get("mAP50", 0.0)
                map95 = metrics.get("mAP50-95", 0.0)
                pct = metrics.get("pct", (epoch / total * 100.0))
                batch = int(metrics.get("batch", 1))
                total_batches = int(metrics.get("total_batches", 1))
                
                log_text = f"[Epoch {epoch}/{total} | Batch {batch}/{total_batches}] 训练进度: {pct:.1f}% | Box: {b_loss:.4f} | Cls: {c_loss:.4f} | mAP50: {map50:.4f}"
                self.log_signal.emit(log_text)
                self.epoch_progress_signal.emit(epoch, total, b_loss, c_loss, map50, map95)
                self.detailed_progress_signal.emit(epoch, total, batch, total_batches, pct, b_loss, c_loss, map50, map95)

            project_dir = os.path.join(os.getcwd(), "runs", "train")
            
            best_pt_path = self.trainer.train_model(
                base_model=self.base_model,
                data_yaml=data_yaml_path,
                epochs=self.epochs,
                imgsz=self.imgsz,
                batch_size=self.batch_size,
                device=self.device,
                project_dir=project_dir,
                name=self.output_name,
                epoch_callback=on_epoch_end,
                log_callback=lambda msg: self.log_signal.emit(msg)
            )

            self.train_finished_signal.emit(best_pt_path, data_yaml_path)

        except Exception as e:
            err_trace = traceback.format_exc()
            self.log_signal.emit(f"\n❌ 训练过程中发生严重错误:\n{err_trace}")
            self.train_error_signal.emit(str(e))
