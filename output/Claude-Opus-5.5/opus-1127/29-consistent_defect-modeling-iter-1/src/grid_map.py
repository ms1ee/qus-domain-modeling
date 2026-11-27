"""Grid map definition (8x8 cells of 100x100 units on an 800x800 map)."""

MAP_SIZE = 800
CELL_SIZE = 100


class GridMap:
    """Describes the coordinate system of the simulated city."""

    def __init__(self, width=MAP_SIZE, height=MAP_SIZE, cell_size=CELL_SIZE):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.rows = height // cell_size
        self.columns = width // cell_size

    def clamp(self, value, upper=None):
        """Clamp a coordinate into the map range."""
        upper = self.width if upper is None else upper
        return max(0, min(upper, int(value)))

    def to_cell_corner(self, value):
        """Convert a raw coordinate to the top-left corner of its cell."""
        value = self.clamp(value)
        return (value // self.cell_size) * self.cell_size

    def to_cell_center(self, value):
        """Return the centre of the cell containing ``value``."""
        value = self.clamp(value)
        center = (value // self.cell_size) * self.cell_size + self.cell_size // 2
        return min(center, self.width)

    def is_location(self, x, y):
        """True if (x, y) is a restaurant/customer location point."""
        return x % self.cell_size == 0 and y % self.cell_size == 0

    def is_street(self, x, y):
        """True if (x, y) lies on a street line."""
        return x % self.cell_size == 0 or y % self.cell_size == 0


DEFAULT_GRID = GridMap()
