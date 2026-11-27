"""Grid-based path planning for the food delivery simulator.

The map is 800x800 units divided into an 8x8 grid of 100x100 cells. Streets
are the grid lines (coordinates that are multiples of 100). Restaurants and
customers sit on street intersections. Movement always follows streets:
straight lines plus right-angle turns at intersections.
"""

import logging
import math

GRID_SIZE = 8
CELL_SIZE = 100
MAP_SIZE = GRID_SIZE * CELL_SIZE

logger = logging.getLogger(__name__)


def clamp(value, low, high):
    """Clamp ``value`` into the inclusive range [low, high]."""
    return max(low, min(high, value))


def to_cell_corner(x, y):
    """Convert a raw map coordinate to the top-left corner of its grid cell.

    Coordinates are clamped to the map boundary first, so abnormal values
    (negative or above 800) are handled safely.

    Args:
        x: Raw x coordinate.
        y: Raw y coordinate.

    Returns:
        Tuple ``(x, y)`` of integers, both multiples of 100 within 0-800.
    """
    x = clamp(int(x), 0, MAP_SIZE)
    y = clamp(int(y), 0, MAP_SIZE)
    return ((x // CELL_SIZE) * CELL_SIZE, (y // CELL_SIZE) * CELL_SIZE)


def grid_cell_center(x, y):
    """Return the centre point of the grid cell containing ``(x, y)``.

    Uses ``center_x = (grid_x // 100) * 100 + 50`` as specified in the PRD.
    """
    x = clamp(int(x), 0, MAP_SIZE - 1)
    y = clamp(int(y), 0, MAP_SIZE - 1)
    return ((x // CELL_SIZE) * CELL_SIZE + 50, (y // CELL_SIZE) * CELL_SIZE + 50)


class PathPlanner:
    """Plans and advances movement along the street grid.

    Attributes:
        grid_size (int): Number of cells per side (8).
        cell_size (int): Size of one cell in map units (100).
        map_size (int): Total map size in map units (800).
    """

    def __init__(self, grid_size=GRID_SIZE, cell_size=CELL_SIZE):
        """Create a planner for a square grid.

        Args:
            grid_size: Number of cells along each axis.
            cell_size: Edge length of a single cell in map units.
        """
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.map_size = grid_size * cell_size

    def is_on_street(self, x, y):
        """Return True when the point lies on a street (a grid line)."""
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def next_position(self, current, target, speed):
        """Advance from ``current`` toward ``target`` by at most ``speed`` units.

        Rules:
            * If the rider is on a vertical street (x on a grid line) and not
              yet level with the target, it moves vertically first.
            * Otherwise it moves horizontally along the current street.
            * Once the x coordinate matches the target, it moves vertically
              along the target's street. This produces right-angle turns only
              at intersections and never leaves the street network.

        Args:
            current: ``(x, y)`` current position.
            target: ``(x, y)`` destination.
            speed: Maximum distance to travel this tick.

        Returns:
            New ``(x, y)`` position after the move.
        """
        x, y = current
        tx, ty = target
        remaining = max(0, int(speed))
        cs = self.cell_size

        while remaining > 0 and (x, y) != (tx, ty):
            if x % cs == 0 and y != ty:
                # Special case: directly above/below or on a vertical street.
                step = min(remaining, abs(ty - y))
                y += step if ty > y else -step
            elif x != tx:
                step = min(remaining, abs(tx - x))
                x += step if tx > x else -step
            else:  # pragma: no cover - unreachable for street-aligned targets
                logger.warning("Off-street target %s from %s", target, current)
                break
            remaining -= step
        return (x, y)

    def plan_route(self, start, end):
        """Compute a street-following route from ``start`` to ``end``.

        The route contains at most one right-angle turn and is returned as a
        list of waypoints including both endpoints.

        Args:
            start: ``(x, y)`` starting point.
            end: ``(x, y)`` destination.

        Returns:
            List of ``(x, y)`` waypoints.
        """
        sx, sy = start
        ex, ey = end
        if sx % self.cell_size == 0:
            corner = (sx, ey)
        else:
            corner = (ex, sy)
        points = [(sx, sy)]
        for point in (corner, (ex, ey)):
            if point != points[-1]:
                points.append(point)
        return points

    @staticmethod
    def route_length(points):
        """Return the total Manhattan length of a list of waypoints."""
        total = 0
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            total += abs(x2 - x1) + abs(y2 - y1)
        return total

    @staticmethod
    def estimate_ticks(distance, speed):
        """Return the number of ticks needed to cover ``distance`` at ``speed``."""
        if speed <= 0:
            return 0
        return int(math.ceil(distance / speed))
