"""Grid geometry helpers for the 800x800 map.

The map is an 8x8 grid of 100x100 unit cells. Riders, restaurants and
customers are always placed at cell centers, computed as
``(coordinate // 100) * 100 + 50``.
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = 8
CELL_HALF = 50
COORD_MIN = 0
COORD_MAX = MAP_SIZE


def validate_coordinate(value):
    """Validate a single integer coordinate.

    Args:
        value: The coordinate value to validate.

    Returns:
        int: The validated coordinate.

    Raises:
        TypeError: If ``value`` is not an integer (booleans are rejected).
        ValueError: If ``value`` lies outside the range 0-800.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"coordinate {value!r} is not an integer")
    if not COORD_MIN <= value <= COORD_MAX:
        raise ValueError(
            f"coordinate {value} is out of range {COORD_MIN}-{COORD_MAX}"
        )
    return value


def cell_index(value):
    """Return the grid index (0-7) that contains a coordinate value.

    Abnormal values are clamped into the map. The far boundary value 800 is
    mapped into the last cell.

    Args:
        value: Coordinate in units (0-800).

    Returns:
        int: Grid index between 0 and 7 inclusive.
    """
    clamped = min(max(int(value), COORD_MIN), MAP_SIZE - 1)
    return clamped // CELL_SIZE


def cell_center(x, y):
    """Convert a coordinate pair to the center point of its grid cell.

    Args:
        x: Horizontal coordinate in units.
        y: Vertical coordinate in units.

    Returns:
        tuple[int, int]: The cell center ``(center_x, center_y)``.
    """
    return (cell_index(x) * CELL_SIZE + CELL_HALF,
            cell_index(y) * CELL_SIZE + CELL_HALF)


def cell_of(x, y):
    """Return the grid cell indices ``(gx, gy)`` of a coordinate pair."""
    return (cell_index(x), cell_index(y))


def manhattan(a, b):
    """Return the Manhattan distance between two points.

    Args:
        a: Point ``(x, y)``.
        b: Point ``(x, y)``.

    Returns:
        int: Sum of absolute axis differences.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def path_length(start, points):
    """Return the total Manhattan length of a poly-line.

    Args:
        start: Starting point ``(x, y)``.
        points: Ordered list of waypoints ``(x, y)`` following ``start``.

    Returns:
        int: Total travelled distance in units.
    """
    total = 0
    current = start
    for point in points:
        total += manhattan(current, point)
        current = point
    return total
