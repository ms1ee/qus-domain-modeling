"""Grid map and coordinate conversion utilities."""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE


def clamp(value, low=0, high=MAP_SIZE):
    """Clamp ``value`` into the inclusive range [low, high]."""
    return max(low, min(high, value))


def cell_index(value):
    """Return the grid cell index (0..7) of a coordinate."""
    v = clamp(int(value))
    return min(v // CELL_SIZE, GRID_DIM - 1)


def to_grid_center(value):
    """Convert a coordinate to the centre of its grid cell.

    ``center = (v // 100) * 100 + 50``; the boundary value 800 maps to 750.
    """
    return cell_index(value) * CELL_SIZE + CELL_SIZE // 2


def nearest_street(value):
    """Return the street line (multiple of 100) nearest to ``value``."""
    line = int(round(value / float(CELL_SIZE))) * CELL_SIZE
    return clamp(line)


def is_street(value):
    """Return True if the coordinate lies on a street line."""
    return int(value) % CELL_SIZE == 0


class GridMap:
    """8x8 grid map description (800x800 units, 100x100 cells)."""

    def __init__(self, map_size=MAP_SIZE, cell_size=CELL_SIZE):
        self.map_size = map_size
        self.cell_size = cell_size
        self.grid_dimension = map_size // cell_size

    def to_cell_center(self, x, y):
        """Return the centre point of the cell containing (x, y)."""
        return to_grid_center(x), to_grid_center(y)

    def cell_of(self, x, y):
        """Return (col, row) cell indices of (x, y)."""
        return cell_index(x), cell_index(y)

    def in_bounds(self, x, y):
        """Return True if (x, y) is inside the map."""
        return 0 <= x <= self.map_size and 0 <= y <= self.map_size
