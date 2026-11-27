"""Grid geometry for the 800x800 food delivery dispatch map.

The map is an 8x8 grid of 100x100 unit cells. Streets run along the grid
lines, meaning a point is on a road when its x or y coordinate is a multiple
of 100. Points where both coordinates are multiples of 100 are intersections,
and they are the only valid restaurant and customer locations.
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE  # 8 cells per side

INTERSECTIONS = tuple(
    (x, y)
    for x in range(0, MAP_SIZE + 1, CELL_SIZE)
    for y in range(0, MAP_SIZE + 1, CELL_SIZE)
)


def clamp(value, low=0, high=MAP_SIZE):
    """Clamp ``value`` into the inclusive range [low, high].

    Args:
        value: The number to clamp.
        low: Lower bound (inclusive).
        high: Upper bound (inclusive).

    Returns:
        int: The clamped value.
    """
    return max(low, min(high, int(value)))


def snap_to_grid(value):
    """Snap a coordinate to the nearest multiple of ``CELL_SIZE``.

    The result is clamped to the map bounds so it always lies on a valid
    grid line between 0 and ``MAP_SIZE``.

    Args:
        value: Raw coordinate value.

    Returns:
        int: Snapped coordinate.
    """
    value = int(value)
    snapped = ((value + CELL_SIZE // 2) // CELL_SIZE) * CELL_SIZE
    return clamp(snapped)


def is_in_bounds(x, y):
    """Return True if the point lies inside the map bounds.

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        bool: Whether the point is within 0..MAP_SIZE on both axes.
    """
    return 0 <= x <= MAP_SIZE and 0 <= y <= MAP_SIZE


def is_road(x, y):
    """Return True if the point lies on a street (a grid line).

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        bool: True when the point is in bounds and on a grid line.
    """
    return is_in_bounds(x, y) and (x % CELL_SIZE == 0 or y % CELL_SIZE == 0)


def is_intersection(x, y):
    """Return True if the point is a grid intersection (restaurant/customer spot).

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        bool: True when both coordinates are multiples of ``CELL_SIZE``.
    """
    return is_in_bounds(x, y) and x % CELL_SIZE == 0 and y % CELL_SIZE == 0


def manhattan(a, b):
    """Return the Manhattan distance between two points.

    Args:
        a: Tuple (x, y).
        b: Tuple (x, y).

    Returns:
        int: |ax - bx| + |ay - by|.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
