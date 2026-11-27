"""Grid-based path planning for the dispatch simulator.

The 800x800 map is divided into an 8x8 grid of 100x100 cells. Riders travel
along streets, which connect the centre points of neighbouring cells. Every
route is made of axis-aligned legs, so a rider always moves horizontally or
vertically and never cuts through a block diagonally.
"""

from __future__ import annotations

import logging
from typing import Iterable, List, Optional, Sequence, Set, Tuple

from config import get_config

Point = Tuple[int, int]

logger = logging.getLogger(__name__)


def manhattan(a: Sequence[int], b: Sequence[int]) -> int:
    """Return the Manhattan (street) distance between two points.

    Args:
        a: First point as (x, y).
        b: Second point as (x, y).

    Returns:
        The sum of the absolute x and y differences.
    """
    return abs(int(a[0]) - int(b[0])) + abs(int(a[1]) - int(b[1]))


def route_length(start: Sequence[int], waypoints: Iterable[Sequence[int]]) -> int:
    """Return the total street length of a route.

    Args:
        start: Starting point as (x, y).
        waypoints: Ordered points the route passes through.

    Returns:
        Sum of Manhattan distances between consecutive points.
    """
    total = 0
    current = start
    for point in waypoints:
        total += manhattan(current, point)
        current = point
    return total


class GridMap:
    """Coordinate system of the 8x8 grid map.

    Attributes:
        map_size: Side length of the map in units (800 by default).
        cell_size: Side length of a grid cell in units (100 by default).
        size: Number of cells per side (8 by default).
    """

    def __init__(self, map_size: int = 800, cell_size: int = 100) -> None:
        """Create a grid map.

        Args:
            map_size: Side length of the map in units.
            cell_size: Side length of one cell in units.

        Raises:
            ValueError: If the sizes are not positive or do not divide evenly.
        """
        if map_size <= 0 or cell_size <= 0 or map_size % cell_size != 0:
            raise ValueError("invalid map and cell size")
        self.map_size = map_size
        self.cell_size = cell_size
        self.size = map_size // cell_size

    @classmethod
    def from_config(cls) -> "GridMap":
        """Build a grid map from the active configuration.

        Returns:
            A GridMap matching the configured map and cell sizes.
        """
        cfg = get_config()
        return cls(cfg.map_size, cfg.cell_size)

    def cell_index(self, coord: int) -> int:
        """Return the grid index of a coordinate, clamped to the map.

        Coordinates equal to the map size (800) belong to the last cell.

        Args:
            coord: Coordinate in units.

        Returns:
            Cell index in the range 0..size-1.
        """
        return min(max(int(coord) // self.cell_size, 0), self.size - 1)

    def cell_center(self, coord: int) -> int:
        """Return the centre coordinate of the cell containing ``coord``.

        Implements ``center = (grid // cell) * cell + cell // 2``.

        Args:
            coord: Coordinate in units.

        Returns:
            Centre coordinate of the cell along that axis.
        """
        return self.cell_index(coord) * self.cell_size + self.cell_size // 2

    def snap(self, x: int, y: int) -> Point:
        """Convert a raw coordinate pair to the centre of its grid cell.

        Args:
            x: Raw x coordinate.
            y: Raw y coordinate.

        Returns:
            Tuple (center_x, center_y).
        """
        return self.cell_center(x), self.cell_center(y)

    def in_range(self, x: int, y: int) -> bool:
        """Check whether a coordinate pair lies on the map.

        Args:
            x: x coordinate.
            y: y coordinate.

        Returns:
            True when both coordinates are within 0..map_size.
        """
        return 0 <= x <= self.map_size and 0 <= y <= self.map_size


class PathPlanner:
    """Plans street-based routes on the grid.

    Routes are returned as lists of waypoints that the rider visits in order.
    The planner prefers a right-angle route through a street intersection, and
    picks the alternative corner when the preferred one is occupied by another
    rider. This keeps riders from queuing on the same intersection.
    """

    def __init__(self, grid_map: GridMap) -> None:
        """Create a planner bound to a grid map.

        Args:
            grid_map: The GridMap describing the coordinate system.
        """
        self.grid_map = grid_map

    def plan(
        self,
        start: Sequence[int],
        goal: Sequence[int],
        occupied: Optional[Set[Point]] = None,
    ) -> List[Point]:
        """Plan a route from ``start`` to the cell centre nearest ``goal``.

        Special cases:
            * Start and goal identical: empty route.
            * Goal directly above/below/left/right of start: a single straight leg.
            * Otherwise: a right-angle route through one of two corners.

        Args:
            start: Current position (x, y).
            goal: Destination (x, y); snapped to the cell centre.
            occupied: Positions occupied by other riders, used to avoid
                intersections where riders would collide.

        Returns:
            Ordered waypoints excluding the start point.
        """
        sx, sy = int(start[0]), int(start[1])
        gx, gy = self.grid_map.snap(int(goal[0]), int(goal[1]))
        if (sx, sy) == (gx, gy):
            return []
        if sx == gx or sy == gy:
            return [(gx, gy)]

        horizontal_first = (gx, sy)
        vertical_first = (sx, gy)
        blocked = occupied or set()
        corner = horizontal_first
        if horizontal_first in blocked and vertical_first not in blocked:
            corner = vertical_first
            logger.debug("Avoiding occupied corner %s", horizontal_first)
        return [corner, (gx, gy)]

    def plan_route(
        self,
        start: Sequence[int],
        stops: Iterable[Sequence[int]],
        occupied: Optional[Set[Point]] = None,
    ) -> List[Point]:
        """Plan a continuous route that visits several stops in order.

        Used for the restaurant-then-customer path of an order.

        Args:
            start: Starting position (x, y).
            stops: Ordered stops, e.g. [restaurant, customer].
            occupied: Positions occupied by other riders.

        Returns:
            Ordered waypoints for the complete route, excluding the start.
        """
        waypoints: List[Point] = []
        current: Point = (int(start[0]), int(start[1]))
        for stop in stops:
            leg = self.plan(current, stop, occupied)
            waypoints.extend(leg)
            current = self.grid_map.snap(int(stop[0]), int(stop[1]))
        return waypoints
