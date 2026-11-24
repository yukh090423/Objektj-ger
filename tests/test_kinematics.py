import unittest

from core.kinematics import calculate_kinematics


class KinematicsTests(unittest.TestCase):
    def test_constant_velocity_and_boundaries(self):
        dt = 0.1
        records = []
        for frame in range(5):
            time = frame * dt
            records.append((frame, time, [2 + 3 * time, 7 - 4 * time]))

        results = calculate_kinematics(records)

        self.assertEqual([row[:3] for row in results], records)
        self.assertIs(results[1][2], records[1][2])
        self.assertEqual(results[0][3:], (None, None))
        self.assertEqual(results[-1][3:], (None, None))
        for _, _, _, velocity, acceleration in results[1:-1]:
            self.assertAlmostEqual(velocity[0], 3)
            self.assertAlmostEqual(velocity[1], -4)
            self.assertAlmostEqual(acceleration[0], 0)
            self.assertAlmostEqual(acceleration[1], 0)

    def test_constant_acceleration(self):
        dt = 0.25
        records = []
        for frame in range(5):
            time = frame * dt
            position = (1 + 2 * time + 3 * time**2, -time - 2 * time**2)
            records.append((frame, time, position))

        for _, time, _, velocity, acceleration in calculate_kinematics(records)[1:-1]:
            self.assertEqual(velocity, (2 + 6 * time, -1 - 4 * time))
            self.assertEqual(acceleration, (6, -4))

    def test_missing_positions_including_first_frame(self):
        records = [
            (frame, frame * 0.25, None if frame in (0, 3) else (frame, -frame))
            for frame in range(8)
        ]

        results = calculate_kinematics(records)

        self.assertEqual([row[:3] for row in results], records)
        self.assertEqual([row[3:] for row in results[:5]], [(None, None)] * 5)
        self.assertEqual(results[5][3:], ((4, -4), (0, 0)))

    def test_frame_number_gap(self):
        records = [
            (frame, frame * 0.25, (frame, -frame))
            for frame in (10, 11, 13, 14, 15)
        ]

        results = calculate_kinematics(records)

        self.assertEqual([row[:3] for row in results], records)
        self.assertEqual(results[1][3:], (None, None))
        self.assertEqual(results[2][3:], (None, None))
        self.assertEqual(results[3][3:], ((4, -4), (0, 0)))

    def test_fewer_than_three_records(self):
        records = [(0, 0.0, (0, 0)), (1, 0.5, (1, 2))]
        for count in range(3):
            with self.subTest(count=count):
                subset = records[:count]
                self.assertEqual(
                    calculate_kinematics(subset),
                    [(*record, None, None) for record in subset],
                )

    def test_invalid_time_intervals(self):
        for times in ((0.0, 0.0, 0.5), (0.0, 0.25, 0.75)):
            with self.subTest(times=times):
                records = [(frame, time, (0, 0)) for frame, time in enumerate(times)]
                with self.assertRaises(ValueError):
                    calculate_kinematics(records)
