from __future__ import annotations

import unittest

from protocol_inspector import Route, RoutingTable


class RoutingTableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.table = RoutingTable(
            [
                Route.from_strings(
                    "0.0.0.0/0", "wan0", next_hop="203.0.113.1", metric=100
                ),
                Route.from_strings(
                    "10.0.0.0/8", "core0", next_hop="10.0.0.1", metric=20
                ),
                Route.from_strings(
                    "10.20.0.0/16", "branch0", next_hop="10.20.0.1", metric=50
                ),
                Route.from_strings(
                    "10.20.0.0/16", "branch1", next_hop="10.20.0.2", metric=10
                ),
                Route.from_strings("10.20.30.0/24", "lan0", metric=0),
            ]
        )

    def test_longest_prefix_wins_before_metric(self) -> None:
        route = self.table.lookup("10.20.30.99")
        self.assertIsNotNone(route)
        assert route is not None
        self.assertEqual(route.interface, "lan0")

    def test_longest_prefix_wins_even_with_higher_metric(self) -> None:
        # metric을 먼저 비교해 더 구체적인 /24 경로를 버리는 구현을 검출합니다.
        table = RoutingTable(
            [
                Route.from_strings("10.0.0.0/8", "broad", metric=0),
                Route.from_strings("10.20.30.0/24", "specific", metric=500),
            ]
        )
        route = table.lookup("10.20.30.99")
        self.assertIsNotNone(route)
        assert route is not None
        self.assertEqual(route.interface, "specific")

    def test_lower_metric_breaks_equal_prefix_tie(self) -> None:
        route = self.table.lookup("10.20.40.1")
        self.assertIsNotNone(route)
        assert route is not None
        self.assertEqual(route.interface, "branch1")

    def test_default_route_is_a_real_candidate(self) -> None:
        route = self.table.lookup("192.0.2.50")
        self.assertIsNotNone(route)
        assert route is not None
        self.assertEqual(str(route.network), "0.0.0.0/0")

    def test_no_default_route_can_return_none(self) -> None:
        table = RoutingTable([Route.from_strings("10.0.0.0/8", "lan0")])
        self.assertIsNone(table.lookup("203.0.113.9"))

    def test_route_input_is_validated(self) -> None:
        with self.assertRaises(ValueError):
            Route.from_strings("10.0.0.0/8", "", metric=0)
        with self.assertRaises(ValueError):
            Route.from_strings("10.0.0.0/8", "lan0", metric=-1)


if __name__ == "__main__":
    unittest.main()
