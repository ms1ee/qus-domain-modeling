"""Grid map definitions: 800x800 coordinate system split into 8x8 cells.

Streets run along every multiple of 100 (both horizontally and vertically).
Restaurants and customers are located at cell centres (``x50`` coordinates).
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIMENSION = MAP_SIZE // CELL_SIZE


class GridMap:
    """Static helper describing the grid map."""

    map_size = MAP_SIZE
    cell_size = CELL_SIZE
    grid_dimension = GRID_DIMENSION

    @staticmethod
    def clamp(value):
        """Clamp a coordinate into the range [0, MAP_SIZE]."""
        return max(0, min(MAP_SIZE, int(value)))

    @staticmethod
    def to_center(value):
        """Convert a raw coordinate into its grid cell centre.

        ``center = (v // 100) * 100 + 50``; values out of range are clamped
        and the upper boundary (800) maps to the last cell (750).
        """
        v = GridMap.clamp(value)
        if v >= MAP_SIZE:
            v = MAP_SIZE - 1
        return (v // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2

    @staticmethod
    def to_center_point(x, y):
        """Convert a raw point to the centre point of its grid cell."""
        return GridMap.to_center(x), GridMap.to_center(y)

    @staticmethod
    def cell_of(x, y):
        """Return the (column, row) cell indices containing the point."""
        col = min(GRID_DIMENSION - 1, max(0, int(x) // CELL_SIZE))
        row = min(GRID_DIMENSION - 1, max(0, int(y) // CELL_SIZE))
        return col, row

    @staticmethod
    def in_bounds(x, y):
        """True if the point lies within the map."""
        return 0 <= x <= MAP_SIZE and 0 <= y <= MAP_SIZE

    @staticmethod
    def is_horizontal_street(y):
        """True if ``y`` lies on a horizontal street."""
        return int(y) % CELL_SIZE == 0

    @staticmethod
    def is_vertical_street(x):
        """True if ``x`` lies on a vertical street."""
        return int(x) % CELL_SIZE == 0

    @staticmethod
    def is_road(x, y):
        """True if the point lies on any street."""
        return GridMap.is_horizontal_street(y) or GridMap.is_vertical_street(x)
