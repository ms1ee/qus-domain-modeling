"""Grid map and coordinate conversion utilities (8x8 grid of 100x100 cells)."""

MAP_SIZE = 800
CELL_SIZE = 100


def clamp_coordinate(value, map_size=MAP_SIZE):
    """Clamp a coordinate into [0, map_size]."""
    value = int(value)
    return max(0, min(map_size, value))


def to_grid_index(value, cell_size=CELL_SIZE, map_size=MAP_SIZE):
    """Convert a raw coordinate into a grid cell index (0..7)."""
    value = clamp_coordinate(value, map_size)
    max_index = map_size // cell_size - 1
    return min(value // cell_size, max_index)


def to_cell_center(value, cell_size=CELL_SIZE, map_size=MAP_SIZE):
    """Convert a raw coordinate to the center of its grid cell.

    ``center = (v // 100) * 100 + 50`` with the boundary value 800 mapped
    into the last cell.
    """
    return to_grid_index(value, cell_size, map_size) * cell_size + cell_size // 2


class GridCell:
    """One cell of the grid."""

    def __init__(self, grid_x, grid_y, cell_size=CELL_SIZE):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.center_x = grid_x * cell_size + cell_size // 2
        self.center_y = grid_y * cell_size + cell_size // 2

    def __repr__(self):
        return "GridCell(%d, %d)" % (self.grid_x, self.grid_y)


class GridMap:
    """The whole map: 800x800 units split into 8x8 cells."""

    def __init__(self, width=MAP_SIZE, height=MAP_SIZE, cell_size=CELL_SIZE):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.columns = width // cell_size
        self.rows = height // cell_size
        self.cells = {(gx, gy): GridCell(gx, gy, cell_size)
                      for gx in range(self.columns) for gy in range(self.rows)}

    def cell_at(self, x, y):
        """Return the GridCell containing (x, y)."""
        gx = to_grid_index(x, self.cell_size, self.width)
        gy = to_grid_index(y, self.cell_size, self.height)
        return self.cells[(gx, gy)]

    def in_bounds(self, x, y):
        """Return True if (x, y) is inside the map."""
        return 0 <= x <= self.width and 0 <= y <= self.height

    def is_street(self, x, y):
        """Streets are the grid lines (x or y multiple of the cell size)."""
        return x % self.cell_size == 0 or y % self.cell_size == 0
