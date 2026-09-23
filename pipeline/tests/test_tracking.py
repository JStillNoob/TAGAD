import unittest

from tagad_pipeline.tracking import GeometricTracker, Track, bbox_iou


class TrackingTests(unittest.TestCase):
    def test_iou_and_matching_keep_temporary_track_id(self):
        self.assertAlmostEqual(bbox_iou((0, 0, 10, 10), (5, 5, 15, 15)), 25 / 175)
        tracker = GeometricTracker()
        first = tracker.update(
            [(10, 10, 30, 30)], timestamp=0, frame_width=100, frame_height=100,
        )[0]
        second = tracker.update(
            [(12, 11, 32, 31)], timestamp=0.2, frame_width=100, frame_height=100,
        )[0]
        self.assertEqual(first.id, second.id)

    def test_confirmation_requires_time_and_valid_faces(self):
        track = Track(1, (0, 0, 10, 10), 0.0, 0.0)
        for _ in range(5):
            track.mark_valid_face()
        self.assertFalse(track.is_confirmed(1.1, 1.2, 5))
        self.assertTrue(track.is_confirmed(1.2, 1.2, 5))

    def test_smoothing_uses_recent_majority(self):
        track = Track(1, (0, 0, 10, 10), 0.0, 0.0)
        track.smooth('Engaged', 0.0, 1.0)
        track.smooth('Bored', 0.2, 1.0)
        self.assertEqual(track.smooth('Engaged', 0.4, 1.0), 'Engaged')
        self.assertEqual(track.smooth('Bored', 1.5, 1.0), 'Bored')

    def test_missing_tracks_expire(self):
        tracker = GeometricTracker(max_missing=1)
        tracker.update([(1, 1, 5, 5)], timestamp=0, frame_width=10, frame_height=10)
        tracker.update([], timestamp=1, frame_width=10, frame_height=10)
        tracker.update([], timestamp=2, frame_width=10, frame_height=10)
        self.assertEqual(tracker.tracks, {})


if __name__ == '__main__':
    unittest.main()
