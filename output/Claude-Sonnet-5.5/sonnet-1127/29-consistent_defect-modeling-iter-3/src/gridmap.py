"""Grid map definition."""


class GridMap:
    """8x8 grid, 100-unit cells, 800x800 map."""

    def __init__(self):
        self.width = 800
        self.height = 800
        self.cell_size = 100
        self.grid_dimension = 8

    def clamp(self, v):
        return max(0, min(self.width, int(v)))

    def to_cell_corner(self, x, y):
        """Convert coordinates to the top-left corner of their grid cell."""
        cx = (self.clamp(x) // self.cell_size) * self.cell_size
        cy = (self.clamp(y) // self.cell_size) * self.cell_size
        return cx, cy

    def to_cell_center(self, x, y):
        cx, cy = self.to_cell_corner(x, y)
        return cx + 50, cy + 50

    def is_road(self, x, y):
        """Points at integer hundreds are locations; others are roads."""
        return not (x % 100 == 0 and y % 100 == 0)
