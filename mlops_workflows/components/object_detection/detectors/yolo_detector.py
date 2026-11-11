"""Detect objects using YOLO models exported to ONNX."""

import ast
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from pydantic import BaseModel, Field

from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.components.object_detection.object_detector import ObjectDetector


class YoloDetectorConfig(BaseModel):
    """Define the settings used by the YOLO detector."""

    model_path: str = Field(min_length=1)
    class_names: list[str] | None = Field(default=None, min_length=1)
    confidence_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class YoloDetector(ObjectDetector):
    """Run object detection using a YOLO ONNX model."""

    def __init__(self, config: YoloDetectorConfig):
        self.config = config

        model_path = Path(config.model_path)

        if not model_path.is_file():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        options = ort.SessionOptions()
        options.intra_op_num_threads = 2

        self.session = ort.InferenceSession(
            str(model_path),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )

        input_info = self.session.get_inputs()[0]
        self.input_name = input_info.name

        shape = input_info.shape

        if len(shape) != 4 or shape[0] != 1 or shape[1] != 3:
            raise ValueError("Expected a YOLO model with input shape [1, 3, H, W].")

        height, width = shape[2], shape[3]

        if not all(isinstance(value, int) and value > 0 for value in (height, width)):
            raise ValueError("The model must have fixed input dimensions.")

        self.input_height = height
        self.input_width = width

        if config.class_names is not None:
            names = config.class_names
        else:
            metadata = self.session.get_modelmeta().custom_metadata_map
            raw_names = metadata.get("names")

            if raw_names is None:
                raise ValueError(
                    "Model metadata does not contain class names. "
                    "Provide class_names in the configuration."
                )

            try:
                parsed_names = ast.literal_eval(raw_names)
            except (ValueError, SyntaxError) as error:
                raise ValueError("Invalid class names metadata.") from error

            if isinstance(parsed_names, dict):
                if set(parsed_names) != set(range(len(parsed_names))):
                    raise ValueError("Class IDs must be consecutive from zero.")

                names = [parsed_names[i] for i in range(len(parsed_names))]

            elif isinstance(parsed_names, (list, tuple)):
                names = list(parsed_names)

            else:
                raise ValueError("Invalid class names metadata.")

        if not names or any(
            not isinstance(name, str) or not name.strip() for name in names
        ):
            raise ValueError("Class names must be nonempty strings.")

        self.class_names = tuple(names)

    def _preprocess(
        self,
        image: np.ndarray,
    ) -> tuple[np.ndarray, float, int, int]:
        """Prepare a BGR image for inference and return resize information."""
        if not isinstance(image, np.ndarray):
            raise TypeError("The image must be a NumPy array.")

        if (
            image.size == 0
            or image.ndim != 3
            or image.shape[2] != 3
            or image.dtype != np.uint8
        ):
            raise ValueError("The image must be a nonempty uint8 BGR image.")

        height, width = image.shape[:2]

        scale = min(
            self.input_height / height,
            self.input_width / width,
        )

        resized_width = max(1, round(width * scale))
        resized_height = max(1, round(height * scale))

        resized = cv2.resize(image, (resized_width, resized_height))

        canvas = np.full(
            (self.input_height, self.input_width, 3),
            114,
            dtype=np.uint8,
        )

        padding_x = (self.input_width - resized_width) // 2
        padding_y = (self.input_height - resized_height) // 2

        canvas[
            padding_y : padding_y + resized_height,
            padding_x : padding_x + resized_width,
        ] = resized

        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        normalized = rgb.astype(np.float32) / 255.0
        channels_first = normalized.transpose(2, 0, 1)
        batch = channels_first[np.newaxis, ...]

        return np.ascontiguousarray(batch), scale, padding_x, padding_y

    def detect(self, image: np.ndarray) -> list[Detection]:
        """Run inference and return filtered object detections."""
        batch, scale, padding_x, padding_y = self._preprocess(image)

        output = self.session.run(
            None,
            {self.input_name: batch},
        )[0]

        expected_channels = 4 + len(self.class_names)

        if (
            not isinstance(output, np.ndarray)
            or output.ndim != 3
            or output.shape[0] != 1
            or output.shape[1] != expected_channels
        ):
            raise ValueError(
                "Unsupported YOLO output shape. "
                f"Expected [1, {expected_channels}, N], "
                f"got {getattr(output, 'shape', None)}."
            )

        if output.shape[2] == 0:
            return []

        predictions = output[0].T

        # Discard predictions containing NaN or infinite values.
        predictions = predictions[np.isfinite(predictions).all(axis=1)]

        if len(predictions) == 0:
            return []

        boxes = predictions[:, :4]
        scores = predictions[:, 4:]

        class_ids = scores.argmax(axis=1)
        confidences = scores.max(axis=1)

        keep = confidences > self.config.confidence_threshold
        boxes = boxes[keep]
        class_ids = class_ids[keep]
        confidences = confidences[keep]

        if len(boxes) == 0:
            return []

        corners = np.empty_like(boxes)
        corners[:, 0] = (boxes[:, 0] - boxes[:, 2] / 2 - padding_x) / scale
        corners[:, 1] = (boxes[:, 1] - boxes[:, 3] / 2 - padding_y) / scale
        corners[:, 2] = (boxes[:, 0] + boxes[:, 2] / 2 - padding_x) / scale
        corners[:, 3] = (boxes[:, 1] + boxes[:, 3] / 2 - padding_y) / scale

        height, width = image.shape[:2]

        corners[:, [0, 2]] = np.clip(corners[:, [0, 2]], 0, width)
        corners[:, [1, 3]] = np.clip(corners[:, [1, 3]], 0, height)

        valid = (corners[:, 2] > corners[:, 0]) & (corners[:, 3] > corners[:, 1])

        corners = corners[valid]
        class_ids = class_ids[valid]
        confidences = confidences[valid]

        detections = []
        selected_indices = []

        for class_id in np.unique(class_ids):
            indices = np.where(class_ids == class_id)[0]

            selected = self._nms(
                corners[indices],
                confidences[indices],
            )

            selected_indices.extend(indices[selected])

        selected_indices.sort(
            key=lambda index: confidences[index],
            reverse=True,
        )

        for index in selected_indices:
            detection = Detection(
                cls=self.class_names[int(class_ids[index])],
                conf=float(confidences[index]),
                box=corners[index].tolist(),
            )
            detections.append(detection)

        return detections

    def _nms(
        self,
        boxes: np.ndarray,
        scores: np.ndarray,
    ) -> list[int]:
        """Select boxes by confidence and suppress excessive overlap."""
        x_min = boxes[:, 0]
        y_min = boxes[:, 1]
        x_max = boxes[:, 2]
        y_max = boxes[:, 3]

        widths = np.maximum(x_max - x_min, 0)
        heights = np.maximum(y_max - y_min, 0)
        areas = widths * heights

        order = scores.argsort()[::-1]
        selected = []

        while order.size > 0:
            current = int(order[0])
            selected.append(current)

            remaining = order[1:]

            intersection_x_min = np.maximum(x_min[current], x_min[remaining])
            intersection_y_min = np.maximum(y_min[current], y_min[remaining])
            intersection_x_max = np.minimum(x_max[current], x_max[remaining])
            intersection_y_max = np.minimum(y_max[current], y_max[remaining])

            intersection_width = np.maximum(
                intersection_x_max - intersection_x_min,
                0,
            )
            intersection_height = np.maximum(
                intersection_y_max - intersection_y_min,
                0,
            )
            intersection_area = intersection_width * intersection_height

            union_area = areas[current] + areas[remaining] - intersection_area
            iou = intersection_area / (union_area + 1e-9)

            order = remaining[iou <= self.config.iou_threshold]

        return selected
