"""Grid coordinate utilities for the 800x800 map.

The map is divided into an 8x8 grid of 100x100 unit cells.  Cell
``(gx, gy)`` covers the coordinates ``gx*100 .. gx*100+99``.  Order
locations are always snapped to the centre of their cell, computed as
``center = (value // 100) * 100 + 50``.

Streets: a cell is considered part of the street network when its column
index or its row index is odd.  Riders travel along these streets where
possible.
"""

import math

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = 8


def validate_coord(value, name="coordinate"):
    """Validate that ``value`` is an integer within the map range.

    Args:
        value (int): coordinate to validate.
        name (str): label used in error messages.

    Returns:
        int: the validated coordinate.

    Raises:
        TypeError: if ``value`` is not an integer.
        ValueError: if ``value`` lies outside 0-800.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer, got {value!r}")
    if not 0 <= value <= MAP_SIZE:
        raise ValueError(f"{name} must be in range 0-{MAP_SIZE}, got {value}")
    return value


def to_cell(value):
    """Return the grid index (0-7) containing a coordinate value.

    Values equal to 800 (the far map edge) are clamped into the last cell.

    Args:
        value (int): coordinate along one axis.

    Returns:
        int: grid index in the range 0 to ``GRID_DIM - 1``.
    """
    index = int(value) // CELL_SIZE
    return min(max(index, 0), GRID_DIM - 1)


def cell_center(value):
    """Return the centre coordinate of the cell containing ``value``.

    Implements ``center = (value // 100) * 100 + 50``.

    Args:
        value (int): coordinate along one axis.

    Returns:
        int: centre coordinate of the containing cell.
    """
    return to_cell(value) * CELL_SIZE + CELL_SIZE // 2


def to_grid_center(x, y):
    """Snap a raw coordinate pair to the centre of its grid cell.

    Args:
        x (int): raw x coordinate (0-800).
        y (int): raw y coordinate (0-800).

    Returns:
        tuple: ``(center_x, center_y)``.
    """
    return cell_center(x), cell_center(y)


def is_street_cell(gx, gy):
    """Return True if grid cell ``(gx, gy)`` belongs to the street network.

    Args:
        gx (int): column index.
        gy (int): row index.

    Returns:
        bool: True for odd column or odd row indices.
    """
    return gx % 2 == 1 or gy % 2 == 1


def is_street_point(x, y):
    """Return True if the raw coordinate ``(x, y)`` lies on a street cell.

    Args:
        x (int): x coordinate.
        y (int): y coordinate.

    Returns:
        bool: street membership of the containing cell.
    """
    return is_street_cell(to_cell(x), to_cell(y))


def manhattan(a, b):
    """Return the Manhattan distance between two points.

    Args:
        a (tuple): ``(x, y)`` point.
        b (tuple): ``(x, y)`` point.

    Returns:
        int: ``|ax - bx| + |ay - by|``.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def euclidean(a, b):
    """Return the Euclidean distance between two points.

    Args:
        a (tuple): ``(x, y)`` point.
        b (tuple): ``(x, y)`` point.

    Returns:
        float: straight-line distance.
    """
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
