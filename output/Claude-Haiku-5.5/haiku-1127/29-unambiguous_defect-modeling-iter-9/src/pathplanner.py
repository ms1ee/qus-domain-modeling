"""Grid-based path planning on the 8x8 street map.

The map is an 800x800 coordinate plane divided into 8x8 cells of 100 units.
Streets are the lines where ``x % 100 == 0`` or ``y % 100 == 0``. Restaurant
and customer locations sit at cell centres (``x % 100 == 50`` and
``y % 100 == 50``) and are reachable only through driveways from the four
adjacent street points. Movement uses a lattice with a 50-unit step, so every
path is a sequence of axis-aligned moves that stay on streets.
"""

import logging
from collections import deque
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

from config import CELL_SIZE, LATTICE_STEP, MAP_SIZE

logger = logging.getLogger(__name__)

Point = Tuple[int, int]

_DIRECTIONS = (
    (LATTICE_STEP, 0),
    (-LATTICE_STEP, 0),
    (0, LATTICE_STEP),
    (0, -LATTICE_STEP),
)


class PathPlanner:
    """Pathfinding over the street lattice.

    The planner uses breadth-first search, which yields a shortest Manhattan
    route that follows streets. Location cells are treated as dead ends: they
    may be used only as the start or goal of a plan, which prevents riders from
    cutting through restaurants and customers' driveways.

    Attributes:
        algorithm_name: Human-readable name of the algorithm.
    """

    algorithm_name = "BFS on street lattice (streets preferred)"

    @staticmethod
    def is_location(point: Point) -> bool:
        """Return True if ``point`` is a restaurant/customer cell centre."""
        return point[0] % CELL_SIZE == LATTICE_STEP and point[1] % CELL_SIZE == LATTICE_STEP

    @staticmethod
    def in_bounds(point: Point) -> bool:
        """Return True if ``point`` lies within the 0..MAP_SIZE square."""
        return 0 <= point[0] <= MAP_SIZE and 0 <= point[1] <= MAP_SIZE

    @classmethod
    def _edge_allowed(cls, a: Point, b: Point) -> bool:
        """Return True if the unit edge ``a``-``b`` is a legal move.

        Edges on a street (horizontal edge on ``y`` street or vertical edge on
        ``x`` street) are allowed. Edges touching a location are driveways and
        are always allowed.
        """
        if cls.is_location(a) or cls.is_location(b):
            return True
        if a[1] == b[1]:
            return a[1] % CELL_SIZE == 0
        return a[0] % CELL_SIZE == 0

    @classmethod
    def neighbors(cls, point: Point) -> Iterator[Point]:
        """Yield the lattice neighbours of ``point`` reachable along streets.

        Args:
            point: A lattice point.

        Yields:
            Neighbouring lattice points connected by a legal edge.
        """
        for dx, dy in _DIRECTIONS:
            nxt = (point[0] + dx, point[1] + dy)
            if cls.in_bounds(nxt) and cls._edge_allowed(point, nxt):
                yield nxt

    @staticmethod
    def _check_lattice(point: Point) -> None:
        """Raise ``ValueError`` if ``point`` is not on the movement lattice."""
        if point[0] % LATTICE_STEP != 0 or point[1] % LATTICE_STEP != 0:
            raise ValueError(f"Point {point} is not on the {LATTICE_STEP}-unit lattice")
        if not (0 <= point[0] <= MAP_SIZE and 0 <= point[1] <= MAP_SIZE):
            raise ValueError(f"Point {point} is outside the map")

    @classmethod
    def plan(cls, start: Sequence[int], goal: Sequence[int]) -> List[Point]:
        """Compute a street-following path from ``start`` to ``goal``.

        Args:
            start: Starting lattice point ``(x, y)``.
            goal: Destination lattice point ``(x, y)``.

        Returns:
            Ordered list of waypoints after ``start`` up to and including
            ``goal``. Empty if ``start == goal``.

        Raises:
            ValueError: If either point is off-lattice or outside the map.
        """
        s: Point = (int(start[0]), int(start[1]))
        g: Point = (int(goal[0]), int(goal[1]))
        cls._check_lattice(s)
        cls._check_lattice(g)
        if s == g:
            return []

        previous: Dict[Point, Optional[Point]] = {s: None}
        queue = deque([s])
        while queue:
            node = queue.popleft()
            if node == g:
                break
            if cls.is_location(node) and node != s:
                continue
            for nxt in cls.neighbors(node):
                if nxt in previous:
                    continue
                if cls.is_location(nxt) and nxt != g:
                    continue
                previous[nxt] = node
                queue.append(nxt)

        if g not in previous:
            logger.warning("No street path from %s to %s; using fallback route.", s, g)
            return cls._fallback(s, g)

        path: List[Point] = []
        node: Optional[Point] = g
        while node is not None and node != s:
            path.append(node)
            node = previous[node]
        path.reverse()
        return path

    @staticmethod
    def _fallback(start: Point, goal: Point) -> List[Point]:
        """Build a simple L-shaped route used only when no street path exists."""
        corner = (goal[0], start[1])
        path: List[Point] = []
        if corner not in (start, goal):
            path.append(corner)
        path.append(goal)
        return path

    @staticmethod
    def route_length(points: Sequence[Point]) -> int:
        """Return the total Manhattan length of a polyline.

        Args:
            points: Ordered points, including the starting point.

        Returns:
            Sum of the axis-aligned distances between consecutive points.
        """
        total = 0
        for a, b in zip(points, points[1:]):
            total += abs(a[0] - b[0]) + abs(a[1] - b[1])
        return total
