"""Grid geometry helpers for the 800x800 dispatch map.

The map is an 8x8 grid of 100x100 cells. Grid lines (coordinates that are
multiples of 100) are streets. The centre of every cell (coordinates of the
form 100k + 50) is a restaurant or customer location. Path planning runs on a
50-unit lattice so that every location is reachable as a graph node.
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_SIZE = 8
LATTICE_STEP = 50
CELL_OFFSET = CELL_SIZE // 2


def is_valid_coordinate(value):
    """Return True if ``value`` is an integer (not bool) within 0..MAP_SIZE.

    Args:
        value: Object to check.

    Returns:
        bool: Validity flag.
    """
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= MAP_SIZE


def clamp_coordinate(value):
    """Clamp a numeric coordinate into the 0..MAP_SIZE range.

    Args:
        value: Numeric coordinate (int or float).

    Returns:
        int: Clamped integer coordinate.
    """
    return max(0, min(MAP_SIZE, int(value)))


def to_cell_center_axis(value):
    """Convert one axis coordinate to the centre of its grid cell.

    Implements ``center = (value // 100) * 100 + 50`` with the index capped at
    the last cell so that the boundary value 800 maps to cell 7.

    Args:
        value: Coordinate on one axis (0..800).

    Returns:
        int: Cell-centre coordinate on that axis.
    """
    value = clamp_coordinate(value)
    index = min(value // CELL_SIZE, GRID_SIZE - 1)
    return index * CELL_SIZE + CELL_OFFSET


def to_grid_point(x, y):
    """Snap an (x, y) input point to the centre of its grid cell.

    Args:
        x: Input x coordinate.
        y: Input y coordinate.

    Returns:
        tuple: ``(center_x, center_y)`` integer pair.
    """
    return (to_cell_center_axis(x), to_cell_center_axis(y))


def is_street_point(x, y):
    """Return True if the point lies on a street (a grid line).

    Args:
        x: x coordinate.
        y: y coordinate.

    Returns:
        bool: True when x or y is a multiple of CELL_SIZE.
    """
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def is_location_point(x, y):
    """Return True if the point is a restaurant/customer cell centre.

    Args:
        x: x coordinate.
        y: y coordinate.

    Returns:
        bool: True when both coordinates are cell centres.
    """
    return x % CELL_SIZE == CELL_OFFSET and y % CELL_SIZE == CELL_OFFSET


def manhattan(a, b):
    """Return the Manhattan distance between two points.

    Args:
        a: Point as an (x, y) sequence.
        b: Point as an (x, y) sequence.

    Returns:
        int: ``|ax - bx| + |ay - by|``.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def path_length(points):
    """Return the total Manhattan length of a polyline of points.

    Args:
        points: Sequence of (x, y) points.

    Returns:
        int: Sum of consecutive Manhattan distances.
    """
    return sum(manhattan(points[i], points[i + 1]) for i in range(len(points) - 1))


def lattice_points():
    """Return every node of the 50-unit planning lattice.

    Returns:
        list[tuple]: All (x, y) pairs with coordinates in 0..MAP_SIZE, step 50.
    """
    return [(x, y)
            for x in range(0, MAP_SIZE + 1, LATTICE_STEP)
            for y in range(0, MAP_SIZE + 1, LATTICE_STEP)]


def road_lattice_points():
    """Return lattice nodes that lie on streets.

    Returns:
        list[tuple]: Road points suitable for initial rider placement.
    """
    return [p for p in lattice_points() if is_street_point(p[0], p[1])]
