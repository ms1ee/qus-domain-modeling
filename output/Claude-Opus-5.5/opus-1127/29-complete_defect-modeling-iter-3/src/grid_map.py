"""Grid map and coordinate conversion helpers (8x8 grid, 100x100 cells)."""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE


def validate_coordinate(value, name="coordinate"):
    """Validate an input coordinate: integer within 0..MAP_SIZE.

    Raises ValueError on invalid input.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0 or value > MAP_SIZE:
        raise ValueError("%s must be between 0 and %d, got %d"
                         % (name, MAP_SIZE, value))
    return value


def to_grid_index(value):
    """Convert a coordinate to its grid cell index (0..7). 800 maps to 7."""
    validate_coordinate(value)
    return min(value // CELL_SIZE, GRID_DIM - 1)


def to_cell_center(value):
    """Convert a coordinate to the center of its grid cell.

    ``center = (v // 100) * 100 + 50`` with the boundary 800 clamped to 750.
    """
    return to_grid_index(value) * CELL_SIZE + CELL_SIZE // 2


def is_on_street(x, y):
    """Return True if the point lies on a street (grid line)."""
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


class GridCell:
    """A single 100x100 cell of the map."""

    def __init__(self, grid_x, grid_y, symbol="."):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.center_x = grid_x * CELL_SIZE + CELL_SIZE // 2
        self.center_y = grid_y * CELL_SIZE + CELL_SIZE // 2
        self.symbol = symbol

    def __repr__(self):
        return "GridCell(%d, %d)" % (self.grid_x, self.grid_y)


class GridMap:
    """The 8x8 grid map containing 64 cells."""

    def __init__(self, map_size=MAP_SIZE, cell_size=CELL_SIZE):
        self.map_size = map_size
        self.cell_size = cell_size
        self.grid_dimension = map_size // cell_size
        self.cells = {(gx, gy): GridCell(gx, gy)
                      for gx in range(self.grid_dimension)
                      for gy in range(self.grid_dimension)}

    def cell_at(self, x, y):
        """Return the cell containing coordinate (x, y)."""
        return self.cells[(to_grid_index(x), to_grid_index(y))]
