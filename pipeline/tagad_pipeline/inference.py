from dataclasses import dataclass
from math import atan2, degrees, sqrt
from pathlib import Path

import cv2
import joblib
import mediapipe as mp
import numpy as np
import pandas as pd
import torch
from ultralytics import YOLO

from .constants import (
    ATTENTION_CLASSES,
    ATTENTION_FEATURES,
    BLENDSHAPES,
    GEOMETRY_FEATURES,
    STATE_CLASSES,
    STATE_FEATURES,
    combine_state,
)
from .tracking import GeometricTracker


class PipelineConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class FrameAnalysis:
    predictions: list
    yolo_candidates: int
    valid_faces: int
    confirmed_students: int


def _model(value):
    return value['model'] if isinstance(value, dict) else value


def _feature_names(model):
    return tuple(str(item) for item in getattr(model, 'feature_names_in_', ()))


class ModelBundle:
    def __init__(self, *, yolo_path, landmarker_path, state_path, attention_path):
        paths = [Path(item) for item in (yolo_path, landmarker_path, state_path, attention_path)]
        missing = [str(path) for path in paths if not path.is_file()]
        if missing:
            raise PipelineConfigurationError(f'Missing model artifact(s): {", ".join(missing)}')

        self.device = 0 if torch.cuda.is_available() else 'cpu'
        self.head_detector = YOLO(str(paths[0]))
        state_package = joblib.load(paths[2])
        self.state_model = _model(state_package)
        self.attention_model = _model(joblib.load(paths[3]))
        self._validate_model(
            self.state_model, STATE_FEATURES, STATE_CLASSES, 'rich state classifier',
        )
        self._validate_model(
            self.attention_model, ATTENTION_FEATURES, ATTENTION_CLASSES,
            'temporal attention classifier',
        )

        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(paths[1])),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
        )
        self.face_landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)

    @staticmethod
    def _validate_model(model, expected_features, expected_classes, name):
        features = _feature_names(model)
        if features != tuple(expected_features):
            raise PipelineConfigurationError(
                f'{name} feature order does not match the frozen TAGAD contract.',
            )
        classes = {str(item) for item in getattr(model, 'classes_', ())}
        if classes != set(expected_classes):
            raise PipelineConfigurationError(
                f'{name} classes do not match the frozen TAGAD contract.',
            )

    def close(self):
        self.face_landmarker.close()


