"""Grid map definition."""


class GridMap:
    """8x8 grid, 100 unit cells, 800x800 coordinate system."""

    def __init__(self, width=800, height=800, cell_size=100):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.grid_dimension = width // cell_size

    def cell_of(self, x, y):
        """Return (col,row) cell index of a coordinate, clamped."""
        d = self.grid_dimension - 1
        cx = min(max(int(x) // self.cell_size, 0), d)
        cy = min(max(int(y) // self.cell_size, 0), d)
        return cx, cy

    def center_of(self, x, y):
        """Return the center point of the cell containing (x, y)."""
        cx, cy = self.cell_of(x, y)
        return cx * self.cell_size + self.cell_size // 2, \
            cy * self.cell_size + self.cell_size // 2

    def in_range(self, v):
        return 0 <= v <= self.width
