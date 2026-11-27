"""8x8 grid map over an 800x800 coordinate system.

Streets run along grid lines (x or y a multiple of 100).  Restaurants and
customers are located at cell centres (``(v // 100) * 100 + 50``).
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE


def clamp(value, low=0, high=MAP_SIZE):
    """Clamp ``value`` into [low, high]."""
    return max(low, min(high, value))


def to_cell_center(value):
    """Convert one raw coordinate to the centre of its grid cell."""
    value = clamp(int(value))
    center = (value // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2
    return min(center, MAP_SIZE - CELL_SIZE // 2)


def to_grid_point(pos):
    """Convert an (x, y) pair to the centre of the containing cell."""
    return (to_cell_center(pos[0]), to_cell_center(pos[1]))


def is_street(x, y):
    """True if the point lies on a street (grid line)."""
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def cell_index(x, y):
    """Return the (column, row) grid cell index of a point."""
    return (min(int(x) // CELL_SIZE, GRID_DIM - 1),
            min(int(y) // CELL_SIZE, GRID_DIM - 1))


class GridMap:
    """Description of the map geometry."""

    def __init__(self):
        self.width = MAP_SIZE
        self.height = MAP_SIZE
        self.cell_size = CELL_SIZE
        self.grid_dimension = GRID_DIM

    def in_bounds(self, x, y):
        """True if the point lies inside the map."""
        return 0 <= x <= self.width and 0 <= y <= self.height

    @staticmethod
    def to_grid_point(pos):
        return to_grid_point(pos)

    @staticmethod
    def is_street(x, y):
        return is_street(x, y)
