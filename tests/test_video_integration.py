import json
from math import sqrt
from pathlib import Path
from statistics import fmean
import unittest

from core.analysis import analyze_video


def acceleration_errors(accelerations, frames, axis, expected):
    errors = [accelerations[frame][axis] - expected for frame in frames]
    return sqrt(fmean(error**2 for error in errors)), max(map(abs, errors))


class VideoIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config_path = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "objektjaeger_blue_marker_test.json"
        )
        config = json.loads(config_path.read_text(encoding="utf-8"))
        video_path = config_path.parent / config["video_file"]
        if not video_path.is_file():
            raise FileNotFoundError(f"통합 테스트 영상이 없습니다: {video_path}")

        calibration = config["calibration"]
        arguments = (
            video_path,
            *calibration["points_px"],
            calibration["reference_length"],
        )
        roi = config["tracking"]["roi_xywh"]
        cls.expected = config["expected"]
        cls.raw = analyze_video(*arguments, roi=roi, use_filter=False)
        cls.filtered = analyze_video(
            *arguments, roi=roi, use_filter=True, window_length=5, polyorder=2
        )

    def test_frame_count_timestamps_and_measured_positions(self):
        start, end = self.expected["missing_position_frames"]
        for label, results in (("필터 끔", self.raw), ("필터 켬", self.filtered)):
            with self.subTest(filter=label):
                self.assertEqual(len(results), self.expected["frame_count"])
                self.assertEqual([row[0] for row in results], list(range(len(results))))
                for frame, time, *_ in results:
                    self.assertAlmostEqual(
                        time, frame / self.expected["fps"], places=8, msg=f"프레임 {frame}"
                    )
                self.assertEqual(
                    [row[0] for row in results if row[2] is None],
                    list(range(start, end + 1)),
                )

        self.assertEqual([row[2] for row in self.raw], [row[2] for row in self.filtered])

    def test_derivative_gaps_with_and_without_filter(self):
        start, end = self.expected["missing_derivative_frames_due_to_gap"]
        last_frame = self.expected["frame_count"] - 1
        raw_missing = [0, *range(start, end + 1), last_frame]
        filtered_missing = [*range(0, 3), *range(47, 58), *range(117, 120)]

        for results, missing, count in (
            (self.raw, raw_missing, 111),
            (self.filtered, filtered_missing, 103),
        ):
            with self.subTest(valid_acceleration_frames=count):
                self.assertEqual([r[0] for r in results if r[3] is None], missing)
                self.assertEqual([r[0] for r in results if r[4] is None], missing)
                self.assertEqual(sum(r[4] is not None for r in results), count)

    def test_filter_reduces_acceleration_errors_on_shared_frames(self):
        raw = {row[0]: row[4] for row in self.raw if row[4] is not None}
        filtered = {row[0]: row[4] for row in self.filtered if row[4] is not None}
        shared = sorted(raw.keys() & filtered.keys())
        self.assertEqual(len(shared), 103)

        for axis, name in enumerate(("x", "y")):
            expected = self.expected["acceleration_mm_s2"][axis]
            before = acceleration_errors(raw, shared, axis, expected)
            after = acceleration_errors(filtered, shared, axis, expected)
            for metric, raw_error, filtered_error in zip(
                ("RMS", "최대 절대 오차"), before, after
            ):
                with self.subTest(axis=name, metric=metric):
                    self.assertLess(
                        filtered_error,
                        raw_error,
                        f"{name}축 {metric} (mm/s²), "
                        f"필터 끔 {raw_error:.6g}, 필터 켬 {filtered_error:.6g}",
                    )
