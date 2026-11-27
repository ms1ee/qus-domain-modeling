"""Grid-based path planning for riders.

The city is an 800x800 unit map divided into 8x8 cells of 100x100 units.
Grid lines (x or y multiple of 100) are streets; integer-hundred points are
restaurant / customer locations. Paths are right-angled and prefer segments
that run along streets.
"""

import math
from typing import Iterable, List, Optional, Sequence, Set, Tuple

Point = Tuple[int, int]


class GridMap:
    """Description of the rectangular map and its grid cells.

    Attributes:
        map_size: Side length of the square map in units (800).
        cell_size: Side length of one grid cell in units (100).
        grid_dimension: Number of cells per side (8).
    """

    def __init__(self, map_size: int = 800, cell_size: int = 100) -> None:
        if map_size <= 0 or cell_size <= 0 or map_size % cell_size != 0:
            raise ValueError("map_size must be a positive multiple of cell_size")
        self.map_size = map_size
        self.cell_size = cell_size
        self.grid_dimension = map_size // cell_size

    def is_inside(self, x: int, y: int) -> bool:
        """Return True if the point lies within the map boundaries."""
        return 0 <= x <= self.map_size and 0 <= y <= self.map_size

    def is_street(self, x: int, y: int) -> bool:
        """Return True if the point lies on a street (a grid line)."""
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def is_intersection(self, x: int, y: int) -> bool:
        """Return True if the point is a grid intersection."""
        return x % self.cell_size == 0 and y % self.cell_size == 0

    def cell_of(self, x: int, y: int) -> Tuple[int, int]:
        """Return the (column, row) index of the cell containing a point."""
        col = min(x // self.cell_size, self.grid_dimension - 1)
        row = min(y // self.cell_size, self.grid_dimension - 1)
        return col, row

    def cell_center(self, x: int, y: int) -> Point:
        """Return the center point of the cell containing (x, y).

        Uses ``center = (grid // 100) * 100 + 50`` on each axis.
        """
        cx = (x // self.cell_size) * self.cell_size + self.cell_size // 2
        cy = (y // self.cell_size) * self.cell_size + self.cell_size // 2
        return cx, cy


class PathPlanner:
    """Computes right-angled, street-first routes on the grid.

    Attributes:
        grid_map: The GridMap describing the map.
        grid_size: Number of cells per side.
        cell_size: Size of one cell in units.
    """

    OCCUPIED_PENALTY = 10

    def __init__(self, grid_map: Optional[GridMap] = None) -> None:
        self.grid_map = grid_map or GridMap()
        self.grid_size = self.grid_map.grid_dimension
        self.cell_size = self.grid_map.cell_size

    @staticmethod
    def manhattan(a: Sequence[int], b: Sequence[int]) -> int:
        """Return the Manhattan distance between two points."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def euclidean(a: Sequence[int], b: Sequence[int]) -> float:
        """Return the Euclidean distance between two points."""
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    @staticmethod
    def is_directly_aligned(a: Sequence[int], b: Sequence[int]) -> bool:
        """Return True if the two points share an x or y coordinate."""
        return a[0] == b[0] or a[1] == b[1]

    @staticmethod
    def is_vertical_alignment(a: Sequence[int], b: Sequence[int]) -> bool:
        """Return True if ``b`` is directly above or below ``a``."""
        return a[0] == b[0] and a[1] != b[1]

    def _segment_on_street(self, a: Point, b: Point) -> bool:
        """Return True if an axis-aligned segment runs along a street."""
        if a[1] == b[1]:
            return a[1] % self.cell_size == 0
        if a[0] == b[0]:
            return a[0] % self.cell_size == 0
        return False

    def plan(
        self,
        start: Sequence[int],
        goal: Sequence[int],
        occupied: Optional[Iterable[Point]] = None,
    ) -> List[Point]:
        """Plan a right-angled route from ``start`` to ``goal``.

        Special cases:
            * start == goal: empty route.
            * directly above/below/left/right of the target: straight line.
            * otherwise two L-shaped candidates are scored; the one with the
              fewest off-street segments wins, and corners occupied by other
              riders are penalised to avoid path conflicts.

        Args:
            start: Current position.
            goal: Target position.
            occupied: Positions held by other riders (conflict avoidance).

        Returns:
            Ordered list of waypoints, excluding ``start`` and ending at
            ``goal``. Empty if already at the goal.
        """
        s = (int(start[0]), int(start[1]))
        g = (int(goal[0]), int(goal[1]))
        if s == g:
            return []
        if self.is_directly_aligned(s, g):
            return [g]

        occupied_set: Set[Point] = set(occupied or [])
        horizontal_first: Point = (g[0], s[1])
        vertical_first: Point = (s[0], g[1])

        def cost(corner: Point) -> int:
            total = 0
            for seg_a, seg_b in ((s, corner), (corner, g)):
                if not self._segment_on_street(seg_a, seg_b):
                    total += 1
            if corner in occupied_set:
                total += self.OCCUPIED_PENALTY
            return total

        best = min((horizontal_first, vertical_first), key=cost)
        return [best, g]

    def plan_route(
        self,
        start: Sequence[int],
        stops: Sequence[Sequence[int]],
        occupied: Optional[Iterable[Point]] = None,
    ) -> List[Point]:
        """Plan a multi-destination route visiting ``stops`` in order.

        Used for the continuous restaurant -> customer path optimisation.

        Returns:
            Concatenated waypoints for all legs (start excluded).
        """
        points: List[Point] = []
        current: Point = (int(start[0]), int(start[1]))
        for stop in stops:
            leg = self.plan(current, stop, occupied)
            points.extend(leg)
            if leg:
                current = leg[-1]
        return points

    def path_length(self, start: Sequence[int], waypoints: Sequence[Point]) -> int:
        """Return the total Manhattan length of a waypoint route."""
        total = 0
        current: Point = (int(start[0]), int(start[1]))
        for point in waypoints:
            total += self.manhattan(current, point)
            current = point
        return total
