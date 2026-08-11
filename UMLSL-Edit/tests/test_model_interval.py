import unittest

from umlsl_edit.model.interval import Interval


class TestInterval(unittest.TestCase):

    def test_interval_creation_valid(self):
        interval = Interval(1.0, 2.0)
        self.assertEqual(interval.start, 1.0)
        self.assertEqual(interval.end, 2.0)

    def test_interval_creation_invalid(self):
        with self.assertRaises(ValueError):
            Interval(2.0, 1.0)

    def test_length(self):
        interval = Interval(1.0, 3.0)
        self.assertEqual(interval.length(), 2.0)

    def test_subset_of_true(self):
        interval = Interval(2.0, 3.0)
        superset = [Interval(1.0, 4.0)]
        self.assertTrue(interval.subset_of(superset))

    def test_subset_of_false(self):
        interval = Interval(1.0, 4.0)
        subsets = [Interval(2.0, 3.0)]
        self.assertFalse(interval.subset_of(subsets))

    def test_intersection_overlapping(self):
        i1 = Interval(1.0, 3.0)
        i2 = Interval(2.0, 4.0)
        result = i1.intersection(i2)
        self.assertEqual(result, Interval(2.0, 3.0))

    def test_intersection_no_overlap(self):
        i1 = Interval(1.0, 2.0)
        i2 = Interval(3.0, 4.0)
        result = i1.intersection(i2)
        self.assertIsNone(result)

    def test_intersects_true(self):
        i1 = Interval(1.0, 3.0)
        i2 = Interval(2.0, 4.0)
        self.assertTrue(i1.intersects(i2))

    def test_intersects_false(self):
        i1 = Interval(1.0, 2.0)
        i2 = Interval(3.0, 4.0)
        self.assertFalse(i1.intersects(i2))

    def test_union_no_intervals(self):
        result = Interval.union([])
        self.assertEqual(result, [])

    def test_union_single_interval(self):
        intervals = [Interval(1.0, 2.0)]
        result = Interval.union(intervals)
        self.assertEqual(result, [Interval(1.0, 2.0)])

    def test_union_overlapping(self):
        intervals = [Interval(1.0, 3.0), Interval(2.0, 4.0)]
        result = Interval.union(intervals)
        self.assertEqual(result, [Interval(1.0, 4.0)])

    def test_union_non_overlapping(self):
        intervals = [Interval(1.0, 2.0), Interval(3.0, 4.0)]
        result = Interval.union(intervals)
        self.assertEqual(result, [Interval(1.0, 2.0), Interval(3.0, 4.0)])

    def test_str(self):
        interval = Interval(1.5, 2.5)
        self.assertEqual(str(interval), "[1.5, 2.5]")


if __name__ == "__main__":
    unittest.main()
