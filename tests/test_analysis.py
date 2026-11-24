import unittest
import warnings
from unittest.mock import patch

from core.analysis import analyze_video


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.load_video = self.enterContext(patch("core.analysis.load_video"))
        self.track_marker = self.enterContext(patch("core.analysis.track_marker"))
        self.video = self.load_video.return_value

    def analyze(self, **options):
        return analyze_video("sample.avi", (100, 200), (103, 204), 10, **options)

    def test_preserves_time_and_applies_scale_and_origin(self):
        self.track_marker.return_value = [
            (10, 2.50, None),
            (11, 2.75, (50, 50)),
            (12, 3.00, (51, 52)),
            (13, 3.25, (54, 54)),
            (14, 3.50, None),
            (15, 3.75, (60, 55)),
        ]

        self.assertEqual(self.analyze(), [
            (10, 2.50, None, None, None),
            (11, 2.75, [0, 0], None, None),
            (12, 3.00, [2, 4], (16, 16), (64, 0)),
            (13, 3.25, [8, 8], None, None),
            (14, 3.50, None, None, None),
            (15, 3.75, [20, 10], None, None),
        ])
        self.load_video.assert_called_once_with("sample.avi")
        self.track_marker.assert_called_once_with(self.video)
        self.video.release.assert_called_once_with()

    def test_forwards_settings_and_warning(self):
        options = {
            "roi": (20, 30, 100, 120),
            "hsv_lower": (100, 100, 80),
            "hsv_upper": (130, 255, 255),
            "min_area": 40,
        }

        def short_read(*args, **kwargs):
            warnings.warn("영상 읽기가 일찍 끝났을 수 있습니다.", RuntimeWarning)
            return [(0, 0.0, (45, 70))]

        self.track_marker.side_effect = short_read
        with self.assertWarnsRegex(RuntimeWarning, "일찍 끝났을"):
            self.assertEqual(self.analyze(**options), [(0, 0.0, [0, 0], None, None)])
        self.track_marker.assert_called_once_with(self.video, **options)
        self.video.release.assert_called_once_with()

    def test_all_frames_missing(self):
        self.track_marker.return_value = [(0, 0.0, None), (1, 0.25, None)]
        with self.assertRaisesRegex(ValueError, "모든 프레임에서 마커를 검출"):
            self.analyze()
        self.video.release.assert_called_once_with()

    def test_releases_video_when_tracking_fails(self):
        self.track_marker.side_effect = RuntimeError("추적 실패")
        with self.assertRaisesRegex(RuntimeError, "추적 실패"):
            self.analyze()
        self.video.release.assert_called_once_with()

    def test_rejects_invalid_calibration_before_loading(self):
        for distance in (0, -1, float("inf"), float("nan")):
            with self.subTest(distance=distance):
                with self.assertRaisesRegex(ValueError, "실제 길이"):
                    analyze_video("sample.avi", (0, 0), (1, 1), distance)

        with self.assertRaisesRegex(ValueError, "같은 위치"):
            analyze_video("sample.avi", (0, 0), [0, 0], 10)
        self.load_video.assert_not_called()

    def test_filter_changes_derivatives_but_preserves_measured_positions(self):
        self.track_marker.return_value = [
            (i, i * 0.25, (i + (5 if i == 2 else 0), 0))
            for i in range(9)
        ]
        default = self.analyze()
        self.assertEqual(self.analyze(use_filter=False), default)

        filtered = self.analyze(use_filter=True)
        self.assertEqual([row[:3] for row in filtered], [row[:3] for row in default])
        self.assertEqual([row[0] for row in filtered if row[4] is not None], [3, 4, 5])
        self.assertAlmostEqual(filtered[3][3][0], -24 / 7)
        self.assertAlmostEqual(filtered[3][4][0], -320 / 7)
