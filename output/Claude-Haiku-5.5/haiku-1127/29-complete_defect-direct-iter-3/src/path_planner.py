"""Grid-based path planning for the food delivery simulator.

The city is an 800x800 unit map divided into an 8x8 grid of 100x100 cells.
Streets are the centre lines of the cells (x or y equal to 50 + 100k), so
every cell centre is an intersection of two streets. Riders always travel
along streets using right-angle turns, which gives Manhattan-length routes.
"""

import logging
import math

logger = logging.getLogger(__name__)

MAP_SIZE = 800
GRID_SIZE = 8
CELL_SIZE = 100
CELL_CENTER_OFFSET = CELL_SIZE // 2
MAX_WAIT_TICKS = 3


def validate_coordinate(value, label="coordinate"):
    """Validate that ``value`` is an integer within the map range.

    Args:
        value: Candidate coordinate.
        label: Name used in error messages.

    Returns:
        The validated integer.

    Raises:
        TypeError: If ``value`` is not an integer (booleans are rejected).
        ValueError: If ``value`` is outside 0-800.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer, got {value!r}")
    if not 0 <= value <= MAP_SIZE:
        raise ValueError(f"{label} must be within 0-{MAP_SIZE}, got {value}")
    return value


def grid_index(value):
    """Return the grid index (0-7) of a map coordinate.

    Args:
        value: Coordinate in the range 0-800.

    Returns:
        Cell index along one axis. The value 800 maps to the last cell.
    """
    return min(value // CELL_SIZE, GRID_SIZE - 1)


def snap_to_center(value):
    """Convert a map coordinate to the centre of its grid cell.

    Implements ``center = (grid_x // 100) * 100 + 50`` with boundary handling.

    Args:
        value: Coordinate in the range 0-800.

    Returns:
        The centre coordinate of the containing cell along that axis.
    """
    return grid_index(value) * CELL_SIZE + CELL_CENTER_OFFSET


def cell_of(point):
    """Return the (column, row) grid cell containing ``point``.

    Args:
        point: Tuple ``(x, y)`` of map coordinates.

    Returns:
        Tuple ``(grid_x, grid_y)`` with values 0-7.
    """
    return grid_index(point[0]), grid_index(point[1])


def manhattan(a, b):
    """Return the Manhattan distance between two points.

    Because routes follow streets, this equals the true travelled length of
    a corner route between the two points.

    Args:
        a: Tuple ``(x, y)``.
        b: Tuple ``(x, y)``.

    Returns:
        Non-negative integer distance in map units.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def route_length(points):
    """Return the total travelled length along a list of waypoints.

    Args:
        points: Sequence of ``(x, y)`` waypoints connected by street segments.

    Returns:
        Sum of Manhattan lengths of consecutive segments.
    """
    return sum(manhattan(a, b) for a, b in zip(points, points[1:]))


def ticks_for_distance(distance, speed):
    """Return the number of ticks needed to travel ``distance`` units.

    Args:
        distance: Travel distance in map units.
        speed: Rider speed in units per tick (positive).

    Returns:
        Integer number of ticks (rounded up).
    """
    if distance <= 0:
        return 0
    return math.ceil(distance / speed)


class PathPlanner:
    """Computes street-following routes and single-tick movement steps.

    The planner prefers right-angle routes along streets. For every leg it
    considers the two corner routes (horizontal-first and vertical-first).
    When one route's destination of this tick is occupied by another rider,
    the alternative route is used. If both are blocked, the rider waits.
    """

    @staticmethod
    def corner_routes(start, goal):
        """Return the candidate street routes from ``start`` to ``goal``.

        Args:
            start: Tuple ``(x, y)`` of the current position.
            goal: Tuple ``(x, y)`` of the destination.

        Returns:
            List of waypoint lists. Each list ends with ``goal`` and contains
            one street corner. Horizontal-first route is listed first.
        """
        sx, sy = start
        gx, gy = goal
        horizontal_first = [(gx, sy), goal]
        vertical_first = [(sx, gy), goal]
        if horizontal_first == vertical_first:
            return [horizontal_first]
        return [horizontal_first, vertical_first]

    def plan_route(self, start, restaurant, customer):
        """Build the continuous route start -> restaurant -> customer.

        This is the multi-destination path used for display and ETA purposes.

        Args:
            start: Rider's current position.
            restaurant: Restaurant cell-centre position.
            customer: Customer cell-centre position.

        Returns:
            List of ``(x, y)`` points including corners, without duplicates.
        """
        points = [start]
        current = start
        for target in (restaurant, customer):
            for point in self.corner_routes(current, target)[0]:
                if point != points[-1]:
                    points.append(point)
            current = target
        return points

    @staticmethod
    def walk(start, waypoints, distance):
        """Move ``distance`` units along ``waypoints`` starting at ``start``.

        Args:
            start: Tuple ``(x, y)`` of the starting position.
            waypoints: Axis-aligned waypoints to follow in order.
            distance: Maximum number of units to travel.

        Returns:
            Tuple ``(x, y)`` of the position after travelling.
        """
        x, y = start
        remaining = distance
        for wx, wy in waypoints:
            if remaining <= 0:
                break
            seg = abs(wx - x) + abs(wy - y)
            if seg == 0:
                continue
            if remaining >= seg:
                x, y = wx, wy
                remaining -= seg
            else:
                if wx != x:
                    x += remaining if wx > x else -remaining
                else:
                    y += remaining if wy > y else -remaining
                remaining = 0
        return x, y

    def next_position(self, start, goal, speed, blocked=frozenset(),
                      ignore_block=False):
        """Compute the position reached after one tick of movement.

        Args:
            start: Tuple ``(x, y)`` current position.
            goal: Tuple ``(x, y)`` target position.
            speed: Units the rider may travel this tick.
            blocked: Set of positions occupied by other riders.
            ignore_block: When True, occupancy is ignored (deadlock breaking).

        Returns:
            Tuple ``(x, y, waiting)``. ``waiting`` is True when every route
            is blocked and the rider must stay where it is this tick.
        """
        if start == goal:
            return start[0], start[1], False
        for route in self.corner_routes(start, goal):
            candidate = self.walk(start, route, speed)
            if candidate == goal or ignore_block or candidate not in blocked:
                return candidate[0], candidate[1], False
        logger.debug("Rider at %s waiting: routes to %s are blocked",
                     start, goal)
        return start[0], start[1], True
