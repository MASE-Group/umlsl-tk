"""Unit tests for `simulation.reservations` -- who has claimed which space.

Four collaborators, tested separately and then through the facade:

* `CarReservationStore`      -- one car's ordered list of held segments.
* `SegmentOccupancyTracker`  -- the same relation read the other way round.
* `CrossingSegmentState`     -- when each car expects to be out of a crossing.
* `IntersectionState`        -- the right-of-way queue and its lease.
* `ReservationManagement`    -- the facade the rest of the simulator talks to.
"""

import unittest

from umlsl_sim.config.simulation_constants import (
    PRIORITY_REORDER_TICKS,
    PRIORITY_WITHDRAW_TICKS,
)
from umlsl_sim.simulation.reservations.car_reservation_store import CarReservationStore
from umlsl_sim.simulation.reservations.crossing_segment_state import CrossingSegmentState
from umlsl_sim.simulation.reservations.intersection_state import ClaimUpdate, IntersectionState
from umlsl_sim.simulation.reservations.lane_change_claim import LaneChangeClaim
from umlsl_sim.simulation.reservations.reservation_management import ReservationManagement
from umlsl_sim.simulation.reservations.segment_occupancy_tracker import SegmentOccupancyTracker
from umlsl_sim.simulation.road_network.road_network import Direction, SegmentInfo

from tests.helpers import single_crossing_world


def _info(segment, begin=0, end=10, direction=Direction.RIGHT):
    return SegmentInfo(segment, begin, end, direction)


class TestCarReservationStore(unittest.TestCase):

    def setUp(self):
        self.world = single_crossing_world()
        self.a = self.world.lane_segment("h1", "right")
        self.b = self.world.crossing_segments("h1", "right")[0]
        self.store = CarReservationStore()

    def test_reservations_are_kept_in_insertion_order(self):
        self.store.add_reservation("c", _info(self.a))
        self.store.add_reservation("c", _info(self.b))
        self.assertEqual([si.segment for si in self.store.get_reserved_segments("c")],
                         [self.a, self.b])

    def test_the_first_reservation_creates_the_car_entry(self):
        self.store.add_reservation("c", _info(self.a))
        self.assertEqual(len(self.store.get_reserved_segments("c")), 1)

    def test_get_reserved_segment_indexes_positionally(self):
        self.store.add_reservation("c", _info(self.a))
        self.store.add_reservation("c", _info(self.b))
        self.assertIs(self.store.get_reserved_segment("c", 0).segment, self.a)
        self.assertIs(self.store.get_reserved_segment("c", -1).segment, self.b)

    def test_pop_removes_and_returns_the_reservation(self):
        self.store.add_reservation("c", _info(self.a))
        self.store.add_reservation("c", _info(self.b))
        popped = self.store.pop_reservation("c", 0)
        self.assertIs(popped.segment, self.a)
        self.assertEqual([si.segment for si in self.store.get_reserved_segments("c")],
                         [self.b])

    def test_update_helpers_write_through_to_the_stored_info(self):
        self.store.add_reservation("c", _info(self.a))
        self.store.update_begin("c", 0, 5)
        self.store.update_end("c", 0, 55)
        self.store.update_turn("c", 0, True)
        stored = self.store.get_reserved_segment("c", 0)
        self.assertEqual((stored.begin, stored.end, stored.turn), (5, 55, True))

    def test_get_reserved_segments_returns_a_copy(self):
        self.store.add_reservation("c", _info(self.a))
        snapshot = self.store.get_reserved_segments("c")
        snapshot.clear()
        self.assertEqual(len(self.store.get_reserved_segments("c")), 1)

    def test_get_reserved_segments_view_returns_the_live_list(self):
        self.store.add_reservation("c", _info(self.a))
        view = self.store.get_reserved_segments_view("c")
        self.store.add_reservation("c", _info(self.b))
        self.assertEqual(len(view), 2, "the view must observe later appends")

    def test_the_copy_still_shares_the_segment_info_objects(self):
        self.store.add_reservation("c", _info(self.a))
        self.store.get_reserved_segments("c")[0].begin = 99
        self.assertEqual(self.store.get_reserved_segment("c", 0).begin, 99)

    def test_an_unknown_car_has_no_entry(self):
        with self.assertRaises(KeyError):
            self.store.get_reserved_segments("nobody")

    def test_reset_clears_every_car(self):
        self.store.add_reservation("c", _info(self.a))
        self.store.reset()
        with self.assertRaises(KeyError):
            self.store.get_reserved_segments("c")


