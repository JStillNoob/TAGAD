from collections import Counter, defaultdict, deque
from math import acos, atan2, degrees, hypot, isfinite
from statistics import mean, pstdev

from .tracking import bbox_centroid


JOINTS = {
    'left_shoulder': 5, 'right_shoulder': 6,
    'left_elbow': 7, 'right_elbow': 8,
    'left_wrist': 9, 'right_wrist': 10,
    'left_hip': 11, 'right_hip': 12,
}
FEATURES = (
    'shoulder_tilt', 'torso_lean', 'left_elbow_angle', 'right_elbow_angle',
    'left_wrist_height', 'right_wrist_height',
    'left_arm_speed', 'right_arm_speed',
)


def record_value(stats, value):
    stats['samples'] += 1
    stats['sum'] += value


def value_summary(stats):
    count = stats['samples']
    return {
        'samples': count,
        'mean': round(stats['sum'] / count, 6) if count else None,
    }


def posture_features(points):
    values = {}
    if 5 not in points or 6 not in points:
        return values, None, {}
    left, right = points[5], points[6]
    scale = hypot(right[0] - left[0], right[1] - left[1])
    if scale <= 1e-6:
        return values, None, {}
    center = ((left[0] + right[0]) / 2, (left[1] + right[1]) / 2)
    values['shoulder_tilt'] = degrees(atan2(right[1] - left[1], abs(right[0] - left[0])))
    if 11 in points and 12 in points:
        hips = ((points[11][0] + points[12][0]) / 2, (points[11][1] + points[12][1]) / 2)
        if hypot(center[0] - hips[0], center[1] - hips[1]) > 1e-6:
            values['torso_lean'] = degrees(atan2(center[0] - hips[0], hips[1] - center[1]))
    wrists = {}
    for side, shoulder, elbow, wrist in (('left', 5, 7, 9), ('right', 6, 8, 10)):
        if wrist in points and elbow in points:
            arm = (points[shoulder][0] - points[elbow][0], points[shoulder][1] - points[elbow][1])
            forearm = (points[wrist][0] - points[elbow][0], points[wrist][1] - points[elbow][1])
            denominator = hypot(*arm) * hypot(*forearm)
            if denominator > 1e-6:
                cosine = sum(a * b for a, b in zip(arm, forearm)) / denominator
                values[f'{side}_elbow_angle'] = degrees(acos(max(-1, min(1, cosine))))
                wrists[side] = (
                    (points[wrist][0] - center[0]) / scale,
                    (points[wrist][1] - center[1]) / scale,
                )
                values[f'{side}_wrist_height'] = -wrists[side][1]
    return values, scale, wrists


class PostureMetrics:
    def __init__(self, confidence=0.5):
        self.confidence = confidence
        self.counts = Counter()
        self.joints = {name: Counter() for name in JOINTS}
        self.feature_stats = {name: Counter() for name in FEATURES}
        self.stability = {name: Counter() for name in FEATURES}
        self.histories = defaultdict(dict)
        self.previous_wrists = {}

    def update(self, tracks, people, timestamp, width, height):
        self.counts['frames'] += 1
        self.counts['head_observations'] += len(tracks)
        self.counts['person_observations'] += len(people)
        matches = {}
        owners = Counter()
        for track in tracks:
            x, y = bbox_centroid(track.bbox)
            candidates = [
                index for index, person in enumerate(people)
                if person['box'][0] <= x <= person['box'][2]
                and person['box'][1] <= y <= person['box'][3]
            ]
            matches[track.id] = candidates
            owners.update(candidates)

        current_ids = {track.id for track in tracks}
        for track_id in set(self.histories) - current_ids:
            self.histories.pop(track_id, None)
            self.previous_wrists.pop(track_id, None)

        for person in people:
            for name, index in JOINTS.items():
                points = person['keypoints']
                if index < len(points) and len(points[index]) >= 3:
                    score = points[index][2]
                    if isfinite(score) and 0 <= score <= 1:
                        record_value(self.joints[name], score)
                        self.joints[name][f'confidence_bin_{min(9, int(score * 10))}'] += 1

        for track in tracks:
            candidates = matches[track.id]
            if len(candidates) != 1 or owners[candidates[0]] != 1:
                reason = 'unmatched' if not candidates else 'ambiguous'
                self.counts[reason] += 1
                self.histories.pop(track.id, None)
                self.previous_wrists.pop(track.id, None)
                continue
            self.counts['matched'] += 1
            raw_points = people[candidates[0]]['keypoints']
            valid_points = {}
            for name, index in JOINTS.items():
                point = raw_points[index] if index < len(raw_points) else ()
                if len(point) < 3:
                    self.counts['joint_missing_confidence'] += 1
                elif not all(isfinite(value) for value in point[:3]):
                    self.counts['joint_nonfinite'] += 1
                elif not 0 <= point[2] <= 1 or point[2] < self.confidence:
                    self.counts['joint_low_confidence'] += 1
                elif not (0 <= point[0] < width and 0 <= point[1] < height):
                    self.counts['joint_out_of_frame'] += 1
                else:
                    valid_points[index] = point[:2]
                    self.joints[name]['usable_observations'] += 1
            for group in ('shoulder', 'elbow', 'wrist', 'hip'):
                if JOINTS[f'left_{group}'] in valid_points and JOINTS[f'right_{group}'] in valid_points:
                    self.counts[f'both_{group}_usable'] += 1

            features, scale, wrists = posture_features(valid_points)
            if scale is None:
                self.counts['invalid_or_missing_body_scale'] += 1
            previous = self.previous_wrists.get(track.id)
            if previous and 0 < timestamp - previous[0] <= 1:
                for side, position in wrists.items():
                    if side in previous[1]:
                        old = previous[1][side]
                        features[f'{side}_arm_speed'] = hypot(
                            position[0] - old[0], position[1] - old[1],
                        ) / (timestamp - previous[0])
            self.previous_wrists[track.id] = (timestamp, wrists)

            for name in FEATURES:
                history = self.histories[track.id].setdefault(name, deque())
                if name not in features:
                    history.clear()
                    self.counts[f'{name}_missing'] += 1
                    continue
                if history and not 0 < timestamp - history[-1][0] <= 1:
                    history.clear()
                history.append((timestamp, features[name]))
                while history and timestamp - history[0][0] > 5:
                    history.popleft()
                if len(history) >= 8 and timestamp - history[0][0] >= 3:
                    values = [item[1] for item in history]
                    if name == 'torso_lean':
                        reference = values[0]
                        values = [reference + (value - reference + 180) % 360 - 180 for value in values]
                        average = (mean(values) + 180) % 360 - 180
                    else:
                        average = mean(values)
                    record_value(self.feature_stats[name], average)
                    record_value(self.stability[name], pstdev(values))
                else:
                    self.counts[f'{name}_not_ready'] += 1

    def summary(self):
        return {
            'counts': dict(self.counts),
            'joints': {
                name: {
                    **value_summary(stats),
                    'usable_observations': stats['usable_observations'],
                    'confidence_histogram': [stats[f'confidence_bin_{i}'] for i in range(10)],
                }
                for name, stats in self.joints.items()
            },
            'features': {
                name: {
                    **value_summary(self.feature_stats[name]),
                    'mean_window_std': value_summary(self.stability[name])['mean'],
                }
                for name in FEATURES
            },
            'denominator': 'Head-candidate observations, requiring separate human visibility review',
            'human_review': 'pending',
            'feasibility': 'unverified',
        }
