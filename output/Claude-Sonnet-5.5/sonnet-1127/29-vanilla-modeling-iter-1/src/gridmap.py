"""Grid map and coordinate helpers."""


class GridMap:
    """8x8 grid, 100x100 units per cell."""

    def __init__(self, width=800, height=800, cell_size=100):
        self.width = width
        self.height = height
        self.cell_size = cell_size

    @property
    def cols(self):
        return self.width // self.cell_size

    @property
    def rows(self):
        return self.height // self.cell_size

    def cell_of(self, x, y):
        """Return (col, row) of the cell containing the point (clamped)."""
        c = min(max(int(x) // self.cell_size, 0), self.cols - 1)
        r = min(max(int(y) // self.cell_size, 0), self.rows - 1)
        return c, r

    def to_center(self, x, y):
        """Convert a coordinate to the centre of its grid cell."""
        c, r = self.cell_of(x, y)
        half = self.cell_size // 2
        return c * self.cell_size + half, r * self.cell_size + half


GRID = GridMap()


def to_center(x, y):
    """Module level shortcut for GridMap.to_center."""
    return GRID.to_center(x, y)
