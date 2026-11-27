"""Grid map and coordinate utilities for the food delivery simulator.

The map is 800x800 units divided into an 8x8 grid of 100x100 cells.

* Street points: points whose x or y coordinate lies on a grid line
  (``x % 100 == 0`` or ``y % 100 == 0``). Riders move only along streets.
* Location points: restaurant and customer positions. They are cell centre
  points, ``center = (v // 100) * 100 + 50``, so ``x % 100 == 50`` and
  ``y % 100 == 50``. Each location point is adjacent to four street points.

Riders move on a 50-unit lattice, so every lattice point is either a street
point or a location point.
"""

from dataclasses import dataclass
from typing import List, Tuple

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIMENSION = 8
LATTICE_STEP = 50

Point = Tuple[int, int]


@dataclass
class Cell:
    """A single 100x100 grid cell.

    Attributes:
        grid_x: Column index of the cell (0-7).
        grid_y: Row index of the cell (0-7).
        is_road: True when the cell boundary is part of the road network.
        is_location_point: True when the cell centre is a location point.
        center_x: X coordinate of the cell centre.
        center_y: Y coordinate of the cell centre.
    """

    grid_x: int
    grid_y: int
    is_road: bool
    is_location_point: bool
    center_x: int
    center_y: int


def manhattan(a: Point, b: Point) -> int:
    """Return the Manhattan distance between two points.

    Args:
        a: First point (x, y).
        b: Second point (x, y).

    Returns:
        Sum of absolute coordinate differences.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def snap_value(value: int, map_length: int = MAP_SIZE,
               cell_size: int = CELL_SIZE) -> int:
    """Snap one coordinate to the centre of its grid cell.

    Args:
        value: Raw coordinate in the range 0-800.
        map_length: Total map length.
        cell_size: Size of one grid cell.

    Returns:
        Centre coordinate of the cell containing ``value``.
    """
    clamped = min(max(int(value), 0), map_length)
    size = map_length // cell_size
    index = min(clamped // cell_size, size - 1)
    return index * cell_size + cell_size // 2


def snap_point(x: int, y: int) -> Point:
    """Snap an (x, y) point to the nearest grid cell centre.

    Args:
        x: Raw x coordinate.
        y: Raw y coordinate.

    Returns:
        Grid cell centre point (x, y).
    """
    return snap_value(x), snap_value(y)


class GridMap:
    """An 8x8 grid representing an 800x800 coordinate system."""

    def __init__(self, size: int = GRID_DIMENSION,
                 cell_size: int = CELL_SIZE) -> None:
        """Create the grid and its 64 cells.

        Args:
            size: Number of cells per row and column.
            cell_size: Edge length of one cell in units.
        """
        self.size = size
        self.cell_size = cell_size
        self.map_length = size * cell_size
        self.cells: List[Cell] = []
        half = cell_size // 2
        for grid_y in range(size):
            for grid_x in range(size):
                self.cells.append(
                    Cell(
                        grid_x=grid_x,
                        grid_y=grid_y,
                        is_road=True,
                        is_location_point=True,
                        center_x=grid_x * cell_size + half,
                        center_y=grid_y * cell_size + half,
                    )
                )

    def cell_at(self, grid_x: int, grid_y: int) -> Cell:
        """Return the cell at the given grid indices.

        Args:
            grid_x: Column index (0 to size-1).
            grid_y: Row index (0 to size-1).

        Returns:
            The Cell object.

        Raises:
            IndexError: If the indices are outside the grid.
        """
        if not (0 <= grid_x < self.size and 0 <= grid_y < self.size):
            raise IndexError(f"cell ({grid_x}, {grid_y}) is outside the grid")
        return self.cells[grid_y * self.size + grid_x]

    def in_bounds(self, x: int, y: int) -> bool:
        """Check whether a point lies inside the map.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            True if 0 <= x, y <= map_length.
        """
        return 0 <= x <= self.map_length and 0 <= y <= self.map_length

    def is_street(self, x: int, y: int) -> bool:
        """Check whether a point lies on the street network.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            True if the point is on a grid line and inside the map.
        """
        if not self.in_bounds(x, y):
            return False
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def is_location(self, x: int, y: int) -> bool:
        """Check whether a point is a restaurant/customer location point.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            True if the point is a cell centre.
        """
        if not self.in_bounds(x, y):
            return False
        half = self.cell_size // 2
        return x % self.cell_size == half and y % self.cell_size == half

    def snap(self, x: int, y: int) -> Point:
        """Snap a raw point to the centre of its grid cell.

        Args:
            x: Raw x coordinate.
            y: Raw y coordinate.

        Returns:
            Cell centre point.
        """
        return (snap_value(x, self.map_length, self.cell_size),
                snap_value(y, self.map_length, self.cell_size))

    def lattice_points(self) -> List[Point]:
        """Return every 50-unit lattice point of the map.

        Returns:
            List of (x, y) lattice points.
        """
        points: List[Point] = []
        for y in range(0, self.map_length + 1, LATTICE_STEP):
            for x in range(0, self.map_length + 1, LATTICE_STEP):
                points.append((x, y))
        return points
