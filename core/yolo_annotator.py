import os
from typing import List, Dict, Any, Optional

class YOLOAnnotator:
    """
    YOLO 模型推理与自动标注核心封装类
    """
    def __init__(self):
        self.model = None
        self.model_path = None
        self.class_names: Dict[int, str] = {}
        self.device = 'cuda' if self.is_cuda_available() else 'cpu'

    @staticmethod
    def is_cuda_available() -> bool:
        """检查 PyTorch 是否有 CUDA 支持"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def load_model(self, model_path: str, device: Optional[str] = None) -> Dict[int, str]:
        """
        加载 YOLO 模型权重 (.pt)

        :param model_path: YOLO 模型路径
        :param device: 指定运行设备 'cuda', 'cpu', 或 None (自动)
        :return: 模型的类别字典 {class_id: class_name}
        """
        from ultralytics import YOLO

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"未找到模型文件: {model_path}")

        if device:
            self.device = device

        self.model = YOLO(model_path)
        self.model_path = model_path
        
        # 提取类别名称 (兼容 dict 与 list/tuple 格式)
        if hasattr(self.model, 'names') and self.model.names:
            names = self.model.names
            if isinstance(names, dict):
                self.class_names = {int(k): str(v) for k, v in names.items()}
            elif isinstance(names, (list, tuple)):
                self.class_names = {i: str(v) for i, v in enumerate(names)}
            else:
                self.class_names = {}
        else:
            self.class_names = {}

        return self.class_names

    def predict_image(
        self, 
        image_path: str, 
        conf_threshold: float = 0.25, 
        iou_threshold: float = 0.45,
        enabled_classes: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        对单张图片进行目标检测推断

        :param image_path: 图片路径
        :param conf_threshold: 置信度阈值
        :param iou_threshold: NMS IoU 阈值
        :param enabled_classes: 运行检测的类别 ID 列表，为 None 则包含所有类别
        :return: 标注框数据列表
        """
        if self.model is None:
            raise RuntimeError("YOLO 模型未加载，请先调用 load_model()")

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"未找到目标图片文件: {image_path}")

        results = self.model.predict(
            source=image_path,
            conf=conf_threshold,
            iou=iou_threshold,
            device=self.device,
            verbose=False,
            classes=enabled_classes
        )

        detected_boxes = []
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            for box in boxes:
                # 提取 xyxy 坐标、置信度与类别 ID
                xyxy = box.xyxy[0].cpu().numpy().tolist()
                confidence = float(box.conf[0].cpu().item())
                cls_id = int(box.cls[0].cpu().item())
                cls_name = self.class_names.get(cls_id, f"class_{cls_id}")

                xmin, ymin, xmax, ymax = round(xyxy[0], 2), round(xyxy[1], 2), round(xyxy[2], 2), round(xyxy[3], 2)
                
                detected_boxes.append({
                    'class_id': cls_id,
                    'class_name': cls_name,
                    'confidence': round(confidence, 4),
                    'bbox': [xmin, ymin, xmax, ymax]
                })

        return detected_boxes
