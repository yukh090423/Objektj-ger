import csv
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch

from core.analysis import analyze_video
from export.csv_exporter import export_motion_csv
from frontend.app import FILTER_MODES, run_analysis
from visualization.plots import plot_motion, plot_motion_summary


class MotionResultTests(unittest.TestCase):
    def analyze(self, observations, compare=False):
        source = Path("sample.mp4")
        points = ((0, 0), (1, 0))
        with (
            patch("core.analysis.load_video"),
            patch("core.analysis.track_marker", return_value=observations),
        ):
            app, filtered, _ = run_analysis(
                source, points, 1, FILTER_MODES[2 if compare else 0], {}
            )
            video_axes = analyze_video(source, *points, 1)
        return app, filtered, video_axes

    def test_upward_motion_and_shared_graph_csv_coordinates(self):
        records = [(i, i * 0.5, (i, 10 - 2 * i)) for i in range(5)]
        results, _, video_axes = self.analyze(records)
        self.assertEqual([row[2][1] for row in results], [0, 2, 4, 6, 8])
        self.assertEqual(results[2][3][1], 4)
        self.assertEqual(video_axes[2][3][1], -4)

        graph = plot_motion(results, "mm")
        csv_rows = list(csv.DictReader(StringIO(export_motion_csv(results, "mm"))))
        self.assertEqual(graph.data[1].y[2], float(csv_rows[2]["y_mm"]))
        self.assertEqual(graph.data[3].y[2], float(csv_rows[2]["vy_mm_per_s"]))

    def test_downward_acceleration_and_magnitude_invariance(self):
        records = [
            (i, i * 0.5, None if i == 8 else (i, i**2)) for i in range(10)
        ]
        results, filtered, video_axes = self.analyze(records, compare=True)
        self.assertEqual(results[3][4][1], -8)
        self.assertAlmostEqual(filtered[3][4][1], -8)
        for series in (results, filtered):
            graph = plot_motion(series, "mm")
            csv_rows = list(csv.DictReader(StringIO(export_motion_csv(series, "mm"))))
            self.assertEqual(graph.data[5].y[3], float(csv_rows[3]["ay_mm_per_s2"]))
            self.assertEqual(csv_rows[8]["y_mm"], "")
            self.assertEqual(csv_rows[8]["ay_mm_per_s2"], "")

        summary = plot_motion_summary(results, "mm", filtered_results=filtered)
        original = plot_motion_summary(video_axes, "mm")
        self.assertEqual(len(summary.data), 5)
        self.assertEqual(summary.layout.yaxis.scaleanchor, "x")
        self.assertEqual(summary.layout.yaxis.scaleratio, 1)
        self.assertEqual(summary.layout.yaxis2.title.text, "mm/s")
        self.assertEqual(summary.layout.yaxis3.title.text, "mm/s²")
        self.assertEqual(summary.data[0].customdata[3], 1.5)
        self.assertIn("%{customdata", summary.data[0].hovertemplate)
        self.assertTrue(all(trace.connectgaps is False for trace in summary.data))
        self.assertTrue(all(trace.y[8] is None for trace in summary.data))
        self.assertIsNone(summary.data[0].x[8])
        self.assertEqual(summary.data[1].y, original.data[1].y)
        self.assertEqual(summary.data[3].y, original.data[2].y)
        self.assertEqual(summary.data[2].line.dash, "dot")
        self.assertEqual(summary.data[4].line.dash, "dot")