class TestSegmentOccupancyTracker(unittest.TestCase):

    def setUp(self):
        self.world = single_crossing_world()
        self.segment = self.world.lane_segment("h1", "right")
        self.other = self.world.lane_segment("v1", "right")
        self.tracker = SegmentOccupancyTracker()

    def test_cars_are_listed_in_the_order_they_claimed_the_segment(self):
        self.tracker.add_segment_occupancy(self.segment, "first")
        self.tracker.add_segment_occupancy(self.segment, "second")
        self.assertEqual(self.tracker.get_cars_on_segment(self.segment),
                         ["first", "second"])

    def test_an_unoccupied_segment_reads_as_empty(self):
        self.assertEqual(self.tracker.get_cars_on_segment(self.segment), [])

    def test_reading_an_unoccupied_segment_does_not_record_it(self):
        """FIXED (FINDINGS #2): the read used to insert an empty list.

        The safety checks query every segment of a projected route, most of
        them empty, so a read that wrote turned an occupancy table into a table
        of every segment ever *considered*.
        """
        internal = self.tracker._SegmentOccupancyTracker__segment_occupancy_dict
        self.tracker.get_cars_on_segment(self.segment)
        self.tracker.get_cars_on_segment(self.other)
        self.assertEqual(internal, {})

    def test_the_returned_list_is_a_copy(self):
        self.tracker.add_segment_occupancy(self.segment, "a")
        self.tracker.get_cars_on_segment(self.segment).append("ghost")
        self.assertEqual(self.tracker.get_cars_on_segment(self.segment), ["a"])

    def test_remove_takes_one_occupant_off(self):
        self.tracker.add_segment_occupancy(self.segment, "a")
        self.tracker.add_segment_occupancy(self.segment, "b")
        self.tracker.remove_segment_occupancy(self.segment, "a")
        self.assertEqual(self.tracker.get_cars_on_segment(self.segment), ["b"])

    def test_removing_one_of_two_identical_claims_leaves_the_other(self):
        # A car straddling back onto a segment can hold it twice.
        self.tracker.add_segment_occupancy(self.segment, "a")
        self.tracker.add_segment_occupancy(self.segment, "a")
        self.tracker.remove_segment_occupancy(self.segment, "a")
        self.assertEqual(self.tracker.get_cars_on_segment(self.segment), ["a"])

    def test_removing_an_absent_occupant_raises(self):
        self.tracker.add_segment_occupancy(self.segment, "a")
        with self.assertRaises(ValueError):
            self.tracker.remove_segment_occupancy(self.segment, "b")

    def test_segments_are_tracked_independently(self):
        self.tracker.add_segment_occupancy(self.segment, "a")
        self.assertEqual(self.tracker.get_cars_on_segment(self.other), [])

    def test_reset_empties_every_segment(self):
        self.tracker.add_segment_occupancy(self.segment, "a")
        self.tracker.reset()
        self.assertEqual(self.tracker.get_cars_on_segment(self.segment), [])


class TestCrossingSegmentState(unittest.TestCase):

    def setUp(self):
        self.state = CrossingSegmentState()

    def test_an_unknown_car_has_no_departure_time(self):
        self.assertIsNone(self.state.get_time_to_leave("nobody"))

    def test_a_recorded_time_reads_back(self):
        self.state.add_time_to_leave("a", 17)
        self.assertEqual(self.state.get_time_to_leave("a"), 17)

    def test_a_later_write_replaces_the_earlier_one(self):
        self.state.add_time_to_leave("a", 17)
        self.state.add_time_to_leave("a", 23)
        self.assertEqual(self.state.get_time_to_leave("a"), 23)

    def test_pop_returns_and_forgets(self):
        self.state.add_time_to_leave("a", 17)
        self.assertEqual(self.state.pop_time_to_leave("a"), 17)
        self.assertIsNone(self.state.get_time_to_leave("a"))

    def test_popping_an_unknown_car_is_not_an_error(self):
        self.assertIsNone(self.state.pop_time_to_leave("nobody"))

    def test_cars_are_tracked_independently(self):
        self.state.add_time_to_leave("a", 1)
        self.state.add_time_to_leave("b", 2)
        self.assertEqual(self.state.get_time_to_leave("a"), 1)
        self.assertEqual(self.state.get_time_to_leave("b"), 2)

    def test_reset_forgets_everyone(self):
        self.state.add_time_to_leave("a", 1)
        self.state.reset()
        self.assertIsNone(self.state.get_time_to_leave("a"))


