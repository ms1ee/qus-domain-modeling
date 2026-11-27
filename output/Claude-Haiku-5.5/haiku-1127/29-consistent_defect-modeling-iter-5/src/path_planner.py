"""Grid-based path planning for riders.

The map is an 8x8 grid of 100x100 cells (800x800 units). Streets lie on the
grid lines (coordinates that are multiples of 100). Restaurants and customers
sit on street intersections, so every planned route runs along streets and
consists only of horizontal and vertical segments joined by right-angle turns.
"""

from typing import List, Sequence, Tuple

Point = Tuple[int, int]


def _dedupe(points: Sequence[Point]) -> List[Point]:
    """Remove consecutive duplicate points from a route.

    Args:
        points: Sequence of (x, y) points.

    Returns:
        List of points with no two consecutive identical entries.
    """
    result: List[Point] = []
    for point in points:
        point = (int(point[0]), int(point[1]))
        if not result or result[-1] != point:
            result.append(point)
    return result


class PathPlanner:
    """Plans and steps rider movement along the street grid.

    Attributes:
        grid_dimension: Number of cells per side (8).
        cell_size: Size of one cell in units (100).
        map_size: Full map size in units (800).
    """

    def __init__(self, grid_dimension: int = 8, cell_size: int = 100) -> None:
        """Create a planner for a square grid.

        Args:
            grid_dimension: Number of cells along one side of the map.
            cell_size: Edge length of a single cell in coordinate units.
        """
        self.grid_dimension = grid_dimension
        self.cell_size = cell_size
        self.map_size = grid_dimension * cell_size

    def is_on_street(self, x: int, y: int) -> bool:
        """Check whether a point lies on a street (a grid line).

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            True if x or y is aligned with a grid line.
        """
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def is_within_map(self, x: int, y: int) -> bool:
        """Check whether a point lies inside the map bounds.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            True if 0 <= x, y <= map_size.
        """
        return 0 <= x <= self.map_size and 0 <= y <= self.map_size

    def plan_route(self, start: Point, goal: Point) -> List[Point]:
        """Plan a street-following route between two points.

        The route moves horizontally first, then vertically, producing a
        single right-angle turn (an L-shaped path along the streets).

        Args:
            start: Starting (x, y) point.
            goal: Destination (x, y) point.

        Returns:
            List of corner points including start and goal.
        """
        sx, sy = start
        gx, gy = goal
        corner = (gx, sy)
        return _dedupe([(sx, sy), corner, (gx, gy)])

    def plan_multi_route(self, points: Sequence[Point]) -> List[Point]:
        """Plan a continuous route passing through several destinations.

        Used for the rider's path from its current position to the restaurant
        and then to the customer.

        Args:
            points: Ordered list of waypoints (start first).

        Returns:
            Combined list of route corner points.
        """
        if not points:
            return []
        route: List[Point] = [(int(points[0][0]), int(points[0][1]))]
        for point in points[1:]:
            segment = self.plan_route(route[-1], (int(point[0]), int(point[1])))
            route.extend(segment[1:])
        return _dedupe(route)

    @staticmethod
    def route_length(route: Sequence[Point]) -> int:
        """Compute the total Manhattan length of a route.

        Args:
            route: Ordered list of route points.

        Returns:
            Sum of segment lengths in coordinate units.
        """
        total = 0
        for (ax, ay), (bx, by) in zip(route, route[1:]):
            total += abs(bx - ax) + abs(by - ay)
        return total

    def next_position(self, x: int, y: int, tx: int, ty: int, speed: int) -> Point:
        """Advance a position towards a target by up to ``speed`` units.

        Movement is horizontal first, then vertical, so the rider never leaves
        the street network when starting from an intersection. The movement
        budget is shared between both axes within a single tick.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            tx: Target x coordinate.
            ty: Target y coordinate.
            speed: Maximum units that can be travelled in one tick.

        Returns:
            New (x, y) position after this tick.
        """
        budget = max(0, int(speed))
        while budget > 0 and (x, y) != (tx, ty):
            if x != tx:
                step = min(budget, abs(tx - x))
                x += step if tx > x else -step
            else:
                step = min(budget, abs(ty - y))
                y += step if ty > y else -step
            budget -= step
        return x, y
