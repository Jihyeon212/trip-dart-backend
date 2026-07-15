import unittest

from app.utils.distance import calculate_distance_km


class DistanceTest(unittest.TestCase):
    def test_same_coordinate_is_zero(self) -> None:
        self.assertEqual(calculate_distance_km(35.15, 126.91, 35.15, 126.91), 0)

    def test_known_coordinates_have_reasonable_distance(self) -> None:
        distance = calculate_distance_km(35.1595, 126.8526, 37.5665, 126.9780)
        self.assertGreater(distance, 250)
        self.assertLess(distance, 300)

    def test_distance_is_non_negative(self) -> None:
        self.assertGreaterEqual(calculate_distance_km(35.1, 126.8, 35.2, 126.9), 0)

    def test_near_coordinate_is_closer_than_far_coordinate(self) -> None:
        near = calculate_distance_km(35.1, 126.9, 35.11, 126.91)
        far = calculate_distance_km(35.1, 126.9, 36.0, 127.5)
        self.assertLess(near, far)


if __name__ == "__main__":
    unittest.main()
