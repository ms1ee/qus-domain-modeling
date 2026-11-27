"""Coordinate system and grid geometry helpers.

The map is 800x800 units divided into an 8x8 grid of 100x100 unit cells.
Orders and riders are placed on cell centers (coordinates ``50 + 100*k``).
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = 8
CELL_HALF = CELL_SIZE // 2


def validate_coordinate(value, name="coordinate"):
    """Validate a single integer coordinate.

    Args:
        value: Candidate coordinate.
        name: Label used in error messages.

    Returns:
        The validated integer.

    Raises:
        ValueError: If the value is not an integer or is outside 0-800.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    if not 0 <= value <= MAP_SIZE:
        raise ValueError(f"{name} {value} is out of range 0-{MAP_SIZE}")
    return value


def validate_point(point, name="point"):
    """Validate an ``[x, y]`` point.

    Args:
        point: Sequence of two integers.
        name: Label used in error messages.

    Returns:
        A tuple ``(x, y)`` of validated integers.

    Raises:
        ValueError: If the point is malformed or out of range.
    """
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        raise ValueError(f"{name} must be a pair of coordinates")
    x = validate_coordinate(point[0], f"{name} x")
    y = validate_coordinate(point[1], f"{name} y")
    return (x, y)


def cell_index(value):
    """Return the grid index (0-7) containing a coordinate.

    The value 800 (map edge) is mapped to the last cell, index 7.
    """
    return min(max(value // CELL_SIZE, 0), GRID_DIM - 1)


def cell_center(x, y):
    """Convert a raw coordinate to the center of its grid cell.

    Implements ``center_x = (grid_x // 100) * 100 + 50``.
    """
    return cell_to_point(cell_index(x), cell_index(y))


def cell_to_point(col, row):
    """Return the center point ``(x, y)`` of grid cell ``(col, row)``."""
    return (col * CELL_SIZE + CELL_HALF, row * CELL_SIZE + CELL_HALF)


def to_cell(point):
    """Return the ``(col, row)`` grid cell containing ``point``."""
    x, y = point
    return (cell_index(x), cell_index(y))


def is_cell_center(x, y):
    """Return True when ``(x, y)`` lies exactly on a cell center."""
    return x % CELL_SIZE == CELL_HALF and y % CELL_SIZE == CELL_HALF


def manhattan(a, b):
    """Return the Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def sign(value):
    """Return -1, 0 or 1 according to the sign of ``value``."""
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0
