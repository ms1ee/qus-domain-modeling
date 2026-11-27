"""Grid-based path planning on the 8x8 street network.

Streets are the grid lines where x or y is a multiple of the cell size.
Riders travel along streets using right-angle turns: they first move
horizontally to the target column, then vertically to the target row.
"""

import math
from typing import List, Tuple

Point = Tuple[int, int]


class PathPlanner:
    """Pathfinding and movement logic for riders on the street grid.

    Attributes:
        grid_dimension (int): Number of cells per side (8).
        cell_size (int): Size of one cell in map units (100).
        map_size (int): Total map size in units (800).
    """

    def __init__(self, grid_dimension: int = 8, cell_size: int = 100) -> None:
        """Create a planner for the given grid.

        Args:
            grid_dimension: Number of grid cells per side.
            cell_size: Size of each grid cell in units.
        """
        self.grid_dimension = grid_dimension
        self.cell_size = cell_size
        self.map_size = grid_dimension * cell_size

    def is_on_street(self, x: int, y: int) -> bool:
        """Return True if the point lies on a street (grid line).

        Args:
            x: X coordinate.
            y: Y coordinate.
        """
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def in_bounds(self, x: int, y: int) -> bool:
        """Return True if the point lies inside the map.

        Args:
            x: X coordinate.
            y: Y coordinate.
        """
        return 0 <= x <= self.map_size and 0 <= y <= self.map_size

    def next_step(self, x: int, y: int, tx: int, ty: int,
                  speed: int) -> Tuple[int, int, bool]:
        """Advance a position by at most ``speed`` units toward a target.

        Movement is horizontal first, then vertical, so the rider keeps
        travelling along streets. When the target lies directly above or
        below (or beside) the current position the movement is a straight
        line and ``special_case`` is True.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            tx: Target x coordinate.
            ty: Target y coordinate.
            speed: Maximum distance to travel this tick.

        Returns:
            A tuple ``(new_x, new_y, special_case)``.
        """
        if (x, y) == (tx, ty):
            return x, y, False
        special_case = x == tx or y == ty
        remaining = max(int(speed), 0)
        cx, cy = x, y
        if cx != tx and remaining > 0:
            step = min(remaining, abs(tx - cx))
            cx += step if tx > cx else -step
            remaining -= step
        if cx == tx and cy != ty and remaining > 0:
            step = min(remaining, abs(ty - cy))
            cy += step if ty > cy else -step
        return cx, cy, special_case

    def route_points(self, start: Point, end: Point, step: int = 50) -> List[Point]:
        """Return the street route from ``start`` to ``end`` as points.

        The route goes horizontally first, then vertically. Points are
        emitted every ``step`` units so the route can be drawn on a map.

        Args:
            start: Starting point.
            end: Destination point.
            step: Spacing between emitted points.

        Returns:
            List of points including both endpoints.
        """
        points: List[Point] = [start]
        x, y = start
        tx, ty = end
        while x != tx:
            delta = min(step, abs(tx - x))
            x += delta if tx > x else -delta
            points.append((x, y))
        while y != ty:
            delta = min(step, abs(ty - y))
            y += delta if ty > y else -delta
            points.append((x, y))
        return points

    def route_through(self, stops: List[Point], step: int = 50) -> List[Point]:
        """Build one continuous route visiting ``stops`` in order.

        Args:
            stops: Ordered list of points (for example rider, restaurant,
                customer).
            step: Spacing between emitted points.

        Returns:
            Combined list of route points without duplicated joints.
        """
        if not stops:
            return []
        route: List[Point] = [stops[0]]
        for previous, current in zip(stops, stops[1:]):
            segment = self.route_points(previous, current, step)
            route.extend(segment[1:])
        return route

    @staticmethod
    def ticks_needed(distance: int, speed: int) -> int:
        """Return the number of ticks needed to cover a distance.

        Args:
            distance: Distance in map units.
            speed: Speed in units per tick.

        Returns:
            Ceiling of distance / speed (0 if distance is 0).
        """
        if distance <= 0:
            return 0
        if speed <= 0:
            raise ValueError("speed must be positive")
        return math.ceil(distance / speed)

    @staticmethod
    def manhattan(a: Point, b: Point) -> int:
        """Return the Manhattan distance between two points.

        Args:
            a: First point.
            b: Second point.
        """
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
