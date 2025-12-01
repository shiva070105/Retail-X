import cv2
import numpy as np
from typing import List
from ultralytics import YOLO

def detect_objects(model: YOLO, image: np.ndarray, confidence_threshold: float = 0.5) -> List[str]:
    """
    Detect objects in image using YOLO model and return list of detected product names.
    """
    try:
        # Run inference
        results = model(image, conf=confidence_threshold)
        
        detected_names = []
        
        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    class_id = int(box.cls.item())
                    confidence = box.conf.item()
                    
                    # Get class name from model
                    class_name = model.names[class_id]
                    detected_names.append(class_name)
        
        return detected_names
        
    except Exception as e:
        print(f"Error in object detection: {e}")
        return []

def detect_objects_with_confidence(model: YOLO, image: np.ndarray, confidence_threshold: float = 0.5) -> List[dict]:
    """
    Detect objects with confidence scores and bounding boxes.
    """
    try:
        results = model(image, conf=confidence_threshold)
        
        detections = []
        
        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    class_id = int(box.cls.item())
                    confidence = box.conf.item()
                    class_name = model.names[class_id]
                    
                    # Get bounding box coordinates
                    bbox = box.xyxy[0].tolist() if box.xyxy is not None else []
                    
                    detections.append({
                        'product_name': class_name,
                        'confidence': confidence,
                        'bbox': bbox
                    })
        
        return detections
        
    except Exception as e:
        print(f"Error in detailed object detection: {e}")
        return []