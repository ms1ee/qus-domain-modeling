"""Grid map definitions.

The map is a square of ``map_size`` units divided into square cells of
``cell_size`` units. Grid lines (coordinates that are multiples of
``cell_size``) are streets. Intersections at integer hundreds are the
restaurant/customer landmarks.
"""

from dataclasses import dataclass


@dataclass
class Location:
    """A point on the map.

    Attributes:
        x: Horizontal coordinate.
        y: Vertical coordinate.
        is_road: Whether the point lies on a street.
    """

    x: int
    y: int
    is_road: bool = False


class GridMap:
    """Coordinate system helper for the 800x800 map with 100-unit cells."""

    def __init__(self, map_size=800, cell_size=100):
        """Create a grid map.

        Args:
            map_size: Side length of the square map in units.
            cell_size: Side length of one grid cell in units.

        Raises:
            ValueError: If the sizes are not positive or do not divide evenly.
        """
        if map_size <= 0 or cell_size <= 0:
            raise ValueError("map_size and cell_size must be positive")
        if map_size % cell_size != 0:
            raise ValueError("map_size must be a multiple of cell_size")
        self.map_size = map_size
        self.cell_size = cell_size
        self.grid_dimension = map_size // cell_size

    def in_bounds(self, x, y):
        """Return True if the point lies inside the map (inclusive)."""
        return 0 <= x <= self.map_size and 0 <= y <= self.map_size

    def is_road(self, x, y):
        """Return True if the point lies on a street (grid line)."""
        if not self.in_bounds(x, y):
            return False
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def is_intersection(self, x, y):
        """Return True if the point is a street intersection (landmark)."""
        return (
            self.in_bounds(x, y)
            and x % self.cell_size == 0
            and y % self.cell_size == 0
        )

    def snap_to_cell(self, value):
        """Clamp a coordinate to the map and floor it to the cell boundary.

        Args:
            value: Raw coordinate.

        Returns:
            The top-left coordinate of the cell containing ``value``.
        """
        clamped = min(max(int(value), 0), self.map_size)
        return (clamped // self.cell_size) * self.cell_size

    def snap_point(self, x, y):
        """Snap an ``(x, y)`` point to the top-left corner of its cell."""
        return self.snap_to_cell(x), self.snap_to_cell(y)

    def cell_of(self, x, y):
        """Return the ``(column, row)`` index of the cell containing a point."""
        col = min(max(int(x) // self.cell_size, 0), self.grid_dimension - 1)
        row = min(max(int(y) // self.cell_size, 0), self.grid_dimension - 1)
        return col, row

    def cell_center(self, x, y):
        """Return the centre point of the cell containing ``(x, y)``.

        Uses ``center = (coord // cell_size) * cell_size + cell_size // 2``.
        """
        half = self.cell_size // 2
        return (
            (int(x) // self.cell_size) * self.cell_size + half,
            (int(y) // self.cell_size) * self.cell_size + half,
        )

    def intersections(self):
        """Return a list of :class:`Location` for every street intersection."""
        points = []
        for gx in range(self.grid_dimension + 1):
            for gy in range(self.grid_dimension + 1):
                points.append(
                    Location(gx * self.cell_size, gy * self.cell_size, True)
                )
        return points
