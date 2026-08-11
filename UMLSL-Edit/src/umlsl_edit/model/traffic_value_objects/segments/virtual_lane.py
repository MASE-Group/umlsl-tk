from dataclasses import dataclass

from umlsl_edit.model.traffic_value_objects.segments.segment_interval import SegmentInterval


@dataclass(frozen=True)
class VirtualLane:
    """
    This is a wrapper class for a list of SegmentIntervals.
    """
    segment_intervals: list[SegmentInterval]
