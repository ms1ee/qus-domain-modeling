"""Grid map definition."""


class GridMap:
    """8x8 grid over an 800x800 coordinate system."""

    def __init__(self, width=800, height=800, cell_size=100):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.grid_dimension = width // cell_size

    def cell_index(self, v):
        """Return the grid index (0..7) of a coordinate."""
        return max(0, min(self.grid_dimension - 1, int(v) // self.cell_size))

    def center(self, v):
        """Return the cell-centre coordinate for a coordinate."""
        return self.cell_index(v) * self.cell_size + self.cell_size // 2

    def valid(self, v):
        """Check coordinate range 0-800."""
        return isinstance(v, int) and 0 <= v <= self.width


GRID = GridMap()
