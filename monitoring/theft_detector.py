"""
theft_detector.py
------------------------------------
Theft detection + Telegram photo alert module
------------------------------------
Detects theft (based on YOLOv8 custom model class 3 = 'product_concealed')
Sends snapshot image + caption to Telegram when theft occurs.
"""

import os
import time
from datetime import datetime
from collections import deque
import cv2
import requests
from ultralytics import YOLO


class TheftDetector:
    def __init__(self):
        # =====================================================
        # 🔹 Fixed Paths (configured once)
        # =====================================================
        self.model_path = r"D:\RetailX\backend\models\theft_detection\weights\best.pt"  # ✅ your trained model
        self.dataset_dir = r"D:\RetailX\backend\dataset"  # optional: your dataset path
        self.output_dir = r"D:\RetailX\backend\alerts"    # where theft snapshots are saved

        os.makedirs(self.output_dir, exist_ok=True)

        # =====================================================
        # 🔹 YOLO + Detection Settings
        # =====================================================
        self.device = 0  # 0 = GPU, -1 = CPU
        self.conf_thresh = 0.25
        self.alert_frames_threshold = 3
        self.alert_cooldown = 30
        self.max_buffer_len = 10

        # =====================================================
        # 🔹 Telegram Config
        # =====================================================
        self.use_telegram = True
        self.telegram_token = "8248379458:AAGVUKXqq7uGl1fVroKOhoxs9YvdqFrA12o"      # ✅ Replace with your Telegram bot token
        self.telegram_chat_id = "1929838160"            # ✅ Replace with your chat ID

        # =====================================================
        # 🔹 Initialize YOLO model
        # =====================================================
        print(f"🚀 Loading YOLO theft detection model: {self.model_path}")
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"❌ Model not found at {self.model_path}")
        self.model = YOLO(self.model_path)

        # Class mapping
        self.class_names = ['person', 'hand', 'product_visible', 'product_concealed']
        self.product_concealed_id = 3

        # State
        self.history = deque(maxlen=self.max_buffer_len)
        self.consecutive_count = 0
        self.last_alert_time = 0

        print("✅ TheftDetector initialized successfully!")
        print(f"📦 Model Path     : {self.model_path}")
        print(f"📁 Dataset Path   : {self.dataset_dir}")
        print(f"💾 Alerts Saved To: {self.output_dir}")

    # ------------------------------------------------
    # Drawing + Alert Helpers
    # ------------------------------------------------
    def _draw_detections(self, frame, boxes, classes, scores):
        for (x1, y1, x2, y2), c, s in zip(boxes, classes, scores):
            color = (0, 0, 255) if c == self.product_concealed_id else (0, 255, 0)
            label = self.class_names[c] if c < len(self.class_names) else str(c)
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            cv2.putText(frame, f"{label} {s:.2f}", (int(x1), max(int(y1) - 6, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        return frame

    def _send_telegram_photo(self, image_path, caption):
        if not self.use_telegram or not self.telegram_token or not self.telegram_chat_id:
            print("⚠️ Telegram disabled or missing config.")
            return False
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendPhoto"
            with open(image_path, "rb") as photo:
                files = {"photo": photo}
                data = {"chat_id": self.telegram_chat_id, "caption": caption}
                r = requests.post(url, data=data, files=files, timeout=15)
            if r.status_code == 200:
                print("✅ Telegram alert sent successfully.")
                return True
            else:
                print("❌ Telegram error:", r.text)
                return False
        except Exception as e:
            print("⚠️ Telegram send failed:", e)
            return False

    # ------------------------------------------------
    # Main Theft Detection Loop
    # ------------------------------------------------
    def run(self, source=0):
        """
        Run live detection (default: webcam)
        Change `source` to a video file if needed.
        """
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print(f"❌ Cannot open video source: {source}")
            return

        print("🎥 Theft detection started (press 'q' to stop).")
        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ Stream ended.")
                break

            results = self.model.predict(frame, device=self.device, imgsz=640,
                                         conf=self.conf_thresh, verbose=False)
            res = results[0]
            boxes, classes, scores = [], [], []

            if res.boxes is not None and len(res.boxes) > 0:
                xyxy = res.boxes.xyxy.cpu().numpy()
                confs = res.boxes.conf.cpu().numpy()
                clss = res.boxes.cls.cpu().numpy().astype(int)
                for b, c, s in zip(xyxy, clss, confs):
                    boxes.append([int(b[0]), int(b[1]), int(b[2]), int(b[3])])
                    classes.append(int(c))
                    scores.append(float(s))

            concealed_detected = any(c == self.product_concealed_id for c in classes)
            self.history.append(1 if concealed_detected else 0)
            self.consecutive_count = self.consecutive_count + 1 if concealed_detected else 0

            now = time.time()
            if self.consecutive_count >= self.alert_frames_threshold and (now - self.last_alert_time > self.alert_cooldown):
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                snapshot_path = os.path.join(self.output_dir, f"theft_{ts}.jpg")

                annotated = self._draw_detections(frame.copy(), boxes, classes, scores)
                cv2.putText(annotated, f"ALERT: Theft Detected ({ts})", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                cv2.imwrite(snapshot_path, annotated)
                print(f"🚨 Theft detected! Snapshot saved: {snapshot_path}")

                caption = f"🚨 Theft Detected at {ts}\nSnapshot attached."
                self._send_telegram_photo(snapshot_path, caption)

                self.last_alert_time = now
                self.consecutive_count = 0
                self.history.clear()

            annotated = self._draw_detections(frame.copy(), boxes, classes, scores)
            cv2.imshow("Smart Theft Detection", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        cv2.destroyAllWindows()
        print("🟢 Detection stopped.")
