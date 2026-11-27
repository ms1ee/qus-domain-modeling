"""Grid-based street path planning for the food delivery simulator.

The map is 800x800 units divided into 8x8 cells of 100x100 units. Any point
whose x or y coordinate is a multiple of 100 lies on a street. Points where
both coordinates are multiples of 100 are intersections; order locations are
snapped to the top-left corner of their grid cell, which is always such an
intersection.

Deadlock avoidance: riders never block one another. Each tick a rider moves
unconditionally along a street toward its target, so every rider makes
progress and no waiting cycle can form.
"""

import logging
import math

logger = logging.getLogger(__name__)

MAP_SIZE = 800
CELL_SIZE = 100
GRID_CELLS = 8
COORD_MIN = 0
COORD_MAX = 1000


def is_valid_coordinate(value):
    """Return True when ``value`` is an int within the accepted range.

    Args:
        value: Candidate coordinate.

    Returns:
        bool: True if the value is an integer in ``[0, 1000]``.
    """
    return (isinstance(value, int) and not isinstance(value, bool)
            and COORD_MIN <= value <= COORD_MAX)


def snap_to_grid(value):
    """Return the top-left coordinate of the grid cell containing ``value``.

    Values beyond the map edge are clamped to the last cell.

    Args:
        value: Coordinate in range 0-1000.

    Returns:
        int: ``(value // 100) * 100`` clamped to the 8x8 grid.
    """
    index = min(max(int(value) // CELL_SIZE, 0), GRID_CELLS - 1)
    return index * CELL_SIZE


def cell_center(value):
    """Return the centre coordinate of the grid cell containing ``value``.

    Args:
        value: Coordinate in range 0-1000.

    Returns:
        int: ``(grid_x // 100) * 100 + 50``.
    """
    return snap_to_grid(value) + CELL_SIZE // 2


def is_on_street(x, y):
    """Return True if the point lies on a street grid line.

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        bool: True when x or y is a multiple of the cell size.
    """
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def manhattan_distance(x1, y1, x2, y2):
    """Return the Manhattan (grid) distance between two points.

    Args:
        x1, y1: First point.
        x2, y2: Second point.

    Returns:
        int: ``|x1 - x2| + |y1 - y2|``.
    """
    return abs(x1 - x2) + abs(y1 - y2)


def euclidean_distance(x1, y1, x2, y2):
    """Return the straight-line distance between two points.

    Args:
        x1, y1: First point.
        x2, y2: Second point.

    Returns:
        float: ``sqrt((x1 - x2)^2 + (y1 - y2)^2)``.
    """
    return math.hypot(x1 - x2, y1 - y2)


class PathPlanner:
    """Plans street-following movement on the grid.

    Movement always prefers streets: when a rider is on a horizontal street it
    travels horizontally first, otherwise it travels vertically along the
    vertical street it occupies. A rider directly above or below its target
    moves straight along the column.
    """

    def __init__(self, cell_size=CELL_SIZE, map_size=MAP_SIZE):
        """Create a planner.

        Args:
            cell_size: Size of one grid cell in units.
            map_size: Size of the map in units.
        """
        self.cell_size = cell_size
        self.map_size = map_size

    def next_step(self, x, y, target_x, target_y, speed):
        """Advance a position by up to ``speed`` units along streets.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            target_x: Target x coordinate.
            target_y: Target y coordinate.
            speed: Maximum distance (units) to travel this tick.

        Returns:
            tuple[int, int]: The new ``(x, y)`` position.

        Raises:
            ValueError: If speed is not positive.
        """
        if speed <= 0:
            raise ValueError("speed must be positive")
        budget = int(speed)
        while budget > 0 and (x, y) != (target_x, target_y):
            if x == target_x:
                # Directly above or below the target: straight vertical move.
                step = min(budget, abs(target_y - y))
                y += step if target_y > y else -step
            elif y == target_y:
                # Same row as the target: straight horizontal move.
                step = min(budget, abs(target_x - x))
                x += step if target_x > x else -step
            elif y % self.cell_size == 0:
                # On a horizontal street: travel along it first.
                step = min(budget, abs(target_x - x))
                x += step if target_x > x else -step
            else:
                # On a vertical street: travel along it first.
                step = min(budget, abs(target_y - y))
                y += step if target_y > y else -step
            budget -= step
        return x, y

    def plan_route(self, x, y, target_x, target_y):
        """Return the corner points of the street route to a target.

        The route follows the same axis preference as :meth:`next_step`.

        Args:
            x: Start x coordinate.
            y: Start y coordinate.
            target_x: Target x coordinate.
            target_y: Target y coordinate.

        Returns:
            list[tuple[int, int]]: Start, corner (if any) and target points.
        """
        if y % self.cell_size == 0:
            corner = (target_x, y)
        else:
            corner = (x, target_y)
        points = [(x, y)]
        for point in (corner, (target_x, target_y)):
            if point != points[-1]:
                points.append(point)
        return points

    @staticmethod
    def path_length(points):
        """Return the total Manhattan length of a polyline.

        Args:
            points: Sequence of ``(x, y)`` tuples.

        Returns:
            int: Sum of Manhattan lengths of consecutive segments.
        """
        total = 0
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            total += manhattan_distance(x1, y1, x2, y2)
        return total
