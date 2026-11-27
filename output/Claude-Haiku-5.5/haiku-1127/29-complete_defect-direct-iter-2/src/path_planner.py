"""Grid-based path planning on the 8x8 street map.

The map is an 800x800 unit plane divided into 8x8 cells of 100x100 units.
Streets run along the grid lines, i.e. coordinates that are multiples of
100. Routes are built from axis-aligned legs (straight horizontal or vertical
movement with right-angle turns). When two corner choices are possible, the
planner prefers the corner whose legs lie along streets.
"""

import math

from config import CELL_SIZE, GRID_SIZE, MAP_SIZE


def is_valid_coordinate(value):
    """Return True if value is an integer within the map range.

    Args:
        value: Value to check.

    Returns:
        True when value is an int (not bool) in 0..800 inclusive.
    """
    return (isinstance(value, int) and not isinstance(value, bool)
            and 0 <= value <= MAP_SIZE)


def cell_index(x, y):
    """Return the (column, row) grid cell containing a coordinate.

    Out-of-range values are clamped to the nearest valid cell, so 800 maps
    to the last cell.

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.

    Returns:
        Tuple ``(col, row)`` with values in 0..7.
    """
    col = min(max(int(x), 0) // CELL_SIZE, GRID_SIZE - 1)
    row = min(max(int(y), 0) // CELL_SIZE, GRID_SIZE - 1)
    return col, row


def to_cell_center(x, y):
    """Convert a coordinate to the center point of its grid cell.

    Uses ``center = (grid // 100) * 100 + 50`` on each axis.

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.

    Returns:
        Tuple ``(center_x, center_y)`` of integers.
    """
    col, row = cell_index(x, y)
    half = CELL_SIZE // 2
    return (col * CELL_SIZE + half, row * CELL_SIZE + half)


def is_on_street(x, y):
    """Return True if a point lies on a street (a grid line).

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.

    Returns:
        True if x or y is a multiple of the cell size.
    """
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def manhattan(point_a, point_b):
    """Return the Manhattan (street-grid) distance between two points.

    Args:
        point_a: Tuple ``(x, y)``.
        point_b: Tuple ``(x, y)``.

    Returns:
        Integer distance in units.
    """
    return abs(point_a[0] - point_b[0]) + abs(point_a[1] - point_b[1])


def _leg_on_street(start, end):
    """Return True if an axis-aligned leg runs along a street.

    Args:
        start: Tuple ``(x, y)`` at the beginning of the leg.
        end: Tuple ``(x, y)`` at the end of the leg.

    Returns:
        True if the fixed coordinate of the leg is on a grid line.
    """
    if start[1] == end[1]:
        return start[1] % CELL_SIZE == 0
    return start[0] % CELL_SIZE == 0


class PathPlanner:
    """Plans right-angle routes between points on the street grid."""

    def plan(self, start, goal):
        """Plan a route from start to goal.

        A point directly above, below, or beside the goal is reached with a
        single straight leg (special case). Otherwise one right-angle corner
        is used, preferring the corner whose legs run along streets.

        Args:
            start: Tuple ``(x, y)`` of the current position.
            goal: Tuple ``(x, y)`` of the destination.

        Returns:
            List of waypoints after start, ending at goal. Empty if the
            start already equals the goal.
        """
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return []
        if start[0] == goal[0] or start[1] == goal[1]:
            return [goal]

        corners = ((goal[0], start[1]), (start[0], goal[1]))
        best_corner = corners[0]
        best_score = -1
        for corner in corners:
            score = (int(_leg_on_street(start, corner))
                     + int(_leg_on_street(corner, goal)))
            if score > best_score:
                best_score = score
                best_corner = corner
        return [best_corner, goal]

    def plan_route(self, start, destinations):
        """Plan one continuous route through several destinations in order.

        Used for the continuous restaurant-to-customer path.

        Args:
            start: Tuple ``(x, y)`` of the starting position.
            destinations: Ordered list of ``(x, y)`` destinations.

        Returns:
            Combined list of waypoints (excluding start).
        """
        waypoints = []
        current = (int(start[0]), int(start[1]))
        for destination in destinations:
            waypoints.extend(self.plan(current, destination))
            current = (int(destination[0]), int(destination[1]))
        return waypoints


def path_length(start, waypoints):
    """Return the total travel distance along a list of waypoints.

    Args:
        start: Tuple ``(x, y)`` of the starting position.
        waypoints: List of ``(x, y)`` waypoints in travel order.

    Returns:
        Integer total distance in units.
    """
    total = 0
    current = start
    for point in waypoints:
        total += manhattan(current, point)
        current = point
    return total


def estimate_ticks(length, speed):
    """Estimate the number of ticks needed to cover a distance.

    Args:
        length: Distance in units.
        speed: Rider speed in units per tick (must be positive).

    Returns:
        Integer number of ticks (rounded up).

    Raises:
        ValueError: If speed is not positive.
    """
    if speed <= 0:
        raise ValueError("speed must be positive")
    return math.ceil(length / speed)
