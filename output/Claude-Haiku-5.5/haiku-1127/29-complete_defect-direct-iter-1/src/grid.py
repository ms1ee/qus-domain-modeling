"""Coordinate helpers for the 8x8 grid representing an 800x800 map."""

import config


def is_valid_coordinate(value):
    """Check that a value is an integer within the map range 0-800.

    Args:
        value: Candidate coordinate.

    Returns:
        bool: True if the value is a valid integer coordinate.
    """
    return (isinstance(value, int) and not isinstance(value, bool)
            and 0 <= value <= config.MAP_SIZE)


def cell_index(value):
    """Return the grid cell index (0-7) that contains a coordinate.

    Coordinates equal to the map edge (800) are clamped into the last cell.

    Args:
        value: Coordinate in units (0-800).

    Returns:
        int: Cell index along one axis.
    """
    index = value // config.CELL_SIZE
    return min(max(index, 0), config.GRID_SIZE - 1)


def to_grid_center(value):
    """Convert a coordinate to the center of its grid cell.

    Implements ``center = (value // 100) * 100 + 50`` with clamping so the
    map edge (800) maps to the center of the last cell (750).

    Args:
        value: Coordinate in units (0-800).

    Returns:
        int: Center coordinate along one axis.
    """
    return cell_index(value) * config.CELL_SIZE + config.NODE_OFFSET


def to_grid_point(x, y):
    """Convert a raw (x, y) position to grid cell center coordinates.

    Args:
        x: Raw x coordinate.
        y: Raw y coordinate.

    Returns:
        tuple[int, int]: Cell-center coordinates.
    """
    return (to_grid_center(x), to_grid_center(y))


def manhattan(a, b):
    """Return the Manhattan distance between two points.

    Args:
        a: First point as (x, y).
        b: Second point as (x, y).

    Returns:
        int: Manhattan distance, which equals the street-travel distance.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def is_street_point(x, y):
    """Return True if a point lies on a street (center line of a cell row/column).

    Args:
        x: x coordinate.
        y: y coordinate.

    Returns:
        bool: True if the point is on a street line.
    """
    return x % config.CELL_SIZE == config.NODE_OFFSET or \
        y % config.CELL_SIZE == config.NODE_OFFSET
