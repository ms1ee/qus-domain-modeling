"""Grid-based path planning for the 8x8 delivery map.

The map is an 800x800 unit area divided into 8x8 cells of 100x100 units.
Grid lines (coordinates that are multiples of 100) are streets.  Restaurant
and customer locations are cell centres (``100 * k + 50``).  Routes are made
of axis-aligned legs only and prefer to travel along the nearest street.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = 8

Point = Tuple[int, int]


class PathPlanner:
    """Stateless helper providing grid coordinates, routes and movement.

    Route rules:
        * A target directly above/below (same x) or on the same row (same y)
          is reached by a straight line (the "special case").
        * Otherwise the rider first moves to the nearest street row, travels
          along that street to the target column, and finally leaves the
          street towards the target.
    """

    @staticmethod
    def clamp(value: int, low: int = 0, high: int = MAP_SIZE) -> int:
        """Clamp ``value`` into the inclusive range ``[low, high]``."""
        return max(low, min(high, int(value)))

    @staticmethod
    def cell_index(value: int) -> int:
        """Return the grid index (0-7) of a coordinate value."""
        return min(max(int(value), 0) // CELL_SIZE, GRID_DIM - 1)

    @classmethod
    def cell_of(cls, x: int, y: int) -> Tuple[int, int]:
        """Return the ``(column, row)`` grid cell containing ``(x, y)``."""
        return cls.cell_index(x), cls.cell_index(y)

    @classmethod
    def cell_center(cls, x: int, y: int) -> Point:
        """Convert a coordinate to the centre of its grid cell.

        Uses ``center = (value // 100) * 100 + 50`` per axis.
        """
        col, row = cls.cell_of(x, y)
        half = CELL_SIZE // 2
        return col * CELL_SIZE + half, row * CELL_SIZE + half

    @staticmethod
    def is_street(x: int, y: int) -> bool:
        """Return True if the point lies on a street (grid line)."""
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    @classmethod
    def nearest_street(cls, value: int) -> int:
        """Return the grid line closest to ``value`` (clamped to the map)."""
        return cls.clamp(((int(value) + CELL_SIZE // 2) // CELL_SIZE) * CELL_SIZE)

    @staticmethod
    def is_straight(start: Sequence[int], target: Sequence[int]) -> bool:
        """Return True when start and target share a column or a row.

        This is the "directly above or below" special case.
        """
        return start[0] == target[0] or start[1] == target[1]

    @classmethod
    def build_route(cls, start: Sequence[int], target: Sequence[int]) -> List[Point]:
        """Build the list of waypoints from ``start`` to ``target``.

        Args:
            start: Current ``(x, y)`` position.
            target: Destination ``(x, y)`` position.

        Returns:
            Waypoints in travel order, excluding the start point. The last
            waypoint is the target. An empty list means already there.
        """
        sx, sy = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        if (sx, sy) == (tx, ty):
            return []
        if cls.is_straight((sx, sy), (tx, ty)):
            return [(tx, ty)]
        street_y = cls.nearest_street(sy)
        candidates = [(sx, street_y), (tx, street_y), (tx, ty)]
        route: List[Point] = []
        previous = (sx, sy)
        for point in candidates:
            if point != previous:
                route.append(point)
                previous = point
        return route

    @staticmethod
    def advance(x: int, y: int, route: List[Point], speed: int) -> Point:
        """Move along ``route`` by up to ``speed`` units.

        Reached waypoints are removed from ``route`` in place.  Movement is
        always axis-aligned.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            route: Mutable list of remaining waypoints.
            speed: Maximum Manhattan distance to travel this tick.

        Returns:
            The new ``(x, y)`` position.
        """
        remaining = int(speed)
        while remaining > 0 and route:
            tx, ty = route[0]
            dx = tx - x
            dy = ty - y
            distance = abs(dx) + abs(dy)
            if distance == 0:
                route.pop(0)
                continue
            step = min(remaining, distance)
            if dx != 0:
                x += step if dx > 0 else -step
            else:
                y += step if dy > 0 else -step
            remaining -= step
            if (x, y) == (tx, ty):
                route.pop(0)
        return x, y
