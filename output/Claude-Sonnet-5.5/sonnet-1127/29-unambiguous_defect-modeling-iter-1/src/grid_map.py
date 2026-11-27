"""Grid map and coordinate helpers."""

MAP_SIZE = 800
CELL = 100


def to_center(v):
    """Convert coordinate to grid cell center, clamped to the map."""
    v = max(0, min(MAP_SIZE - 1, int(v)))
    return (v // CELL) * CELL + CELL // 2


def convert_point(x, y):
    """Convert a point to its cell center."""
    return (to_center(x), to_center(y))


def cell_of(v):
    """Grid index of a coordinate."""
    return max(0, min(MAP_SIZE // CELL - 1, int(v) // CELL))


class GridMap:
    """8x8 grid map description."""

    def __init__(self, width=MAP_SIZE, height=MAP_SIZE, cell_size=CELL):
        self.width = width
        self.height = height
        self.cell_size = cell_size
