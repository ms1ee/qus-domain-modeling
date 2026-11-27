"""Grid map definition."""


class GridMap:
    """8x8 grid, 800x800 units, 100-unit cells."""

    def __init__(self):
        self.width = 800
        self.height = 800
        self.cell_size = 100
        self.grid_dimension = 8

    def to_grid(self, v):
        """Convert a coordinate to the top-left corner of its cell."""
        v = max(0, min(int(v), self.width))
        return min((v // self.cell_size) * self.cell_size, self.width)

    def is_poi(self, x, y):
        """True for restaurant/customer points (integer hundreds)."""
        return x % 100 == 0 and y % 100 == 0
