"""Grid-based path planning for riders on the 8x8 street map.

The map is an 800x800 coordinate system divided into 100x100 cells.
Streets are the grid lines (points whose x or y coordinate is a multiple
of the cell size). The planner prefers routes whose segments run along
streets and always moves in axis-aligned, right-angle steps.
"""

import logging
from typing import List, Tuple

LOGGER = logging.getLogger("dispatch.path")

Point = Tuple[int, int]


class GridMap:
    """Description of the 800x800 map made of 100x100 grid cells.

    Attributes:
        width: Map width in units.
        height: Map height in units.
        cell_size: Size of one grid cell in units.
    """

    def __init__(self, width: int = 800, height: int = 800,
                 cell_size: int = 100) -> None:
        """Create a grid map.

        Args:
            width: Map width (must be a multiple of ``cell_size``).
            height: Map height (must be a multiple of ``cell_size``).
            cell_size: Size of one cell.

        Raises:
            ValueError: If the dimensions are not positive multiples of
                ``cell_size``.
        """
        if cell_size <= 0 or width <= 0 or height <= 0:
            raise ValueError("Map dimensions must be positive")
        if width % cell_size or height % cell_size:
            raise ValueError("Map dimensions must be multiples of cell_size")
        self.width = width
        self.height = height
        self.cell_size = cell_size

    @property
    def cells_per_side(self) -> int:
        """Number of grid cells along one side of the map (8 by default)."""
        return self.width // self.cell_size

    def is_valid_point(self, x: int, y: int) -> bool:
        """Return True if (x, y) lies inside the map bounds."""
        return 0 <= x <= self.width and 0 <= y <= self.height

    def is_street(self, x: int, y: int) -> bool:
        """Return True if the point lies on a street (grid line)."""
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def cell_center(self, col: int, row: int) -> Point:
        """Return the center point of the cell at (col, row)."""
        half = self.cell_size // 2
        return col * self.cell_size + half, row * self.cell_size + half


class PathPlanner:
    """Computes right-angle, street-preferring routes on the grid.

    The planner is stateless with respect to riders; it only needs the
    current position, the target and the alternate-route flag used by
    riders to avoid conflicts.
    """

    def __init__(self, grid_map: GridMap = None) -> None:
        """Create a planner bound to a grid map.

        Args:
            grid_map: Map to plan on. A default 800x800 map is used if None.
        """
        self.grid_map = grid_map or GridMap()

    @staticmethod
    def distance(x1: int, y1: int, x2: int, y2: int) -> int:
        """Return the Manhattan distance between two points."""
        return abs(x1 - x2) + abs(y1 - y2)

    @staticmethod
    def is_directly_above_or_below(x: int, y: int, tx: int, ty: int) -> bool:
        """Return True when the rider shares the target's x coordinate.

        This is the "special case" in which the rider moves purely
        vertically toward the target.
        """
        return x == tx and y != ty

    def _on_street_line(self, value: int) -> bool:
        """Return True if a single coordinate lies on a grid line."""
        return value % self.grid_map.cell_size == 0

    def plan(self, sx: int, sy: int, tx: int, ty: int,
             alternate: bool = False) -> List[Point]:
        """Plan a route from (sx, sy) to (tx, ty) as a list of waypoints.

        If the two points share an x or y coordinate the route is a single
        straight segment. Otherwise two candidate corners are considered:
        horizontal-first and vertical-first. The corner whose segments lie
        on streets scores higher and is chosen unless ``alternate`` is True,
        in which case the other corner is used (conflict avoidance).

        Args:
            sx: Start x coordinate.
            sy: Start y coordinate.
            tx: Target x coordinate.
            ty: Target y coordinate.
            alternate: Prefer the non-default corner when True.

        Returns:
            Ordered list of waypoints beginning with the start point and
            ending with the target point.
        """
        if sx == tx or sy == ty:
            return [(sx, sy), (tx, ty)]

        corner_a = (tx, sy)
        score_a = int(self._on_street_line(sy)) + int(self._on_street_line(tx))
        corner_b = (sx, ty)
        score_b = int(self._on_street_line(sx)) + int(self._on_street_line(ty))

        prefer_a = score_a >= score_b
        if alternate:
            prefer_a = not prefer_a
        corner = corner_a if prefer_a else corner_b
        return [(sx, sy), corner, (tx, ty)]

    def next_position(self, x: int, y: int, tx: int, ty: int, speed: int,
                      alternate: bool = False) -> Point:
        """Return the position reached after moving up to ``speed`` units.

        Movement follows the planned route and never overshoots the target.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            tx: Target x coordinate.
            ty: Target y coordinate.
            speed: Maximum distance travelled in one tick.
            alternate: Use the alternate corner of the route when True.

        Returns:
            The new (x, y) position.
        """
        waypoints = self.plan(x, y, tx, ty, alternate=alternate)
        cx, cy = x, y
        remaining = speed
        for wx, wy in waypoints[1:]:
            while remaining > 0 and (cx, cy) != (wx, wy):
                if cx != wx:
                    step = min(abs(wx - cx), remaining)
                    cx += step if wx > cx else -step
                else:
                    step = min(abs(wy - cy), remaining)
                    cy += step if wy > cy else -step
                remaining -= step
            if remaining <= 0:
                break
        return cx, cy


DEFAULT_PLANNER = PathPlanner()
