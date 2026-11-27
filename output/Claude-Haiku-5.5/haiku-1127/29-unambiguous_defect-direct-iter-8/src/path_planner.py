"""Grid-based path planning for the 800x800 street network.

Coordinate model
----------------
* The map is 800 x 800 units divided into 8 x 8 cells of 100 x 100 units.
* Restaurants and customers sit at cell centres (50, 150, ..., 750).
* Streets are the grid lines where ``x % 100 == 0`` or ``y % 100 == 0``.
* A location at a cell centre is reached through a short access stub to the
  street point directly below it (``(cx, cy - 50)``).  This also covers the
  "directly above or below the target" special case.
* The planner searches a 50-unit lattice of street points with breadth-first
  search.  The result is a shortest right-angle path that prefers straight
  runs along streets.
"""

import random
from collections import deque
from typing import Deque, Dict, Iterator, List, Optional, Sequence, Tuple

from globalvar import CELL_SIZE, GRID_SIZE, MAP_SIZE

Point = Tuple[int, int]

HALF_CELL: int = CELL_SIZE // 2      # 50
LATTICE_STEP: int = HALF_CELL        # resolution of the street lattice


def clamp_coordinate(value: int) -> int:
    """Clamp a coordinate into the valid map range ``[0, MAP_SIZE]``.

    Args:
        value: Raw integer coordinate.

    Returns:
        The clamped coordinate.
    """
    return max(0, min(MAP_SIZE, int(value)))


