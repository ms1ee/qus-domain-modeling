"""Grid-based path planning for the 800x800 street map.

The map is an 8x8 grid of 100x100 cells. Grid lines (coordinates that are
multiples of 100) are streets. Restaurant and customer locations sit at cell
centres. Routes are axis-aligned, and the planner prefers corners whose
segments run along streets.
"""

from typing import List, Sequence, Tuple

Point = Tuple[int, int]

MAP_SIZE = 800
CELL_SIZE = 100
GRID_CELLS = MAP_SIZE // CELL_SIZE
MAX_INPUT_COORD = 1000
DISPLAY_STEP = 50


def cell_center(value: int) -> int:
    """Return the centre coordinate of the grid cell containing ``value``.

    Uses ``center = (value // 100) * 100 + 50``. Values beyond the map are
    clamped to the nearest border cell, so 800 maps to 750.

    Args:
        value: A coordinate on one axis.

    Returns:
        The cell centre coordinate.
    """
    cell = int(value) // CELL_SIZE
    cell = max(0, min(GRID_CELLS - 1, cell))
    return cell * CELL_SIZE + CELL_SIZE // 2


def to_grid_point(x: int, y: int) -> Point:
    """Convert raw coordinates to the centre of their grid cell.

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.

    Returns:
        ``(cell_center_x, cell_center_y)``.
    """
    return (cell_center(x), cell_center(y))


def manhattan(a: Point, b: Point) -> int:
    """Return the Manhattan distance between two points.

    Args:
        a: First point.
        b: Second point.

    Returns:
        ``|ax - bx| + |ay - by|``.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def is_street_point(point: Point) -> bool:
    """Return True if the point lies on a street (a grid line).

    Args:
        point: Point to test.

    Returns:
        True when x or y is a multiple of the cell size.
    """
    return point[0] % CELL_SIZE == 0 or point[1] % CELL_SIZE == 0


def _segment_on_street(a: Point, b: Point) -> bool:
    """Return True if an axis-aligned segment runs along a street.

    Args:
        a: Segment start.
        b: Segment end.

    Returns:
        True for horizontal segments on a street row or vertical segments on
        a street column. Returns False for non-axis-aligned segments.
    """
    if a[1] == b[1]:
        return a[1] % CELL_SIZE == 0
    if a[0] == b[0]:
        return a[0] % CELL_SIZE == 0
    return False


def route_length(points: Sequence[Point]) -> int:
    """Return the total Manhattan length of a polyline.

    Args:
        points: Ordered route points, including the start.

    Returns:
        Sum of segment lengths.
    """
    return sum(manhattan(a, b) for a, b in zip(points, points[1:]))


def expand_route(points: Sequence[Point]) -> List[Point]:
    """Interpolate a polyline into points spaced ``DISPLAY_STEP`` apart.

    Used for drawing routes on the ASCII map.

    Args:
        points: Ordered route points, including the start.

    Returns:
        List of intermediate points, starting with the first point.
    """
    if not points:
        return []
    start = (int(points[0][0]), int(points[0][1]))
    result: List[Point] = [start]
    cur = start
    for raw in points[1:]:
        target = (int(raw[0]), int(raw[1]))
        while cur != target:
            dx = target[0] - cur[0]
            dy = target[1] - cur[1]
            if dx != 0:
                step = min(DISPLAY_STEP, abs(dx))
                cur = (cur[0] + (step if dx > 0 else -step), cur[1])
            else:
                step = min(DISPLAY_STEP, abs(dy))
                cur = (cur[0], cur[1] + (step if dy > 0 else -step))
            result.append(cur)
    return result


class PathPlanner:
    """Plans axis-aligned routes that prefer streets.

    Special cases handled:
        * Target directly above/below or beside the start (straight line).
        * Target located off-street (final approach into a cell centre).
        * Multi-destination routes (restaurant then customer) are chained.
    """

    def plan(self, start: Point, goal: Point) -> List[Point]:
        """Compute waypoints from ``start`` to ``goal``.

        Args:
            start: Current position.
            goal: Destination.

        Returns:
            Waypoints after ``start``, ending with ``goal``. Consecutive points
            are axis-aligned. An empty list means the start is the goal.
        """
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return []
        if start[0] == goal[0] or start[1] == goal[1]:
            return [goal]

        horizontal_first = (goal[0], start[1])
        vertical_first = (start[0], goal[1])
        score_h = int(_segment_on_street(start, horizontal_first)) + \
            int(_segment_on_street(horizontal_first, goal))
        score_v = int(_segment_on_street(start, vertical_first)) + \
            int(_segment_on_street(vertical_first, goal))
        corner = horizontal_first if score_h >= score_v else vertical_first
        return [corner, goal]

    def plan_multi(self, start: Point, stops: Sequence[Point]) -> List[Point]:
        """Plan a continuous route through several stops in order.

        Args:
            start: Starting position.
            stops: Ordered destinations, e.g. ``[restaurant, customer]``.

        Returns:
            Concatenated waypoints for the full route (start excluded).
        """
        points: List[Point] = []
        current = (int(start[0]), int(start[1]))
        for stop in stops:
            leg = self.plan(current, stop)
            points.extend(leg)
            if leg:
                current = leg[-1]
            else:
                current = (int(stop[0]), int(stop[1]))
        return points

    def is_special_case(self, start: Point, goal: Point) -> bool:
        """Return True if the leg needs special handling.

        A leg is special when the goal is directly above/below or beside the
        start, or when the goal is an off-street location.

        Args:
            start: Current position.
            goal: Destination.

        Returns:
            Whether the special-case flag should be raised.
        """
        aligned = start[0] == goal[0] or start[1] == goal[1]
        return aligned or not is_street_point(goal)
