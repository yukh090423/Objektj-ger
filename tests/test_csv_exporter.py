import csv
from io import StringIO
import json
from pathlib import Path
import unittest

from core.analysis import analyze_video
from export.csv_exporter import export_motion_csv


class CsvExporterTests(unittest.TestCase):
    def test_column_order_values_and_input_order(self):
        records = [
            (7, 0.125, [1.25, -2.5], (3, -4), (5, -6)),
            (2, 0.05, [11, 12], (13, 14), (15, 16)),
        ]
        rows = list(csv.reader(StringIO(export_motion_csv(records, "mm"))))
        self.assertEqual(rows, [
            ["frame", "time_s", "x_mm", "y_mm", "vx_mm_per_s", "vy_mm_per_s",
             "ax_mm_per_s2", "ay_mm_per_s2"],
            ["7", "0.125", "1.25", "-2.5", "3", "-4", "5", "-6"],
            ["2", "0.05", "11", "12", "13", "14", "15", "16"],
        ])

    def test_preserves_zeros_and_only_blanks_missing_vectors(self):
        records = [
            (0, 0, [0, 0], None, None),
            (1, 0.5, None, (0, 0), (0, 0)),
            (2, 1, [3, 0], (0, 2), None),
            (3, 1.5, [0, 1], None, (0, 2)),
        ]
        rows = list(csv.reader(StringIO(export_motion_csv(records, "cm"))))
        self.assertEqual(rows[0][2:], [
            "x_cm", "y_cm", "vx_cm_per_s", "vy_cm_per_s", "ax_cm_per_s2", "ay_cm_per_s2",
        ])
        self.assertEqual(rows[1:], [
            ["0", "0", "0", "0", "", "", "", ""],
            ["1", "0.5", "", "", "0", "0", "0", "0"],
            ["2", "1", "3", "0", "0", "2", "", ""],
            ["3", "1.5", "0", "1", "", "", "0", "2"],
        ])

    def test_empty_input_returns_only_header(self):
        rows = list(csv.reader(StringIO(export_motion_csv([], "m"))))
        self.assertEqual(rows, [[
            "frame", "time_s", "x_m", "y_m", "vx_m_per_s", "vy_m_per_s",
            "ax_m_per_s2", "ay_m_per_s2",
        ]])

    def test_exports_filtered_synthetic_video(self):
        config_path = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "objektjaeger_blue_marker_test.json"
        )
        config = json.loads(config_path.read_text(encoding="utf-8"))
        calibration = config["calibration"]
        results = analyze_video(
            config_path.parent / config["video_file"],
            *calibration["points_px"],
            calibration["reference_length"],
            roi=config["tracking"]["roi_xywh"],
            use_filter=True,
            window_length=5,
            polyorder=2,
        )
        csv_text = export_motion_csv(results, calibration["length_unit"])
        _, *rows = csv.reader(StringIO(csv_text))
        expected = config["expected"]
        self.assertEqual(len(rows), expected["frame_count"])
        self.assertEqual([int(row[0]) for row in rows], list(range(len(rows))))

        start, end = expected["missing_position_frames"]
        missing = [int(row[0]) for row in rows if row[2:4] == ["", ""]]
        self.assertEqual(missing, list(range(start, end + 1)))

        boundary = rows[start - 1]
        self.assertEqual([float(value) for value in boundary[2:4]], results[start - 1][2])
        self.assertEqual(boundary[4:], ["", "", "", ""])
