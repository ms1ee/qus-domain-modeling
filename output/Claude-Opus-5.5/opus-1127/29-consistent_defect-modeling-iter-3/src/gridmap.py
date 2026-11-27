"""Grid map and coordinate conversion utilities."""

MAP_SIZE = 800
CELL_SIZE = 100


def clamp(value, low=0, high=MAP_SIZE):
    """Clamp ``value`` into [low, high]."""
    return max(low, min(high, int(value)))


def to_grid(value, cell=CELL_SIZE):
    """Convert a raw coordinate to the top-left corner of its grid cell."""
    return (clamp(value) // cell) * cell


def to_grid_point(pos, cell=CELL_SIZE):
    """Convert an (x, y) pair to the top-left corner of its grid cell."""
    return [to_grid(pos[0], cell), to_grid(pos[1], cell)]


def grid_center(value, cell=CELL_SIZE):
    """Return the center of the grid cell: (v // 100) * 100 + 50."""
    return (clamp(value) // cell) * cell + cell // 2


class GridMap:
    """An 8x8 grid representing an 800x800 coordinate system."""

    def __init__(self, width=MAP_SIZE, height=MAP_SIZE, cell_size=CELL_SIZE):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.grid_dimension = width // cell_size

    def in_bounds(self, x, y):
        return 0 <= x <= self.width and 0 <= y <= self.height

    def is_location(self, x, y):
        """Points at integer hundreds are restaurant/customer locations."""
        return x % self.cell_size == 0 and y % self.cell_size == 0

    def is_street(self, x, y):
        """A point lies on a street if x or y is aligned with a grid line."""
        return x % self.cell_size == 0 or y % self.cell_size == 0
