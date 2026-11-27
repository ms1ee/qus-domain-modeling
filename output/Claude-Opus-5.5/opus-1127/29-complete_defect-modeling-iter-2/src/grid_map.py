"""Grid map and coordinate conversion utilities."""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = 8


def clamp_coord(value):
    """Clamp a coordinate into the valid map range [0, MAP_SIZE]."""
    return max(0, min(MAP_SIZE, int(value)))


def to_grid_index(value):
    """Convert a raw coordinate into a grid index (0..GRID_DIM-1)."""
    idx = clamp_coord(value) // CELL_SIZE
    if idx >= GRID_DIM:
        idx = GRID_DIM - 1
    return idx


def to_cell_center(value):
    """Convert a raw coordinate into the center of its grid cell."""
    return to_grid_index(value) * CELL_SIZE + CELL_SIZE // 2


class GridCell:
    """A single 100x100 cell of the map."""

    def __init__(self, grid_x, grid_y):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.center_x = grid_x * CELL_SIZE + CELL_SIZE // 2
        self.center_y = grid_y * CELL_SIZE + CELL_SIZE // 2

    def __repr__(self):
        return "GridCell(%d, %d)" % (self.grid_x, self.grid_y)


class GridMap:
    """8x8 grid representing an 800x800 coordinate system."""

    def __init__(self, width=MAP_SIZE, height=MAP_SIZE, cell_size=CELL_SIZE):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.grid_dimension = width // cell_size
        self.cells = [[GridCell(gx, gy) for gx in range(self.grid_dimension)]
                      for gy in range(self.grid_dimension)]

    def cell_at(self, x, y):
        """Return the GridCell containing raw coordinates (x, y)."""
        return self.cells[to_grid_index(y)][to_grid_index(x)]

    def is_street(self, x, y):
        """True if (x, y) lies on a street (grid line)."""
        return x % self.cell_size == 0 or y % self.cell_size == 0
