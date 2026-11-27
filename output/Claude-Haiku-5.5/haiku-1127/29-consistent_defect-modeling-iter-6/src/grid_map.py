"""Grid geometry for the 800x800 unit city map.

The city is an 8x8 grid of 100x100 unit cells. Streets run along the lines
whose x or y coordinate is a multiple of 100. Intersections (points where both
coordinates are multiples of 100) are used as restaurant, customer and rider
waypoint locations.
"""

from typing import List, Tuple

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIMENSION = MAP_SIZE // CELL_SIZE  # 8 cells per axis

Point = Tuple[int, int]


class GridMap:
    """Geometry helper describing the grid city layout."""

    def __init__(self, map_size: int = MAP_SIZE, cell_size: int = CELL_SIZE) -> None:
        """Create a grid map.

        Args:
            map_size: Side length of the square map in units.
            cell_size: Side length of one grid cell in units.

        Raises:
            ValueError: If the sizes are not positive or do not divide evenly.
        """
        if map_size <= 0 or cell_size <= 0 or map_size % cell_size != 0:
            raise ValueError("map_size must be a positive multiple of cell_size")
        self.map_size = map_size
        self.cell_size = cell_size
        self.grid_dimension = map_size // cell_size

    def is_valid_coordinate(self, value: int) -> bool:
        """Return True if a single coordinate lies within the map bounds."""
        return isinstance(value, int) and 0 <= value <= self.map_size

    def is_valid_point(self, point: Point) -> bool:
        """Return True if both coordinates of ``point`` lie within the map."""
        x, y = point
        return self.is_valid_coordinate(x) and self.is_valid_coordinate(y)

    def is_intersection(self, point: Point) -> bool:
        """Return True if ``point`` lies on a street intersection."""
        x, y = point
        return (
            self.is_valid_point(point)
            and x % self.cell_size == 0
            and y % self.cell_size == 0
        )

    def is_on_street(self, point: Point) -> bool:
        """Return True if ``point`` lies on a street (grid line)."""
        x, y = point
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def snap_coordinate(self, value: int) -> int:
        """Snap one coordinate to the top-left corner of its grid cell.

        Values outside the map are clamped first, so 800 maps to 700.
        """
        value = int(value)
        value = min(max(value, 0), self.map_size - 1)
        return (value // self.cell_size) * self.cell_size

    def snap_point(self, point: Point) -> Point:
        """Convert a point to the top-left corner of its grid cell."""
        x, y = point
        return (self.snap_coordinate(x), self.snap_coordinate(y))

    def cell_of(self, point: Point) -> Tuple[int, int]:
        """Return the (column, row) index of the cell containing ``point``."""
        x, y = point
        col = min(max(int(x), 0), self.map_size - 1) // self.cell_size
        row = min(max(int(y), 0), self.map_size - 1) // self.cell_size
        return col, row

    def cell_center(self, point: Point) -> Point:
        """Return the centre point of the cell containing ``point``.

        Uses ``center = (grid // cell_size) * cell_size + cell_size // 2``.
        """
        col, row = self.cell_of(point)
        half = self.cell_size // 2
        return (col * self.cell_size + half, row * self.cell_size + half)

    def intersection_neighbors(self, point: Point) -> List[Point]:
        """Return the adjacent intersections reachable along a street.

        The order of the result prefers horizontal moves (east, west) before
        vertical moves (south, north).
        """
        x, y = point
        step = self.cell_size
        result: List[Point] = []
        for dx, dy in ((step, 0), (-step, 0), (0, step), (0, -step)):
            nx, ny = x + dx, y + dy
            if 0 <= nx <= self.map_size and 0 <= ny <= self.map_size:
                result.append((nx, ny))
        return result
