"""Grid-based path planning.

Routes are built from axis-aligned legs.  For a diagonal move the planner
chooses the corner that lies on a street, so the rider prefers travelling
along the road network.  Straight moves along one row or column are used
when the start and goal share a coordinate.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List

import grid

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Location:
    """A point on the map.

    Attributes:
        x (int): x coordinate.
        y (int): y coordinate.
    """

    x: int
    y: int


@dataclass
class Route:
    """A planned route.

    Attributes:
        points (list[Location]): ordered points, starting at the origin.
        total_distance (float): total Manhattan length of the route.
        estimated_ticks (int): ticks needed at the planned speed.
    """

    points: List[Location] = field(default_factory=list)
    total_distance: float = 0.0
    estimated_ticks: int = 0


class PathPlanner:
    """Computes street-first routes on the 8x8 grid.

    Attributes:
        grid_size (int): number of cells per side.
        cell_size (int): size of one cell in units.
    """

    def __init__(self, grid_size=grid.GRID_DIM, cell_size=grid.CELL_SIZE):
        """Create a planner for the given grid dimensions.

        Args:
            grid_size (int): cells per side.
            cell_size (int): units per cell.
        """
        self.grid_size = grid_size
        self.cell_size = cell_size

    def plan(self, start, goal, speed=10):
        """Plan a route from ``start`` to ``goal``.

        Args:
            start (tuple): origin ``(x, y)``.
            goal (tuple): destination ``(x, y)``.
            speed (int): units per tick, used for the tick estimate.

        Returns:
            Route: the planned route including the origin.
        """
        sx, sy = int(start[0]), int(start[1])
        gx, gy = int(goal[0]), int(goal[1])
        if (sx, sy) == (gx, gy):
            points = [Location(sx, sy)]
        elif sx == gx or sy == gy:
            points = [Location(sx, sy), Location(gx, gy)]
        else:
            corner = (gx, sy)
            if not grid.is_street_point(*corner) and grid.is_street_point(sx, gy):
                corner = (sx, gy)
            points = [Location(sx, sy), Location(corner[0], corner[1]), Location(gx, gy)]

        total = 0
        for a, b in zip(points, points[1:]):
            total += abs(a.x - b.x) + abs(a.y - b.y)
        ticks = math.ceil(total / speed) if speed > 0 and total > 0 else 0
        logger.debug("Planned route %s -> %s length=%s", start, goal, total)
        return Route(points=points, total_distance=float(total), estimated_ticks=ticks)

    @staticmethod
    def is_directly_above_or_below(start, goal):
        """Return True when start and goal share an x coordinate but not y.

        This is the special case where the rider moves straight up or down.

        Args:
            start (tuple): origin ``(x, y)``.
            goal (tuple): destination ``(x, y)``.

        Returns:
            bool: True for a vertical-only move.
        """
        return start[0] == goal[0] and start[1] != goal[1]
