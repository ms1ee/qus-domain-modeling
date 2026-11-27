"""Coordinate helpers for the 8x8 grid (800x800 units, 100-unit cells).

Streets run along grid lines (x or y is a multiple of 100). Restaurant and
customer locations are cell centers (``cell * 100 + 50``). Each location is
served from the street intersection at the top-left corner of its cell
(the "access node"), which is always a multiple of 100 on both axes.
"""

import config


def is_valid_coordinate(value):
    """Return True when ``value`` is an ``int`` within the map bounds.

    Args:
        value: Candidate coordinate.

    Returns:
        bool: True if the value is an integer in ``[COORD_MIN, COORD_MAX]``.
    """
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and config.COORD_MIN <= value <= config.COORD_MAX
    )


def clamp_coordinate(value):
    """Clamp a numeric value into the map bounds and return an int.

    Args:
        value: Numeric coordinate (int or float).

    Returns:
        int: Value limited to ``[COORD_MIN, COORD_MAX]``.
    """
    return max(config.COORD_MIN, min(config.COORD_MAX, int(value)))


def cell_index(value):
    """Return the grid cell index (0-7) containing a coordinate.

    Values equal to the map edge (800) belong to the last cell.

    Args:
        value: Coordinate value.

    Returns:
        int: Cell index in ``[0, GRID_CELLS - 1]``.
    """
    clamped = min(clamp_coordinate(value), config.MAP_SIZE - 1)
    return clamped // config.CELL_SIZE


def snap_to_center(x, y):
    """Transform raw input coordinates to the center of their grid cell.

    Implements ``center = (grid // 100) * 100 + 50`` for both axes.

    Args:
        x: Raw x coordinate.
        y: Raw y coordinate.

    Returns:
        tuple[int, int]: Cell center coordinates.
    """
    center_x = cell_index(x) * config.CELL_SIZE + config.CELL_CENTER_OFFSET
    center_y = cell_index(y) * config.CELL_SIZE + config.CELL_CENTER_OFFSET
    return center_x, center_y


def access_node(point):
    """Return the street intersection serving the cell that contains ``point``.

    Args:
        point: ``(x, y)`` location (usually a cell center).

    Returns:
        tuple[int, int]: Intersection coordinates (both multiples of 100).
    """
    x, y = point
    return (
        cell_index(x) * config.CELL_SIZE,
        cell_index(y) * config.CELL_SIZE,
    )


def is_on_road(x, y):
    """Return True when the point lies on a street (grid line).

    Args:
        x: x coordinate.
        y: y coordinate.

    Returns:
        bool: True if ``x`` or ``y`` is a multiple of the cell size.
    """
    return x % config.CELL_SIZE == 0 or y % config.CELL_SIZE == 0


def snap_to_road(x, y):
    """Move an off-road point horizontally onto the nearest vertical street.

    Args:
        x: x coordinate.
        y: y coordinate.

    Returns:
        tuple[int, int]: A point that lies on a street.
    """
    x = clamp_coordinate(x)
    y = clamp_coordinate(y)
    if is_on_road(x, y):
        return x, y
    half = config.CELL_SIZE // 2
    street_x = min(config.MAP_SIZE, ((x + half) // config.CELL_SIZE) * config.CELL_SIZE)
    return street_x, y


def manhattan(a, b):
    """Return the Manhattan (street-following) distance between two points.

    Args:
        a: ``(x, y)`` point.
        b: ``(x, y)`` point.

    Returns:
        int: ``|ax - bx| + |ay - by|``.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
