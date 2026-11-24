import unittest

from core.filtering import smooth_positions
from core.kinematics import calculate_kinematics


class FilteringTests(unittest.TestCase):
    def test_preserves_linear_positions(self):
        records = [(i + 10, i * 0.25, [3 * i, 10 - i]) for i in range(9)]
        result = smooth_positions(records)

        self.assertEqual([row[:2] for row in result], [row[:2] for row in records])
        self.assertEqual([row[2] for row in result[:2] + result[-2:]], [None] * 4)
        for index in range(2, 7):
            for actual, expected in zip(result[index][2], records[index][2]):
                self.assertAlmostEqual(actual, expected)

    def test_preserves_quadratic_positions_and_nonzero_acceleration(self):
        records = [
            (i, t, (2 * t**2 + t, -3 * t**2))
            for i, t in enumerate(i * 0.25 for i in range(9))
        ]
        filtered = smooth_positions(records)
        for result, original in zip(filtered[2:-2], records[2:-2]):
            for actual, expected in zip(result[2], original[2]):
                self.assertAlmostEqual(actual, expected)

        motion = calculate_kinematics(filtered)
        self.assertEqual([row[0] for row in motion if row[4] is not None], [3, 4, 5])
        for _, t, _, velocity, acceleration in motion[3:6]:
            self.assertAlmostEqual(velocity[0], 4 * t + 1)
            self.assertAlmostEqual(velocity[1], -6 * t)
            self.assertAlmostEqual(acceleration[0], 4)
            self.assertAlmostEqual(acceleration[1], -6)

    def test_splits_at_missing_positions_and_frame_gaps(self):
        records = [
            (i, i * 0.25, None if i == 5 else (i, -i))
            for i in (*range(11), *range(12, 17), *range(20, 24))
        ]
        result = smooth_positions(records)
        self.assertEqual([row[:2] for row in result], [row[:2] for row in records])
        self.assertEqual([i for i, _, position in result if position is not None], [2, 8, 14])

    def test_accepts_custom_settings_and_empty_input(self):
        records = [(0, 0.0, (1, 2)), (1, 0.25, None)]
        self.assertEqual(smooth_positions(records, window_length=1, polyorder=0), records)
        self.assertEqual(smooth_positions([]), [])

    def test_invalid_settings(self):
        for window_length, polyorder in ((0, 0), (-5, 2), (4, 2), (5, -1), (5, 5), (5.0, 2), (5, 1.5)):
            with self.subTest(window_length=window_length, polyorder=polyorder):
                with self.assertRaisesRegex(ValueError, "window_length|polyorder"):
                    smooth_positions([], window_length=window_length, polyorder=polyorder)
