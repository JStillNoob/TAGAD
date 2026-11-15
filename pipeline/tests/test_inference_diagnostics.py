import unittest
from types import SimpleNamespace

import numpy as np

from tagad_pipeline.constants import GEOMETRY_FEATURES
from tagad_pipeline.inference import CameraPipeline
from tagad_pipeline.tracking import Track


class FixedTracker:
    def __init__(self):
        self.track = Track(1, (0, 0, 10, 10), 0.0, 0.0)
        self.last_expired_count = 0

    def update(self, boxes, **_kwargs):
        return [self.track] if boxes else []


class InferenceDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = CameraPipeline(
            SimpleNamespace(), confirmation_seconds=0,
            confirmation_valid_faces=1, smoothing_seconds=0,
        )
        self.pipeline.tracker = FixedTracker()
        self.pipeline._detect_heads = lambda _frame: [(0, 0, 10, 10)]
        self.pipeline._extract_features = lambda _crop: {
            feature: 0.0 for feature in GEOMETRY_FEATURES
        }

    def test_aggregates_stage_outputs_without_changing_final_mapping(self):
        states = iter((('Engaged', 0.8), ('Bored', 0.6)))
        attention = iter(((None, None), ('HigherAttention', 0.7)))
        self.pipeline._predict_state = lambda _features: next(states)
        self.pipeline._predict_attention = lambda _track, _timestamp: next(attention)
        frame = np.zeros((20, 20, 3), dtype=np.uint8)

        first = self.pipeline.process_frame(frame, 0.0)
        second = self.pipeline.process_frame(frame, 1.0)
        diagnostics = self.pipeline.diagnostics_snapshot()

        self.assertEqual(first.predictions[0]['label'], 'Engaged')
        self.assertEqual(second.predictions[0]['label'], 'Bored')
        self.assertEqual(diagnostics['raw_state_counts']['engaged'], 1)
        self.assertEqual(diagnostics['raw_state_counts']['bored'], 1)
        self.assertEqual(diagnostics['attention_counts']['not_ready'], 1)
        self.assertEqual(diagnostics['attention_counts']['higher_attention'], 1)
        self.assertEqual(diagnostics['attention_ready_tracks'], 1)
        self.assertEqual(diagnostics['state_confidence']['average'], 0.7)
        self.assertEqual(diagnostics['attention_confidence']['average'], 0.7)

        self.pipeline.reset_diagnostics()
        reset = self.pipeline.diagnostics_snapshot()
        self.assertEqual(sum(reset['raw_state_counts'].values()), 0)
        self.assertIsNone(reset['state_confidence']['average'])

    def test_attention_confidence_is_the_model_decision_margin(self):
        model = SimpleNamespace(
            predict=lambda _frame: np.array(['LowerAttention']),
            decision_function=lambda _frame: np.array([-1.25]),
        )
        self.pipeline.models = SimpleNamespace(attention_model=model)
        self.pipeline.attention_minimum_samples = 2
        self.pipeline.attention_minimum_seconds = 1.0
        track = self.pipeline.tracker.track
        track.geometry_history.extend([
            {'time': 0.0, **{feature: 0.0 for feature in GEOMETRY_FEATURES}},
            {'time': 1.0, **{feature: 0.1 for feature in GEOMETRY_FEATURES}},
        ])

        label, margin = self.pipeline._predict_attention(track, 1.0)

        self.assertEqual(label, 'LowerAttention')
        self.assertEqual(margin, 1.25)

    def test_attention_readiness_depends_on_valid_face_sampling_rate(self):
        model = SimpleNamespace(
            predict=lambda _frame: np.array(['LowerAttention']),
            decision_function=lambda _frame: np.array([-1.0]),
        )
        for hz, expected_first_ready in ((1.0, None), (2.5, 7.2)):
            with self.subTest(valid_face_hz=hz):
                pipeline = CameraPipeline(SimpleNamespace(attention_model=model))
                track = Track(1, (0, 0, 10, 10), 0, 0)
                first_ready = None
                for index in range(int(20 * hz) + 1):
                    timestamp = index / hz
                    track.geometry_history.append({'time': timestamp, **{
                        feature: 0.0 for feature in GEOMETRY_FEATURES
                    }})
                    label, _margin = pipeline._predict_attention(track, timestamp)
                    if label is not None and first_ready is None:
                        first_ready = timestamp
                self.assertEqual(first_ready, expected_first_ready)


if __name__ == '__main__':
    unittest.main()
