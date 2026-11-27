"""Grid map and coordinate conversion utilities.

The map is 800x800 units divided into an 8x8 grid of 100x100 cells.
Grid lines (x or y a multiple of 100) are streets.
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE


def clamp_coord(value):
    """Clamp a coordinate into the valid range 0..MAP_SIZE."""
    return max(0, min(MAP_SIZE, int(value)))


def to_grid_index(value):
    """Convert a raw coordinate into a grid index 0..GRID_DIM-1.

    The boundary value 800 belongs to the last cell (index 7).
    """
    value = clamp_coord(value)
    return min(value // CELL_SIZE, GRID_DIM - 1)


def to_cell_center(value):
    """Convert a raw coordinate into the coordinate of its cell center.

    ``center = (v // 100) * 100 + 50`` with boundary handling for 800.
    """
    return to_grid_index(value) * CELL_SIZE + CELL_SIZE // 2


def to_cell_center_point(pos):
    """Convert an ``(x, y)`` point to its cell center point."""
    return (to_cell_center(pos[0]), to_cell_center(pos[1]))


def to_grid_point(pos):
    """Convert an ``(x, y)`` point to its ``(grid_x, grid_y)`` indices."""
    return (to_grid_index(pos[0]), to_grid_index(pos[1]))


def is_street(x, y):
    """Return True if the point lies on a street (a grid line)."""
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

    def __init__(self, width=MAP_SIZE, height=MAP_SIZE, cell_size=CELL_SIZE):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.grid_dimension = width // cell_size
        self.cells = [[GridCell(gx, gy) for gx in range(self.grid_dimension)]
                      for gy in range(self.grid_dimension)]

    def cell_at(self, x, y):
        """Return the cell containing raw coordinate ``(x, y)``."""
        return self.cells[to_grid_index(y)][to_grid_index(x)]

    def all_cells(self):
        """Return a flat list of all cells."""
        return [c for row in self.cells for c in row]
