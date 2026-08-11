from dataclasses import dataclass


@dataclass(frozen=True)
class Interval:
    start: float
    end: float

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError(f"End must be greater than or equal to start but got start={self.start} and end={self.end}")

    def length(self):
        return self.end - self.start

    def subset_of(self, intervals: list['Interval']):
        for interval in intervals:
            if interval.start <= self.start and self.end <= interval.end:
                return True
        return False

    def intersection(self, other: 'Interval') -> 'Interval | None':
        intersect_end = min(self.end, other.end)
        intersect_start = max(self.start, other.start)

        if intersect_start > intersect_end:
            return None

        return Interval(intersect_start, intersect_end)

    def intersects(self, other: 'Interval') -> bool:
        return self.intersection(other) is not None

    @staticmethod
    def union(interval: list['Interval']) -> list['Interval']:
        """"
        Returns the union of a list of intervals (that may overlap).
        """
        if len(interval) == 0:
            return []

        sorted_intervals = sorted(interval, key=lambda x: x.start)
        merged = []

        current_start = sorted_intervals[0].start
        current_end = sorted_intervals[0].end

        for i in range(1, len(sorted_intervals)):
            next_interval = sorted_intervals[i]

            if next_interval.start <= current_end:
                # Intervals overlap
                current_end = max(current_end, next_interval.end)
            else:
                # Intervals do not overlap, create a new one
                merged.append(Interval(current_start, current_end))

                current_start = next_interval.start
                current_end = next_interval.end

        merged.append(Interval(current_start, current_end))
        return merged

    def __str__(self):
        return f"[{self.start}, {self.end}]"
