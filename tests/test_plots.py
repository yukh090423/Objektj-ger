import unittest

from plotly.graph_objects import Figure

from visualization.plots import plot_motion


class PlotTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            (0, 0.0, (1, 2), (3, 4), (8, 9)),
            (1, 0.5, None, None, None),
            (2, 1.0, (5, 6), (7, 8), (4, 5)),
        ]

    def test_single_result_units_and_shared_time_axis(self):
        figure = plot_motion(self.records, "mm")

        self.assertIsInstance(figure, Figure)
        self.assertEqual(len(figure.data), 6)
        self.assertEqual(
            [figure.layout[axis].title.text for axis in ("yaxis", "yaxis2", "yaxis3")],
            ["mm", "mm/s", "mm/s²"],
        )
        self.assertEqual(figure.layout.xaxis3.title.text, "시간 (초)")
        self.assertEqual(figure.layout.xaxis.matches, "x3")
        self.assertEqual(figure.layout.xaxis2.matches, "x3")
        self.assertEqual([t.yaxis for t in figure.data], ["y", "y", "y2", "y2", "y3", "y3"])
        self.assertEqual(tuple(figure.data[0].y), (1, None, 5))

    def test_keeps_missing_values_and_their_timestamps(self):
        figure = plot_motion(self.records, "cm")
        for trace in figure.data:
            with self.subTest(axis=trace.yaxis, name=trace.name):
                self.assertEqual(tuple(trace.x), (0.0, 0.5, 1.0))
                self.assertIsNone(trace.y[1])
                self.assertIs(trace.connectgaps, False)

    def test_comparison_shows_position_once_and_distinguishes_derivatives(self):
        filtered = [
            (0, 0.0, (1, 2), None, None),
            (1, 0.5, None, None, None),
            (2, 1.0, (5, 6), (5, 7), (3, 2)),
        ]
        figure = plot_motion(self.records, "m", filtered_results=filtered)

        self.assertEqual(len(figure.data), 10)
        self.assertEqual(sum(trace.yaxis == "y" for trace in figure.data), 2)
        self.assertEqual(tuple(figure.data[0].y), (1, None, 5))
        for panel in ("y2", "y3"):
            traces = [trace for trace in figure.data if trace.yaxis == panel]
            self.assertEqual([t.line.dash for t in traces], ["solid", "solid", "dot", "dot"])
            self.assertEqual(
                [t.line.color for t in traces],
                [figure.data[0].line.color, figure.data[1].line.color] * 2,
            )
            self.assertTrue(traces[0].name.endswith("필터 끔"))
            self.assertTrue(traces[2].name.endswith("필터 켬"))
            self.assertIsNone(traces[2].y[0])
        self.assertEqual(tuple(figure.data[-2].y), (None, None, 3))
        self.assertNotEqual(figure.data[0].line.color, figure.data[1].line.color)

    def test_positions_are_visible_without_derivatives(self):
        figure = plot_motion([(0, 0.0, (2, 3), None, None)], "mm")
        self.assertEqual([t.y[0] for t in figure.data], [2, 3, None, None, None, None])
        self.assertIn("markers", figure.data[0].mode)

    def test_rejects_empty_results(self):
        with self.assertRaisesRegex(ValueError, "표시할 분석 결과가 없습니다"):
            plot_motion([], "mm")
        with self.assertRaisesRegex(ValueError, "비교 결과가 비어 있습니다"):
            plot_motion(self.records, "mm", filtered_results=[])
