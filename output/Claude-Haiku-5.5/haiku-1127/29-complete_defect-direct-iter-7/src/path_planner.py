"""Grid-based path planning along the street network of the 8x8 map.

Routes are sequences of waypoints (grid-cell centres).  Every leg is
axis-aligned, so a route always follows streets and turns at right angles.
A leg whose endpoints share an x or y coordinate is a straight line (the
"directly above / below / beside" special case).
"""

from __future__ import annotations

from typing import Iterable, Sequence

Point = tuple[int, int]


class PathPlanner:
    """Plans and advances street-following routes between grid points."""

    @staticmethod
    def is_aligned(a: Point, b: Point) -> bool:
        """Return True if two points share a street line (same x or y).

        Args:
            a: First point.
            b: Second point.

        Returns:
            bool: Whether a straight street segment joins the points.
        """
        return a[0] == b[0] or a[1] == b[1]

    @classmethod
    def plan(cls, start: Sequence[int], goal: Sequence[int],
             prefer_vertical: bool = False) -> list[Point]:
        """Plan the waypoints from ``start`` to ``goal``.

        Args:
            start: Starting point.
            goal: Destination point.
            prefer_vertical: If True, use the corner that moves vertically
                first; this is the alternate route used to avoid blocking.

        Returns:
            list[Point]: Waypoints after ``start`` ending at ``goal``.  Empty
            if the points coincide.
        """
        s = (int(start[0]), int(start[1]))
        g = (int(goal[0]), int(goal[1]))
        if s == g:
            return []
        if cls.is_aligned(s, g):
            # Special case: target directly above/below/beside the start.
            return [g]
        if prefer_vertical:
            corner = (s[0], g[1])
        else:
            corner = (g[0], s[1])
        return [corner, g]

    @classmethod
    def plan_route(cls, start: Sequence[int],
                   stops: Iterable[Sequence[int]]) -> list[Point]:
        """Plan a continuous route visiting several destinations in order.

        Args:
            start: Starting point.
            stops: Ordered destinations (e.g. restaurant, then customer).

        Returns:
            list[Point]: Concatenated waypoints for the whole route.
        """
        route: list[Point] = []
        current = (int(start[0]), int(start[1]))
        for stop in stops:
            target = (int(stop[0]), int(stop[1]))
            route.extend(cls.plan(current, target))
            current = target
        return route

    @staticmethod
    def route_length(start: Sequence[int],
                     waypoints: Iterable[Sequence[int]]) -> int:
        """Return the total street distance of a waypoint route.

        Args:
            start: Starting point of the route.
            waypoints: Waypoints of the route in order.

        Returns:
            int: Sum of Manhattan lengths of each leg.
        """
        total = 0
        cur = (int(start[0]), int(start[1]))
        for point in waypoints:
            nxt = (int(point[0]), int(point[1]))
            total += abs(nxt[0] - cur[0]) + abs(nxt[1] - cur[1])
            cur = nxt
        return total

    @staticmethod
    def advance(position: Sequence[int], waypoints: Sequence[Sequence[int]],
                budget: int) -> tuple[Point, list[Point]]:
        """Move along a waypoint route using at most ``budget`` units.

        Movement is axis-aligned: along the x axis towards the current
        waypoint first, then along the y axis.  Reached waypoints are
        dropped from the returned list.

        Args:
            position: Current (x, y) position.
            waypoints: Remaining waypoints of the route.
            budget: Maximum distance (units) that may be travelled.

        Returns:
            tuple: (new position, remaining waypoints).
        """
        x, y = int(position[0]), int(position[1])
        remaining = [(int(p[0]), int(p[1])) for p in waypoints]
        while budget > 0 and remaining:
            tx, ty = remaining[0]
            if (x, y) == (tx, ty):
                remaining.pop(0)
                continue
            if x != tx:
                step = min(budget, abs(tx - x))
                x += step if tx > x else -step
            else:
                step = min(budget, abs(ty - y))
                y += step if ty > y else -step
            budget -= step
        return (x, y), remaining