class CameraPipeline:
    def __init__(
        self,
        models,
        *,
        yolo_confidence=0.60,
        max_heads=40,
        head_padding=0.30,
        confirmation_seconds=1.2,
        confirmation_valid_faces=5,
        attention_window_seconds=10.0,
        attention_minimum_seconds=7.0,
        attention_minimum_samples=15,
        smoothing_seconds=1.0,
    ):
        self.models = models
        self.yolo_confidence = yolo_confidence
        self.max_heads = max_heads
        self.head_padding = head_padding
        self.confirmation_seconds = confirmation_seconds
        self.confirmation_valid_faces = confirmation_valid_faces
        self.attention_window_seconds = attention_window_seconds
        self.attention_minimum_seconds = attention_minimum_seconds
        self.attention_minimum_samples = attention_minimum_samples
        self.smoothing_seconds = smoothing_seconds
        self.tracker = GeometricTracker()

    def process_frame(self, frame, timestamp):
        height, width = frame.shape[:2]
        boxes = self._detect_heads(frame)
        tracks = self.tracker.update(
            boxes, timestamp=timestamp, frame_width=width, frame_height=height,
        )
        predictions = []
        valid_faces = 0
        confirmed_students = 0

        for track in tracks:
            features = self._extract_features(self._head_crop(frame, track.bbox))
            current_prediction = None
            if features is not None:
                valid_faces += 1
                track.mark_valid_face()
                raw_state, confidence = self._predict_state(features)
                track.geometry_history.append({'time': timestamp, **{
                    name: features[name] for name in GEOMETRY_FEATURES
                }})
                attention = self._predict_attention(track, timestamp)
                final_state = combine_state(raw_state, attention)
                if final_state is not None:
                    track.current_label = track.smooth(
                        final_state, timestamp, self.smoothing_seconds,
                    )
                    track.current_confidence = confidence
                    current_prediction = {
                        'label': track.current_label,
                        'confidence': confidence,
                        'track_id': track.id,
                    }

            if track.is_confirmed(
                timestamp, self.confirmation_seconds, self.confirmation_valid_faces,
            ):
                confirmed_students += 1
                predictions.append(current_prediction or {
                    'label': None,
                    'confidence': None,
                    'track_id': track.id,
                })

        return FrameAnalysis(
            predictions=predictions,
            yolo_candidates=len(boxes),
            valid_faces=valid_faces,
            confirmed_students=confirmed_students,
        )

    def _detect_heads(self, frame):
        result = self.models.head_detector.predict(
            frame,
            conf=self.yolo_confidence,
            imgsz=640,
            device=self.models.device,
            verbose=False,
        )[0]
        detected = []
        if result.boxes is not None:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                detected.append(((x1, y1, x2, y2), max(1, x2 - x1) * max(1, y2 - y1)))
        detected.sort(key=lambda item: item[1], reverse=True)
        return [item[0] for item in detected[:self.max_heads]]

    def _head_crop(self, frame, box):
        height, width = frame.shape[:2]
        x1, y1, x2, y2 = box
        pad_x = int(max(1, x2 - x1) * self.head_padding)
        pad_y = int(max(1, y2 - y1) * self.head_padding)
        return frame[
            max(0, y1 - pad_y):min(height, y2 + pad_y),
            max(0, x1 - pad_x):min(width, x2 + pad_x),
        ]

    def _extract_features(self, crop):
        if crop.size == 0:
            return None
        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(crop, cv2.COLOR_BGR2RGB),
        )
        result = self.models.face_landmarker.detect(image)
        if not result.face_landmarks or not result.facial_transformation_matrixes:
            return None
        if not result.face_blendshapes:
            return None
        try:
            pitch, yaw, roll = self._head_pose(result.facial_transformation_matrixes[0])
            horizontal_gaze, vertical_gaze = self._gaze(result.face_landmarks[0])
        except (IndexError, TypeError, ValueError, np.linalg.LinAlgError):
            return None

        blendshapes = {
            str(category.category_name): float(category.score)
            for category in result.face_blendshapes[0]
            if category.category_name is not None and category.score is not None
        }
        features = {
            'mean_pitch': pitch,
            'mean_yaw': yaw,
            'mean_roll': roll,
            'mean_Gh': horizontal_gaze,
            'mean_Gv': vertical_gaze,
        }
        features.update({f'bs_{name}': blendshapes.get(name, 0.0) for name in BLENDSHAPES})
        return features

    @staticmethod
    def _head_pose(matrix):
        rotation = np.array(matrix, dtype=np.float64)[:3, :3]
        left, _, right = np.linalg.svd(rotation)
        rotation = left @ right
        if np.linalg.det(rotation) < 0:
            left[:, -1] *= -1
            rotation = left @ right
        sy = sqrt(rotation[0, 0] ** 2 + rotation[1, 0] ** 2)
        if sy >= 1e-6:
            values = (
                atan2(rotation[2, 1], rotation[2, 2]),
                atan2(-rotation[2, 0], sy),
                atan2(rotation[1, 0], rotation[0, 0]),
            )
        else:
            values = (atan2(-rotation[1, 2], rotation[1, 1]), atan2(-rotation[2, 0], sy), 0)
        return tuple(float(degrees(value)) for value in values)

    @staticmethod
    def _center(landmarks, indices):
        return (
            float(np.mean([landmarks[index].x for index in indices])),
            float(np.mean([landmarks[index].y for index in indices])),
        )

    @staticmethod
    def _ratio(value, left, right):
        low, high = min(left, right), max(left, right)
        return 0.5 if abs(high - low) < 1e-6 else (value - low) / (high - low)

    @classmethod
    def _gaze(cls, landmarks):
        right_x, right_y = cls._center(landmarks, (468, 469, 470, 471, 472))
        left_x, left_y = cls._center(landmarks, (473, 474, 475, 476, 477))
        horizontal = (
            cls._ratio(right_x, landmarks[33].x, landmarks[133].x)
            + cls._ratio(left_x, landmarks[362].x, landmarks[263].x)
        ) / 2
        vertical = (
            cls._ratio(right_y, landmarks[159].y, landmarks[145].y)
            + cls._ratio(left_y, landmarks[386].y, landmarks[374].y)
        ) / 2
        return (
            float(np.clip((horizontal - 0.5) * 2, -1, 1)),
            float(np.clip((vertical - 0.5) * 2, -1, 1)),
        )

    def _predict_state(self, features):
        frame = pd.DataFrame(
            [[features[name] for name in STATE_FEATURES]], columns=STATE_FEATURES,
        )
        raw_state = str(self.models.state_model.predict(frame)[0])
        probabilities = self.models.state_model.predict_proba(frame)[0]
        return raw_state, float(np.max(probabilities))

    def _predict_attention(self, track, timestamp):
        history = track.geometry_history
        while history and timestamp - history[0]['time'] > self.attention_window_seconds:
            history.popleft()
        if len(history) < self.attention_minimum_samples:
            return None
        if history[-1]['time'] - history[0]['time'] < self.attention_minimum_seconds:
            return None

        values = {}
        for feature in GEOMETRY_FEATURES:
            samples = np.array([item[feature] for item in history], dtype=np.float64)
            values[feature] = float(np.mean(samples))
            values[f"std_{feature.removeprefix('mean_')}"] = float(np.std(samples))
        frame = pd.DataFrame(
            [[values[name] for name in ATTENTION_FEATURES]], columns=ATTENTION_FEATURES,
        )
        return str(self.models.attention_model.predict(frame)[0])
