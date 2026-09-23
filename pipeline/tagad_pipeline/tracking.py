from collections import Counter, deque
from dataclasses import dataclass, field
from math import hypot


def bbox_centroid(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def bbox_iou(left, right):
    lx1, ly1, lx2, ly2 = left
    rx1, ry1, rx2, ry2 = right
    width = max(0, min(lx2, rx2) - max(lx1, rx1))
    height = max(0, min(ly2, ry2) - max(ly1, ry1))
    intersection = width * height
    left_area = max(1, lx2 - lx1) * max(1, ly2 - ly1)
    right_area = max(1, rx2 - rx1) * max(1, ry2 - ry1)
    union = left_area + right_area - intersection
    return intersection / union if union else 0.0


@dataclass
class Track:
    id: int
    bbox: tuple
    first_seen: float
    last_seen: float
    missing: int = 0
    valid_face_observations: int = 0
    geometry_history: deque = field(default_factory=deque)
    state_history: deque = field(default_factory=deque)
    current_label: str | None = None
    current_confidence: float | None = None

    def mark_valid_face(self):
        self.valid_face_observations += 1

    def is_confirmed(self, now, minimum_seconds, minimum_valid_faces):
        return (
            now - self.first_seen >= minimum_seconds
            and self.valid_face_observations >= minimum_valid_faces
        )

    def smooth(self, label, now, window_seconds):
        self.state_history.append((now, label))
        while self.state_history and now - self.state_history[0][0] > window_seconds:
            self.state_history.popleft()
        counts = Counter(item[1] for item in self.state_history)
        first_seen = {item[1]: index for index, item in enumerate(self.state_history)}
        return min(counts, key=lambda value: (-counts[value], first_seen[value]))


class GeometricTracker:
    def __init__(self, *, max_missing=8, max_distance_ratio=0.10, minimum_iou=0.05):
        self.max_missing = max_missing
        self.max_distance_ratio = max_distance_ratio
        self.minimum_iou = minimum_iou
        self.tracks = {}
        self.next_track_id = 1

    def update(self, boxes, *, timestamp, frame_width, frame_height):
        track_ids = list(self.tracks)
        frame_diagonal = hypot(frame_width, frame_height) or 1
        candidates = []
        for track_id in track_ids:
            track = self.tracks[track_id]
            track_center = bbox_centroid(track.bbox)
            for detection_index, box in enumerate(boxes):
                detection_center = bbox_centroid(box)
                distance_ratio = hypot(
                    track_center[0] - detection_center[0],
                    track_center[1] - detection_center[1],
                ) / frame_diagonal
                overlap = bbox_iou(track.bbox, box)
                if overlap >= self.minimum_iou or distance_ratio <= self.max_distance_ratio:
                    candidates.append((distance_ratio - 0.20 * overlap, track_id, detection_index))

        matches = {}
        used_tracks = set()
        used_detections = set()
        for _, track_id, detection_index in sorted(candidates):
            if track_id in used_tracks or detection_index in used_detections:
                continue
            used_tracks.add(track_id)
            used_detections.add(detection_index)
            matches[detection_index] = track_id

        for track_id in set(track_ids) - used_tracks:
            self.tracks[track_id].missing += 1
        for track_id in [
            item.id for item in self.tracks.values() if item.missing > self.max_missing
        ]:
            del self.tracks[track_id]

        for detection_index, box in enumerate(boxes):
            track_id = matches.get(detection_index)
            if track_id is None:
                track_id = self.next_track_id
                self.next_track_id += 1
                self.tracks[track_id] = Track(track_id, box, timestamp, timestamp)
                matches[detection_index] = track_id
            track = self.tracks[track_id]
            track.bbox = box
            track.last_seen = timestamp
            track.missing = 0

        return [self.tracks[matches[index]] for index in range(len(boxes))]