class TestIntersectionStateClaims(unittest.TestCase):

    def setUp(self):
        self.state = IntersectionState()

    def test_a_car_with_no_claim_has_no_priority(self):
        self.assertIsNone(self.state.get_car_priority("a"))

    def test_a_claim_takes_the_tick_it_was_made_on_as_its_priority(self):
        self.state.add_car_priority("a", 7)
        self.assertEqual(self.state.get_car_priority("a"), 7)

    def test_claiming_again_keeps_the_place_already_earned(self):
        self.state.add_car_priority("a", 7)
        self.state.add_car_priority("a", 99)
        self.assertEqual(self.state.get_car_priority("a"), 7)

    def test_pop_returns_the_place_and_removes_the_claim(self):
        self.state.add_car_priority("a", 7)
        self.assertEqual(self.state.pop_car_priority("a"), 7)
        self.assertIsNone(self.state.get_car_priority("a"))

    def test_popping_a_car_that_never_claimed_is_not_an_error(self):
        self.assertIsNone(self.state.pop_car_priority("nobody"))

    def test_get_priority_items_lists_every_outstanding_claim(self):
        self.state.add_car_priority("a", 1)
        self.state.add_car_priority("b", 2)
        self.assertEqual(sorted(self.state.get_priority_items()), [("a", 1), ("b", 2)])

    def test_reset_clears_the_queue(self):
        self.state.add_car_priority("a", 1)
        self.state.reset()
        self.assertEqual(self.state.get_priority_items(), [])


class TestIntersectionStateOrdering(unittest.TestCase):

    def setUp(self):
        self.state = IntersectionState()

    def test_the_only_claimant_is_never_outranked(self):
        self.state.add_car_priority("a", 5)
        self.assertFalse(self.state.outranked("a"))

    def test_a_later_claim_is_outranked_by_an_earlier_one(self):
        self.state.add_car_priority("early", 1)
        self.state.add_car_priority("late", 2)
        self.assertTrue(self.state.outranked("late"))
        self.assertFalse(self.state.outranked("early"))

    def test_claims_made_on_the_same_tick_do_not_block_each_other(self):
        self.state.add_car_priority("a", 3)
        self.state.add_car_priority("b", 3)
        self.assertFalse(self.state.outranked("a"))
        self.assertFalse(self.state.outranked("b"))

    def test_a_car_holding_no_claim_is_never_outranked(self):
        self.state.add_car_priority("someone", 1)
        self.assertFalse(self.state.outranked("stranger"))

    def test_withdrawing_the_leader_releases_everyone_behind_it(self):
        self.state.add_car_priority("early", 1)
        self.state.add_car_priority("late", 2)
        self.state.pop_car_priority("early")
        self.assertFalse(self.state.outranked("late"))


