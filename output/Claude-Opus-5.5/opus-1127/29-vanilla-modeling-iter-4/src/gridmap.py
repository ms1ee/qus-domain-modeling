"""Grid map definitions and coordinate conversion helpers."""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE


def clamp_coord(value):
    """Convert ``value`` to int and clamp it into [0, MAP_SIZE].

    Raises:
        ValueError: if the value cannot be converted to an integer.
    """
    if isinstance(value, bool):
        raise ValueError("Boolean is not a valid coordinate")
    try:
        v = int(value)
    except (TypeError, ValueError):
        raise ValueError("Invalid coordinate: {!r}".format(value))
    return max(0, min(MAP_SIZE, v))


def to_cell_center(value):
    """Convert a coordinate to the centre of its grid cell.

    ``center = (v // 100) * 100 + 50``; the boundary value 800 maps to 750.
    """
    v = clamp_coord(value)
    center = (v // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2
    return min(center, MAP_SIZE - CELL_SIZE // 2)


def to_grid_point(x, y):
    """Convert a point to the centre point of its grid cell."""
    return to_cell_center(x), to_cell_center(y)


def cell_index(x, y):
    """Return (column, row) index of the cell containing the point."""
    col = min(GRID_DIM - 1, max(0, int(x) // CELL_SIZE))
    row = min(GRID_DIM - 1, max(0, int(y) // CELL_SIZE))
    return col, row


def is_street(x, y):
    """Return True if the point lies on a street (a grid line)."""
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


class GridMap:
    """8x8 grid map of an 800x800 coordinate system."""

    def __init__(self, map_size=MAP_SIZE, cell_size=CELL_SIZE):
        self.map_size = map_size
        self.cell_size = cell_size
        self.grid_dimension = map_size // cell_size

    def in_bounds(self, x, y):
        """Return True when the point lies inside the map."""
        return 0 <= x <= self.map_size and 0 <= y <= self.map_size

    def to_cell_center(self, value):
        """See :func:`to_cell_center`."""
        return to_cell_center(value)

    def is_street(self, x, y):
        """See :func:`is_street`."""
        return is_street(x, y)
