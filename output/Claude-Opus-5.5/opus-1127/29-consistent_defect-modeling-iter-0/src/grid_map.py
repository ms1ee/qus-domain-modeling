"""Grid map model (8x8 cells over an 800x800 coordinate system)."""

try:
    from . import config
except ImportError:  # pragma: no cover
    import config


class GridMap:
    """Represents the 800x800 map split into 100x100 cells."""

    def __init__(self, width=config.MAP_SIZE, height=config.MAP_SIZE,
                 cell_size=config.CELL_SIZE):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.grid_dimension = width // cell_size

    def in_bounds(self, x, y):
        """Return True if (x, y) is within the map."""
        return 0 <= x <= self.width and 0 <= y <= self.height

    def is_location(self, x, y):
        """Points at integer hundreds are restaurant/customer locations."""
        return x % self.cell_size == 0 and y % self.cell_size == 0

    def is_road(self, x, y):
        """Any non-location point is a road."""
        return not self.is_location(x, y)

    def is_street(self, x, y):
        """A point lies on a street when x or y aligns with a grid line."""
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def cell_of(self, x, y):
        """Return the (col, row) cell index of a coordinate, clamped."""
        col = min(max(int(x), 0) // self.cell_size, self.grid_dimension - 1)
        row = min(max(int(y), 0) // self.cell_size, self.grid_dimension - 1)
        return col, row

    def center_of(self, x, y):
        """Return the center point of the cell containing (x, y)."""
        col, row = self.cell_of(x, y)
        half = self.cell_size // 2
        return col * self.cell_size + half, row * self.cell_size + half

    def to_dict(self):
        return {"width": self.width, "height": self.height,
                "cell_size": self.cell_size,
                "grid_dimension": self.grid_dimension}
