"""Grid-based path planning for the 800x800 map divided into an 8x8 grid.

Each 100x100 unit cell has a center point at ``(col * 100 + 50, row * 100 + 50)``.
Riders travel between cell centers along the center lines of the grid, which
act as the streets. Routes are planned with Dijkstra's algorithm with a turn
penalty, so straight streets are preferred over frequent right-angle turns.
Movement is non-blocking, so riders never wait on each other, which rules out
deadlock between riders.
"""

import heapq
import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

MAP_SIZE = 800
CELL_SIZE = 100
GRID_SIZE = 8
CENTER_OFFSET = 50
TURN_PENALTY = 1

# Horizontal moves are listed first so that streets are preferred.
STREET_DIRECTIONS: Tuple[Tuple[int, int], ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))

Point = Tuple[int, int]
RoutePoint = Tuple[int, int, Optional[str]]


def validate_coordinate(value: object) -> int:
    """Validate a map coordinate.

    Args:
        value: Candidate coordinate.

    Returns:
        The coordinate as an int.

    Raises:
        ValueError: If the value is not an integer or lies outside 0-800.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"coordinate {value!r} is not an integer")
    if not 0 <= value <= MAP_SIZE:
        raise ValueError(f"coordinate {value} is out of range 0-{MAP_SIZE}")
    return value


def cell_index(coord: int) -> int:
    """Return the grid index (0-7) containing a map coordinate.

    The boundary value 800 is clamped into the last cell.

    Args:
        coord: Map coordinate (0-800).

    Returns:
        Grid index in the range 0-7.
    """
    return min(max(coord // CELL_SIZE, 0), GRID_SIZE - 1)


def grid_cell(x: int, y: int) -> Tuple[int, int]:
    """Return the (column, row) grid cell containing a map position.

    Args:
        x: Map x coordinate.
        y: Map y coordinate.

    Returns:
        Tuple ``(col, row)``.
    """
    return cell_index(x), cell_index(y)


def to_cell_center(x: int, y: int) -> Point:
    """Convert a map position to the center point of its grid cell.

    Uses ``center = (index // 100) * 100 + 50`` for each axis.

    Args:
        x: Map x coordinate.
        y: Map y coordinate.

    Returns:
        Tuple ``(center_x, center_y)``.
    """
    col, row = grid_cell(x, y)
    return col * CELL_SIZE + CENTER_OFFSET, row * CELL_SIZE + CENTER_OFFSET


def manhattan(a: Sequence[int], b: Sequence[int]) -> int:
    """Return the Manhattan distance between two points.

    Args:
        a: First point ``(x, y)``.
        b: Second point ``(x, y)``.

    Returns:
        Manhattan distance in map units.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def route_length(points: Iterable[Sequence[int]]) -> int:
    """Return the total Manhattan length of a polyline.

    Args:
        points: Sequence of points; extra tuple elements are ignored.

    Returns:
        Total length in map units.
    """
    total = 0
    previous = None
    for point in points:
        if previous is not None:
            total += manhattan(previous, point)
        previous = point
    return total


def is_on_street(x: int, y: int) -> bool:
    """Return True if a position lies on a street (a grid center line).

    Args:
        x: Map x coordinate.
        y: Map y coordinate.

    Returns:
        True if x or y lies on a street center line.
    """
    return x % CELL_SIZE == CENTER_OFFSET or y % CELL_SIZE == CENTER_OFFSET


class PathPlanner:
    """Plans axis-aligned routes over the 8x8 street grid."""

    def __init__(self, turn_penalty: int = TURN_PENALTY) -> None:
        """Create a planner.

        Args:
            turn_penalty: Extra cost charged for each right-angle turn.
        """
        self.turn_penalty = turn_penalty

    def plan(self, start: Sequence[int], goal: Sequence[int]) -> List[Point]:
        """Plan a street path between two map positions.

        The returned list starts at the center of the start cell and ends at
        the center of the goal cell. Consecutive points are adjacent cell
        centers, so every segment is horizontal or vertical.

        Args:
            start: Start position ``(x, y)``.
            goal: Goal position ``(x, y)``.

        Returns:
            List of center points ``(x, y)`` describing the path.

        Raises:
            RuntimeError: If no path exists (cannot happen on the full grid).
        """
        start_cell = grid_cell(start[0], start[1])
        goal_cell = grid_cell(goal[0], goal[1])
        start_center = to_cell_center(start[0], start[1])
        if start_cell == goal_cell:
            return [start_center]

        initial_state = (start_cell, -1)
        best: Dict[Tuple[Tuple[int, int], int], float] = {initial_state: 0}
        previous: Dict[Tuple[Tuple[int, int], int], Tuple[Tuple[int, int], int]] = {}
        heap: List[Tuple[float, int, int, int]] = [
            (0, start_cell[0], start_cell[1], -1)
        ]
        goal_state = None

        while heap:
            cost, col, row, direction = heapq.heappop(heap)
            state = ((col, row), direction)
            if cost > best.get(state, math.inf):
                continue
            if (col, row) == goal_cell:
                goal_state = state
                break
            for new_dir, (dc, dr) in enumerate(STREET_DIRECTIONS):
                ncol, nrow = col + dc, row + dr
                if not (0 <= ncol < GRID_SIZE and 0 <= nrow < GRID_SIZE):
                    continue
                step = 1
                if direction != -1 and direction != new_dir:
                    step += self.turn_penalty
                new_cost = cost + step
                new_state = ((ncol, nrow), new_dir)
                if new_cost < best.get(new_state, math.inf):
                    best[new_state] = new_cost
                    previous[new_state] = state
                    heapq.heappush(heap, (new_cost, ncol, nrow, new_dir))

        if goal_state is None:
            raise RuntimeError(f"no path from {start} to {goal}")

        cells: List[Tuple[int, int]] = []
        state = goal_state
        while state is not None:
            cells.append(state[0])
            state = previous.get(state)
        cells.reverse()
        return [(c * CELL_SIZE + CENTER_OFFSET, r * CELL_SIZE + CENTER_OFFSET) for c, r in cells]

    def plan_route(self, start: Sequence[int],
                   stops: Sequence[Tuple[int, int, Optional[str]]]) -> List[RoutePoint]:
        """Plan a continuous multi-destination route.

        Legs are chained one after another (for example current position to
        restaurant, then restaurant to customer). Each stop is tagged on the
        route point where it is reached.

        Args:
            start: Start position ``(x, y)``.
            stops: Sequence of ``(x, y, tag)`` stops in visiting order.

        Returns:
            List of ``(x, y, tag)`` route points. ``tag`` is None for
            intermediate points and the stop tag for reached stops.
        """
        current = to_cell_center(start[0], start[1])
        route: List[RoutePoint] = [(current[0], current[1], None)]
        for stop_x, stop_y, tag in stops:
            leg = self.plan(current, (stop_x, stop_y))
            points = leg[1:] or [current]
            for px, py in points:
                route.append((px, py, None))
            last_x, last_y = points[-1]
            route[-1] = (last_x, last_y, tag)
            current = (last_x, last_y)
        return route
