"""Person detection module using YOLOv8 for visitor recognition."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

import cv2
import numpy as np
from ultralytics import YOLO

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    """Result of a single person detection frame."""

    detected: bool
    confidence: float
    bbox: tuple[int, int, int, int] | None  # (x, y, w, h)
    distance_zone: str  # "too_close", "reception_zone", "too_far"


class PersonDetector:
    """
    Detects persons in camera feed using YOLOv8 and determines if they are in the
    reception zone (appropriate distance for interaction).

    The reception zone is defined by bounding box area being 5-15% of frame,
    indicating the person is at an optimal distance for the receptionist interaction.
    """

    def __init__(self, config: dict) -> None:
        """
        Initialize the person detector.

        Args:
            config: Configuration dict with keys:
                - camera_index: int, camera device index (default: 0)
                - model_path: str, path to YOLOv8 model (default: "yolov8n")
                - confidence_threshold: float, detection confidence (default: 0.70)
                - min_bbox_ratio: float, min bbox area ratio (default: 0.05)
                - max_bbox_ratio: float, max bbox area ratio (default: 0.15)
        """
        self.camera_index = config.get("camera_index", 0)
        self.model_path = config.get("model_path", "yolov8n")
        self.confidence_threshold = config.get("confidence_threshold", 0.70)
        self.min_bbox_ratio = config.get("min_bbox_ratio", 0.05)
        self.max_bbox_ratio = config.get("max_bbox_ratio", 0.15)

        logger.info(f"Loading YOLOv8 model from {self.model_path}")
        self.model = YOLO(self.model_path)

        logger.info(f"Opening camera device {self.camera_index}")
        self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            logger.error(f"Failed to open camera device {self.camera_index}")
            raise RuntimeError(f"Cannot open camera device {self.camera_index}")

        # Set camera properties for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        logger.info("PersonDetector initialized successfully")

    def detect(self) -> Optional[DetectionResult]:
        """
        Detect persons in the current camera frame.

        Returns:
            DetectionResult with detection status and zone info, or None if frame read fails.
        """
        ret, frame = self.cap.read()
        if not ret:
            logger.warning("Failed to read frame from camera")
            return None

        frame_height, frame_width = frame.shape[:2]
        frame_area = frame_height * frame_width

        # Run YOLOv8 inference
        results = self.model(frame, conf=self.confidence_threshold, verbose=False)

        # Look for person detections (class_id=0)
        person_detections = []
        for result in results:
            for box in result.boxes:
                if int(box.cls[0]) == 0:  # class 0 is "person"
                    person_detections.append((box.conf[0].item(), box.xyxy[0].cpu().numpy()))

        if not person_detections:
            logger.debug("No persons detected in frame")
            return DetectionResult(
                detected=False, confidence=0.0, bbox=None, distance_zone="none"
            )

        # Get highest confidence detection
        best_conf, best_box = max(person_detections, key=lambda x: x[0])

        # Convert box format [x1, y1, x2, y2] to [x, y, w, h]
        x1, y1, x2, y2 = best_box
        x, y, w, h = int(x1), int(y1), int(x2 - x1), int(y2 - y1)
        bbox = (x, y, w, h)

        # Determine distance zone based on bbox area
        bbox_area = w * h
        bbox_ratio = bbox_area / frame_area

        if bbox_ratio < self.min_bbox_ratio:
            distance_zone = "too_far"
            logger.debug(f"Person too far (ratio: {bbox_ratio:.4f})")
        elif bbox_ratio > self.max_bbox_ratio:
            distance_zone = "too_close"
            logger.debug(f"Person too close (ratio: {bbox_ratio:.4f})")
        else:
            distance_zone = "reception_zone"
            logger.info(f"Person in reception zone (ratio: {bbox_ratio:.4f}, conf: {best_conf:.2f})")

        return DetectionResult(
            detected=True,
            confidence=float(best_conf),
            bbox=bbox,
            distance_zone=distance_zone,
        )

    def run_detection_loop(
        self, on_person_detected: Callable[[], None], cooldown_seconds: float = 30.0
    ) -> None:
        """
        Run continuous detection loop that triggers callback when person in reception zone.

        Args:
            on_person_detected: Callback function to invoke when person detected in zone
            cooldown_seconds: Seconds to wait before allowing next trigger (prevents re-triggering)
        """
        import time

        logger.info(f"Starting detection loop with {cooldown_seconds}s cooldown")
        last_trigger_time = 0.0

        try:
            while True:
                result = self.detect()

                if (
                    result
                    and result.detected
                    and result.distance_zone == "reception_zone"
                    and time.time() - last_trigger_time > cooldown_seconds
                ):
                    logger.info(
                        f"Triggering person detected callback (conf: {result.confidence:.2f})"
                    )
                    last_trigger_time = time.time()
                    on_person_detected()

                # Small sleep to prevent CPU spinning
                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Detection loop interrupted by user")
        finally:
            self.release()

    def release(self) -> None:
        """Release camera resources."""
        if hasattr(self, "cap") and self.cap is not None:
            self.cap.release()
            logger.info("Camera released")
