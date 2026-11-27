"""Grid-based path planning on the 800x800 street map.

The map is an 8x8 grid of 100x100 blocks. Streets are the lines where ``x``
or ``y`` is a multiple of 100. Locations (restaurants, customers, and
intersections) sit at integer hundreds. Riders only move along streets, one
unit per step. Breadth-first search gives shortest right-angle routes, and
neighbours closer to the goal are explored first so that routes tend to run
straight whenever possible.
"""

import random
from collections import deque
from typing import Deque, Dict, List, Optional, Sequence, Tuple

MAP_SIZE = 800
BLOCK_SIZE = 100
GRID_DIMENSION = MAP_SIZE // BLOCK_SIZE  # 8 cells per side

Point = Tuple[int, int]


def is_on_map(x: int, y: int) -> bool:
    """Return True when the point lies inside the 0-800 map bounds.

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.
    """
    return 0 <= x <= MAP_SIZE and 0 <= y <= MAP_SIZE


def is_on_road(x: int, y: int) -> bool:
    """Return True when the point lies on a street.

    A point is on a street when its x or y coordinate is a multiple of 100.

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.
    """
    if not is_on_map(x, y):
        return False
    return x % BLOCK_SIZE == 0 or y % BLOCK_SIZE == 0


def manhattan(a: Sequence[int], b: Sequence[int]) -> int:
    """Return the Manhattan distance between two points.

    Args:
        a: First point as ``(x, y)``.
        b: Second point as ``(x, y)``.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def snap_coordinate(value: float) -> int:
    """Clamp a coordinate to 0-800 and snap it to the nearest multiple of 100.

    Args:
        value: Raw coordinate value.

    Returns:
        The nearest integer hundred within the map bounds.
    """
    clamped = max(0.0, min(float(MAP_SIZE), float(value)))
    snapped = int(clamped / BLOCK_SIZE + 0.5) * BLOCK_SIZE
    return max(0, min(MAP_SIZE, snapped))


def snap_point(x: float, y: float) -> Point:
    """Snap both coordinates of a point to the nearest location (integer hundred).

    Args:
        x: Raw horizontal coordinate.
        y: Raw vertical coordinate.

    Returns:
        A ``(x, y)`` tuple where both coordinates are multiples of 100.
    """
    return (snap_coordinate(x), snap_coordinate(y))


def grid_cell(point: Sequence[int]) -> Tuple[int, int]:
    """Return the (column, row) index of the 8x8 grid cell containing a point.

    Args:
        point: Point as ``(x, y)``.

    Returns:
        Tuple ``(col, row)`` with both values in the range 0-7.
    """
    col = min(int(point[0]) // BLOCK_SIZE, GRID_DIMENSION - 1)
    row = min(int(point[1]) // BLOCK_SIZE, GRID_DIMENSION - 1)
    return (col, row)


class PathPlanner:
    """Plans street-constrained routes between map points.

    Attributes:
        _rng: Random generator used to pick random road positions.
    """

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        """Create a planner.

        Args:
            rng: Optional random generator. A new one is created when omitted.
        """
        self._rng = rng if rng is not None else random.Random()

    @staticmethod
    def neighbors(point: Point, goal: Point) -> List[Point]:
        """Return the street neighbours of a point, closest-to-goal first.

        Args:
            point: Current road point.
            goal: Destination used to order the neighbours.

        Returns:
            List of neighbouring points that lie on a street.
        """
        x, y = point
        candidates = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        candidates = [p for p in candidates if is_on_road(p[0], p[1])]
        candidates.sort(key=lambda p: manhattan(p, goal))
        return candidates

    def find_path(self, start: Sequence[int], goal: Sequence[int]) -> Optional[List[Point]]:
        """Compute the shortest street path from ``start`` to ``goal``.

        The start point is excluded from the result and the goal point is
        included as the final element.

        Args:
            start: Starting point ``(x, y)`` on a street.
            goal: Destination point ``(x, y)`` on a street.

        Returns:
            List of points to visit in order (empty when already at the goal),
            or None when either point is off-street or the goal is unreachable.
        """
        start_pt = (int(start[0]), int(start[1]))
        goal_pt = (int(goal[0]), int(goal[1]))
        if not is_on_road(*start_pt) or not is_on_road(*goal_pt):
            return None
        if start_pt == goal_pt:
            return []

        parent: Dict[Point, Optional[Point]] = {start_pt: None}
        queue: Deque[Point] = deque([start_pt])
        while queue:
            current = queue.popleft()
            if current == goal_pt:
                break
            for nxt in self.neighbors(current, goal_pt):
                if nxt not in parent:
                    parent[nxt] = current
                    queue.append(nxt)

        if goal_pt not in parent:
            return None

        path: List[Point] = []
        node: Optional[Point] = goal_pt
        while node is not None and node != start_pt:
            path.append(node)
            node = parent[node]
        path.reverse()
        return path

    def random_road_point(self) -> Point:
        """Return a random point on a street, used to place new riders.

        Returns:
            A random ``(x, y)`` point where x or y is a multiple of 100.
        """
        if self._rng.random() < 0.5:
            y = self._rng.randint(0, GRID_DIMENSION) * BLOCK_SIZE
            x = self._rng.randint(0, MAP_SIZE)
        else:
            x = self._rng.randint(0, GRID_DIMENSION) * BLOCK_SIZE
            y = self._rng.randint(0, MAP_SIZE)
        return (x, y)

    @staticmethod
    def is_straight(a: Sequence[int], b: Sequence[int]) -> bool:
        """Return True when two points share an x or y coordinate.

        Args:
            a: First point.
            b: Second point.
        """
        return a[0] == b[0] or a[1] == b[1]