def cell_index(value: int) -> int:
    """Return the grid index (0-7) of a map coordinate.

    Values at or beyond the map edge are assigned to the last cell.

    Args:
        value: Map coordinate in units.

    Returns:
        Grid index along one axis.
    """
    clamped = max(0, min(MAP_SIZE - 1, int(value)))
    return min(clamped // CELL_SIZE, GRID_SIZE - 1)


def to_grid_center(point: Sequence[int]) -> Point:
    """Convert an input coordinate to the centre of its grid cell.

    Implements ``center = (value // 100) * 100 + 50`` per axis, with boundary
    clamping.

    Args:
        point: Pair ``(x, y)`` of integers.

    Returns:
        The cell centre ``(cx, cy)``.
    """
    x, y = point
    return (
        cell_index(x) * CELL_SIZE + HALF_CELL,
        cell_index(y) * CELL_SIZE + HALF_CELL,
    )


def grid_cell_of(point: Sequence[int]) -> Point:
    """Return the ``(column, row)`` grid cell index containing ``point``.

    Args:
        point: Pair ``(x, y)`` of map coordinates.

    Returns:
        Pair ``(column, row)`` with both values in ``0..7``.
    """
    return cell_index(point[0]), cell_index(point[1])


def is_street_point(x: int, y: int) -> bool:
    """Return True when ``(x, y)`` lies on a street (grid line).

    Args:
        x: X coordinate.
        y: Y coordinate.
    """
    if not (0 <= x <= MAP_SIZE and 0 <= y <= MAP_SIZE):
        return False
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def is_cell_center(x: int, y: int) -> bool:
    """Return True when ``(x, y)`` is a restaurant/customer cell centre.

    Args:
        x: X coordinate.
        y: Y coordinate.
    """
    return x % CELL_SIZE == HALF_CELL and y % CELL_SIZE == HALF_CELL


def access_point(point: Point) -> Point:
    """Return the street point a rider must reach before entering ``point``.

    Street points are their own access point.  A cell centre is accessed from
    the street directly below it.

    Args:
        point: Location on the map.

    Returns:
        A street point.
    """
    x, y = point
    if is_street_point(x, y):
        return (x, y)
    return (x, y - HALF_CELL)


def _build_road_points() -> Tuple[Point, ...]:
    """Enumerate every lattice point that lies on a street."""
    points = []
    for x in range(0, MAP_SIZE + 1, LATTICE_STEP):
        for y in range(0, MAP_SIZE + 1, LATTICE_STEP):
            if is_street_point(x, y):
                points.append((x, y))
    return tuple(points)


ROAD_POINTS: Tuple[Point, ...] = _build_road_points()


def random_road_point(rng: Optional[random.Random] = None) -> Point:
    """Pick a random street point, used to place newly recruited riders.

    Args:
        rng: Optional random generator; the module-level generator is used
            when omitted.

    Returns:
        A lattice point lying on a street.
    """
    generator = rng if rng is not None else random
    return generator.choice(ROAD_POINTS)


class PathPlanner:
    """Plan right-angle, street-following routes on the map.

    The planner is stateless; a single instance may be shared freely.
    """

    @staticmethod
    def _neighbors(point: Point) -> Iterator[Point]:
        """Yield the street-lattice neighbours reachable along a street.

        A horizontal step is allowed only along a horizontal street
        (``y % 100 == 0``); a vertical step only along a vertical street
        (``x % 100 == 0``).
        """
        x, y = point
        if y % CELL_SIZE == 0:
            for nx in (x - LATTICE_STEP, x + LATTICE_STEP):
                if 0 <= nx <= MAP_SIZE:
                    yield (nx, y)
        if x % CELL_SIZE == 0:
            for ny in (y - LATTICE_STEP, y + LATTICE_STEP):
                if 0 <= ny <= MAP_SIZE:
                    yield (x, ny)

    def _bfs(self, start: Point, goal: Point) -> List[Point]:
        """Return the shortest lattice path from ``start`` to ``goal``.

        Both endpoints must be street points.  The returned list includes both
        endpoints.

        Raises:
            RuntimeError: If no path exists (should not occur on this grid).
        """
        if start == goal:
            return [start]
        parent: Dict[Point, Optional[Point]] = {start: None}
        queue: Deque[Point] = deque([start])
        while queue:
            current = queue.popleft()
            if current == goal:
                break
            for neighbor in self._neighbors(current):
                if neighbor not in parent:
                    parent[neighbor] = current
                    queue.append(neighbor)
        if goal not in parent:
            raise RuntimeError(f"No street path from {start} to {goal}")
        path: List[Point] = []
        node: Optional[Point] = goal
        while node is not None:
            path.append(node)
            node = parent[node]
        path.reverse()
        return path

    def plan(self, start: Point, goal: Point) -> List[Point]:
        """Plan a street-following route from ``start`` to ``goal``.

        Args:
            start: Current position (street point or cell centre).
            goal: Destination (street point or cell centre).

        Returns:
            Ordered list of waypoints that follow the route.  ``start`` is not
            included; the last element is ``goal``.  The list is empty when
            ``start == goal``.

        Raises:
            ValueError: If either point lies outside the map.
        """
        for x, y in (start, goal):
            if not (0 <= x <= MAP_SIZE and 0 <= y <= MAP_SIZE):
                raise ValueError(f"Point ({x}, {y}) is outside the map")
        start_acc = access_point(start)
        goal_acc = access_point(goal)
        path: List[Point] = [start]
        if start_acc != start:
            path.append(start_acc)
        lattice = self._bfs(start_acc, goal_acc)
        path.extend(lattice[1:])
        if goal_acc != goal:
            path.append(goal)
        return path[1:]

    @staticmethod
    def route_length(points: Sequence[Point], start: Point) -> int:
        """Return the total travelled distance along ``points``.

        Args:
            points: Waypoints in travel order.
            start: Point the route begins from.

        Returns:
            Sum of axis-aligned segment lengths, in map units.
        """
        total = 0
        cx, cy = start
        for x, y in points:
            total += abs(x - cx) + abs(y - cy)
            cx, cy = x, y
        return total

    def distance(self, start: Point, goal: Point) -> int:
        """Return the street-route distance between two points.

        Args:
            start: Origin point.
            goal: Destination point.

        Returns:
            Route length in map units.
        """
        return self.route_length(self.plan(start, goal), start)
