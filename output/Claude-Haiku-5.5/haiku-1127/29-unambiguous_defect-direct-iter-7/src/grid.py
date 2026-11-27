"""Coordinate system helpers for the 800x800 delivery map.

The map is an 8x8 grid of 100x100 cells. Streets run along the lines where
x or y is a multiple of 100. Points at integer hundreds are street
intersections where restaurants, customers and riders are located.
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE      # 8 cells per axis
LATTICE_DIM = GRID_DIM + 1            # 9 street lines per axis
MIN_COORD = 0
MAX_COORD = MAP_SIZE


class CoordinateError(ValueError):
    """Raised when a coordinate is not an integer or lies outside the map."""


def validate_coordinate(value):
    """Check that ``value`` is an integer within the map bounds.

    Args:
        value: The coordinate to check.

    Returns:
        The validated integer coordinate.

    Raises:
        CoordinateError: If the value is not an integer or is out of range.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise CoordinateError(f"coordinate must be an integer, got {value!r}")
    if not MIN_COORD <= value <= MAX_COORD:
        raise CoordinateError(
            f"coordinate {value} is out of range {MIN_COORD}-{MAX_COORD}"
        )
    return value


def snap_axis(value):
    """Round one axis value to the nearest integer-hundred street line.

    Args:
        value: A numeric coordinate.

    Returns:
        An integer multiple of 100 within the map bounds.
    """
    value = max(MIN_COORD, min(MAX_COORD, int(value)))
    snapped = ((value + CELL_SIZE // 2) // CELL_SIZE) * CELL_SIZE
    return max(MIN_COORD, min(MAX_COORD, snapped))


def snap_to_grid(x, y):
    """Adjust a point to the nearest street intersection.

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.

    Returns:
        Tuple ``(x, y)`` of integer hundreds.
    """
    return snap_axis(x), snap_axis(y)


def cell_index(x, y):
    """Return the (column, row) index of the grid cell containing a point.

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.

    Returns:
        Tuple ``(column, row)`` with values in 0-7.
    """
    col = min(max(int(x) // CELL_SIZE, 0), GRID_DIM - 1)
    row = min(max(int(y) // CELL_SIZE, 0), GRID_DIM - 1)
    return col, row


def cell_center(x, y):
    """Return the center point of the cell containing a point.

    Uses ``center = (grid // 100) * 100 + 50`` for each axis.

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.

    Returns:
        Tuple ``(center_x, center_y)``.
    """
    col, row = cell_index(x, y)
    return col * CELL_SIZE + CELL_SIZE // 2, row * CELL_SIZE + CELL_SIZE // 2


def is_on_street(x, y):
    """Return True if the point lies on a street (grid line).

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.
    """
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def manhattan(a, b):
    """Return the Manhattan distance between two points.

    Args:
        a: Tuple ``(x, y)``.
        b: Tuple ``(x, y)``.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