class TestIntersectionStateLease(unittest.TestCase):
    """The lease: a claim survives only while its holder keeps moving."""

    def setUp(self):
        self.state = IntersectionState()
        self.state.add_car_priority("a", 0)

    def test_renewing_a_claim_nobody_holds_reports_it_gone(self):
        self.assertIs(self.state.renew_car_priority("stranger", 1, made_progress=True),
                      ClaimUpdate.WITHDRAWN)

    def test_progress_holds_the_claim(self):
        for tick in range(1, PRIORITY_WITHDRAW_TICKS + 5):
            self.assertIs(self.state.renew_car_priority("a", tick, made_progress=True),
                          ClaimUpdate.HELD)
        self.assertEqual(self.state.get_car_priority("a"), 0)

    def test_a_short_stall_holds_the_claim(self):
        for tick in range(1, PRIORITY_REORDER_TICKS):
            self.assertIs(self.state.renew_car_priority("a", tick, made_progress=False),
                          ClaimUpdate.HELD)

    def test_a_stall_of_reorder_length_moves_the_claim_to_the_back(self):
        result = None
        for tick in range(1, PRIORITY_REORDER_TICKS + 1):
            result = self.state.renew_car_priority("a", tick, made_progress=False)
        self.assertIs(result, ClaimUpdate.REORDERED)
        self.assertEqual(self.state.get_car_priority("a"), PRIORITY_REORDER_TICKS)

    def test_a_claim_is_only_reordered_once_per_stall(self):
        results = [self.state.renew_car_priority("a", tick, made_progress=False)
                   for tick in range(1, PRIORITY_WITHDRAW_TICKS)]
        self.assertEqual(results.count(ClaimUpdate.REORDERED), 1)

    def test_a_long_enough_stall_withdraws_the_claim(self):
        result = None
        for tick in range(1, PRIORITY_WITHDRAW_TICKS + 1):
            result = self.state.renew_car_priority("a", tick, made_progress=False)
        self.assertIs(result, ClaimUpdate.WITHDRAWN)
        self.assertIsNone(self.state.get_car_priority("a"))

    def test_progress_resets_the_stall_counter(self):
        for tick in range(1, PRIORITY_WITHDRAW_TICKS):
            self.state.renew_car_priority("a", tick, made_progress=False)
        self.state.renew_car_priority("a", PRIORITY_WITHDRAW_TICKS, made_progress=True)
        self.assertIs(
            self.state.renew_car_priority("a", PRIORITY_WITHDRAW_TICKS + 1, made_progress=False),
            ClaimUpdate.HELD,
        )
        self.assertIsNotNone(self.state.get_car_priority("a"))

    def test_progress_re_arms_the_reorder_so_a_second_stall_demotes_again(self):
        for tick in range(1, PRIORITY_REORDER_TICKS + 1):
            self.state.renew_car_priority("a", tick, made_progress=False)
        self.state.renew_car_priority("a", 100, made_progress=True)
        results = [self.state.renew_car_priority("a", 100 + tick, made_progress=False)
                   for tick in range(1, PRIORITY_REORDER_TICKS + 1)]
        self.assertIs(results[-1], ClaimUpdate.REORDERED)

    def test_a_stalled_leader_stops_holding_the_queue_closed(self):
        """The property the lease exists for: a cyclic wait always breaks."""
        self.state.add_car_priority("behind", 1)
        self.assertTrue(self.state.outranked("behind"))
        for tick in range(1, PRIORITY_WITHDRAW_TICKS + 1):
            self.state.renew_car_priority("a", tick, made_progress=False)
        self.assertFalse(self.state.outranked("behind"))

    def test_reordering_alone_already_releases_a_later_claimant(self):
        self.state.add_car_priority("behind", 1)
        for tick in range(1, PRIORITY_REORDER_TICKS + 1):
            self.state.renew_car_priority("a", tick, made_progress=False)
        self.assertFalse(self.state.outranked("behind"))
        self.assertIsNotNone(self.state.get_car_priority("a"),
                             "reordering keeps the claimant queued, it does not evict it")

    def test_the_withdraw_bound_is_looser_than_the_reorder_bound(self):
        self.assertGreater(PRIORITY_WITHDRAW_TICKS, PRIORITY_REORDER_TICKS)


class TestReservationManagement(unittest.TestCase):
    """The facade: reservations and occupancy kept in step with one another."""

    def setUp(self):
        self.world = single_crossing_world()
        self.rm = ReservationManagement()
        self.lane_seg = self.world.lane_segment("h1", "right")
        self.crossing = self.world.crossing_segments("h1", "right")[0]

    def test_adding_a_reservation_also_records_the_occupancy(self):
        self.rm.add_car_reservation("c", _info(self.lane_seg))
        self.assertEqual(self.rm.get_cars_on_segment(self.lane_seg), ["c"])
        self.assertIs(self.rm.get_car_reservation("c", 0).segment, self.lane_seg)

    def test_popping_a_reservation_also_clears_the_occupancy(self):
        self.rm.add_car_reservation("c", _info(self.lane_seg))
        self.rm.pop_car_reservation("c", 0)
        self.assertEqual(self.rm.get_cars_on_segment(self.lane_seg), [])

    def test_popping_a_crossing_also_drops_its_departure_time(self):
        self.rm.add_car_reservation("c", _info(self.crossing))
        self.crossing.crossing_segment_state.add_time_to_leave("c", 42)
        self.rm.pop_car_reservation("c", 0)
        self.assertIsNone(self.crossing.crossing_segment_state.get_time_to_leave("c"))

    def test_popping_a_lane_segment_leaves_other_cars_departure_times_alone(self):
        self.rm.add_car_reservation("c", _info(self.crossing))
        self.rm.add_car_reservation("d", _info(self.crossing))
        self.crossing.crossing_segment_state.add_time_to_leave("d", 42)
        self.rm.pop_car_reservation("c", 0)
        self.assertEqual(self.crossing.crossing_segment_state.get_time_to_leave("d"), 42)

    def test_occupancy_order_follows_claim_order(self):
        self.rm.add_car_reservation("first", _info(self.lane_seg))
        self.rm.add_car_reservation("second", _info(self.lane_seg))
        self.assertEqual(self.rm.get_cars_on_segment(self.lane_seg), ["first", "second"])

    def test_reservations_view_is_live_and_the_copy_is_not(self):
        self.rm.add_car_reservation("c", _info(self.lane_seg))
        view = self.rm.get_car_reservations_view("c")
        copy = self.rm.get_car_reservations("c")
        self.rm.add_car_reservation("c", _info(self.crossing))
        self.assertEqual(len(view), 2)
        self.assertEqual(len(copy), 1)

    def test_update_helpers_write_through(self):
        self.rm.add_car_reservation("c", _info(self.lane_seg))
        self.rm.update_car_reservation_begin("c", 0, 5)
        self.rm.update_car_reservation_end("c", 0, 65)
        self.rm.update_car_reservation_turn("c", 0, True)
        stored = self.rm.get_car_reservation("c", 0)
        self.assertEqual((stored.begin, stored.end, stored.turn), (5, 65, True))

    def test_reset_clears_reservations_occupancy_and_lane_changes(self):
        self.rm.add_car_reservation("c", _info(self.lane_seg))
        self.rm.set_lane_change_claim("c", LaneChangeClaim(self.lane_seg, 0))
        self.rm.reset()
        self.assertEqual(self.rm.get_cars_on_segment(self.lane_seg), [])
        self.assertIsNone(self.rm.get_lane_change_claim("c"))


