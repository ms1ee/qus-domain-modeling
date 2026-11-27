"""Grid-based path planning for the 800x800 street map.

The map is divided into an 8x8 grid of 100x100 cells. Points whose x or y
coordinate is a multiple of 100 lie on streets. Movement is performed one
unit at a time along horizontal or vertical axes, which yields right-angle
turns and straight-line movement. Streets are preferred whenever the planner
has a choice between two axes.
"""

import logging
from typing import Iterable, List, Optional, Sequence, Set, Tuple

logger = logging.getLogger(__name__)

MAP_SIZE = 800
CELL_SIZE = 100
GRID_SIZE = MAP_SIZE // CELL_SIZE

Point = Tuple[int, int]


def to_cell_index(value: int) -> int:
    """Return the grid cell index (0-7) containing a coordinate.

    Coordinates equal to the map edge (800) are assigned to the last cell.

    Args:
        value: Coordinate value in units (0-800).

    Returns:
        Cell index in the range 0..GRID_SIZE-1.
    """
    return min(max(int(value) // CELL_SIZE, 0), GRID_SIZE - 1)


def to_cell_center(x: int, y: int) -> Point:
    """Convert a coordinate to the centre point of its grid cell.

    Implements ``center_x = (grid_x // 100) * 100 + 50``.

    Args:
        x: Input x coordinate (0-800).
        y: Input y coordinate (0-800).

    Returns:
        Tuple (center_x, center_y).
    """
    center_x = to_cell_index(x) * CELL_SIZE + CELL_SIZE // 2
    center_y = to_cell_index(y) * CELL_SIZE + CELL_SIZE // 2
    return center_x, center_y


class PathPlanner:
    """Computes unit-step routes on the street grid.

    Attributes:
        grid_size: Number of cells per side.
        cell_size: Size of one cell in units.
        map_size: Total map size in units.
    """

    def __init__(self, grid_size: int = GRID_SIZE, cell_size: int = CELL_SIZE) -> None:
        """Create a planner for a square grid.

        Args:
            grid_size: Number of cells per side.
            cell_size: Size of a cell in units.
        """
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.map_size = grid_size * cell_size

    def is_in_bounds(self, point: Point) -> bool:
        """Return True if the point lies inside the map."""
        x, y = point
        return 0 <= x <= self.map_size and 0 <= y <= self.map_size

    def is_on_street(self, point: Point) -> bool:
        """Return True if the point lies on a street (grid line)."""
        x, y = point
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def prefers_vertical(self, point: Point) -> bool:
        """Decide the preferred axis when both axes are possible.

        A rider standing on a vertical street (x on a grid line, y not on one)
        prefers to keep moving vertically; otherwise horizontal movement is
        preferred.

        Args:
            point: Current position.

        Returns:
            True if vertical movement should be tried first.
        """
        x, y = point
        return x % self.cell_size == 0 and y % self.cell_size != 0

    def candidate_moves(self, position: Point, target: Point,
                        prefer_vertical: bool = False) -> List[Point]:
        """List the unit moves that reduce the distance to the target.

        Special cases:
            * Same x as target (directly above or below): vertical only.
            * Same y as target (directly left or right): horizontal only.

        Args:
            position: Current position.
            target: Destination position.
            prefer_vertical: Whether vertical moves are tried first.

        Returns:
            Ordered list of candidate next points (most preferred first).
        """
        x, y = position
        tx, ty = target
        if (x, y) == (tx, ty):
            return []
        sx = (tx > x) - (tx < x)
        sy = (ty > y) - (ty < y)
        if x == tx:
            return [(x, y + sy)]
        if y == ty:
            return [(x + sx, y)]
        horizontal = (x + sx, y)
        vertical = (x, y + sy)
        if prefer_vertical:
            return [vertical, horizontal]
        return [horizontal, vertical]

    def next_step(self, position: Point, target: Point,
                  occupied: Optional[Set[Point]] = None,
                  prefer_vertical: Optional[bool] = None) -> Optional[Point]:
        """Return the next unit position toward the target.

        Args:
            position: Current position.
            target: Destination position.
            occupied: Points that other riders occupy (avoided to prevent conflicts).
            prefer_vertical: Axis preference; computed from the street layout if None.

        Returns:
            The next point, or None if every useful move is blocked.
        """
        if prefer_vertical is None:
            prefer_vertical = self.prefers_vertical(position)
        for candidate in self.candidate_moves(position, target, prefer_vertical):
            if not self.is_in_bounds(candidate):
                continue
            if occupied and candidate in occupied:
                continue
            return candidate
        return None

    def plan_path(self, start: Sequence[int], target: Sequence[int],
                  occupied: Optional[Iterable[Point]] = None) -> List[Point]:
        """Compute the list of unit points from start to target.

        The start point is excluded from the result. Without occupancy
        information the path always reaches the target.

        Args:
            start: Starting coordinates.
            target: Destination coordinates.
            occupied: Optional set of blocked points.

        Returns:
            List of points visited in order (ending at target if reachable).
        """
        blocked = set(occupied) if occupied is not None else None
        pos = (int(start[0]), int(start[1]))
        goal = (int(target[0]), int(target[1]))
        path: List[Point] = []
        while pos != goal:
            nxt = self.next_step(pos, goal, blocked)
            if nxt is None:
                logger.debug("Path from %s to %s blocked at %s", start, target, pos)
                break
            path.append(nxt)
            pos = nxt
        return path

    def plan_route(self, start: Sequence[int], restaurant: Sequence[int],
                   customer: Sequence[int]) -> List[Point]:
        """Plan the continuous route start -> restaurant -> customer.

        Args:
            start: Rider position.
            restaurant: Restaurant grid centre.
            customer: Customer grid centre.

        Returns:
            Concatenated list of route points.
        """
        to_restaurant = self.plan_path(start, restaurant)
        to_customer = self.plan_path(restaurant, customer)
        return to_restaurant + to_customer