class TestReservationManagementLaneChanges(unittest.TestCase):

    def setUp(self):
        self.world = single_crossing_world()
        self.rm = ReservationManagement()
        self.target = self.world.lane_segment("h1", "right")
        self.other = self.world.lane_segment("v1", "right")

    def test_a_car_that_never_registered_one_reads_as_none(self):
        """FIXED (FINDINGS #3): this used to raise KeyError.

        Every caller already handles None as "no lane change pending", and a
        car that has simply never changed lane is the ordinary case, not a
        lookup error.
        """
        self.assertIsNone(self.rm.get_lane_change_claim("never-seen"))

    def test_a_registered_change_reads_back(self):
        self.rm.set_lane_change_claim("c", LaneChangeClaim(self.target, 4))
        claim = self.rm.get_lane_change_claim("c")
        self.assertEqual((claim.segment, claim.claimed_at), (self.target, 4))

    def test_a_claim_reads_back_as_uncommitted(self):
        self.rm.set_lane_change_claim("c", LaneChangeClaim(self.target, 4))
        self.assertFalse(self.rm.get_lane_change_claim("c").committed)

    def test_committing_marks_the_claim_and_leaves_it_in_place(self):
        self.rm.set_lane_change_claim("c", LaneChangeClaim(self.target, 4))
        self.rm.commit_lane_change_claim("c")
        claim = self.rm.get_lane_change_claim("c")
        self.assertTrue(claim.committed)
        self.assertEqual(self.rm.get_cars_changing_into_segment(self.target), ["c"])

    def test_committing_a_claim_nobody_holds_does_nothing(self):
        self.rm.commit_lane_change_claim("never-seen")
        self.assertIsNone(self.rm.get_lane_change_claim("never-seen"))

    def test_a_committed_change_is_listed_alongside_a_bare_claim(self):
        self.rm.set_lane_change_claim("a", LaneChangeClaim(self.target, 0))
        self.rm.set_lane_change_claim("b", LaneChangeClaim(self.target, 0))
        self.rm.commit_lane_change_claim("b")
        self.assertEqual(sorted(self.rm.get_cars_changing_into_segment(self.target)),
                         ["a", "b"])

    def test_removing_a_change_clears_it(self):
        self.rm.set_lane_change_claim("c", LaneChangeClaim(self.target, 4))
        self.rm.remove_lane_change_claim("c")
        self.assertIsNone(self.rm.get_lane_change_claim("c"))

    def test_cars_changing_into_a_segment_are_listed(self):
        self.rm.set_lane_change_claim("a", LaneChangeClaim(self.target, 0))
        self.rm.set_lane_change_claim("b", LaneChangeClaim(self.target, 0))
        self.rm.set_lane_change_claim("c", LaneChangeClaim(self.other, 0))
        self.assertEqual(sorted(self.rm.get_cars_changing_into_segment(self.target)),
                         ["a", "b"])

    def test_a_cleared_change_no_longer_counts_towards_a_segment(self):
        self.rm.set_lane_change_claim("a", LaneChangeClaim(self.target, 0))
        self.rm.remove_lane_change_claim("a")
        self.assertEqual(self.rm.get_cars_changing_into_segment(self.target), [])

    def test_a_segment_nobody_is_moving_into_lists_nobody(self):
        self.assertEqual(self.rm.get_cars_changing_into_segment(self.target), [])


if __name__ == "__main__":
    unittest.main()
