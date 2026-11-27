"""Grid geometry for the 800x800 food delivery map.

The map is an 8x8 arrangement of 100x100 cells. Points whose coordinates are
both multiples of 100 are *locations* (restaurants, customers and street
intersections). Points where exactly one coordinate is a multiple of 100 lie
on a *street*. All other points are inside city blocks and are not drivable.
"""

import math
from typing import List, Tuple

MAP_SIZE = 800
CELL_SIZE = 100
DIMENSIONS = MAP_SIZE // CELL_SIZE
POINT_STEP = 50  # Sampling resolution used for road sampling and ASCII map.


def _is_int(value) -> bool:
    """Return True when ``value`` is an int but not a bool.

    Args:
        value: Any object.

    Returns:
        bool: Whether the value is a genuine integer.
    """
    return isinstance(value, int) and not isinstance(value, bool)


class Grid:
    """Coordinate helper describing the dispatch grid."""

    def __init__(self, map_size: int = MAP_SIZE, cell_size: int = CELL_SIZE):
        """Create a grid description.

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
        self.dimensions = map_size // cell_size
        self.half_cell = cell_size // 2

    def is_valid_coord(self, x, y) -> bool:
        """Check that both coordinates are integers inside the map.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            bool: True when the point lies within 0..map_size on both axes.
        """
        return (
            _is_int(x)
            and _is_int(y)
            and 0 <= x <= self.map_size
            and 0 <= y <= self.map_size
        )

    def clamp(self, value) -> int:
        """Clamp a value into the map range.

        Args:
            value: Numeric coordinate.

        Returns:
            int: Value limited to 0..map_size.
        """
        return max(0, min(self.map_size, int(value)))

    def snap_to_location(self, x, y) -> Tuple[int, int]:
        """Transform arbitrary coordinates to the nearest grid location.

        Locations are the points at integer hundreds (e.g. 100, 200).

        Args:
            x: X coordinate (may be any integer in range).
            y: Y coordinate.

        Returns:
            Tuple[int, int]: Snapped (x, y) location within the map.
        """
        cs = self.cell_size
        snapped_x = math.floor(x / cs + 0.5) * cs
        snapped_y = math.floor(y / cs + 0.5) * cs
        return self.clamp(snapped_x), self.clamp(snapped_y)

    def is_location(self, x: int, y: int) -> bool:
        """Return True if the point is a grid location (intersection).

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            bool: Whether both coordinates are multiples of the cell size.
        """
        return x % self.cell_size == 0 and y % self.cell_size == 0

    def is_horizontal_street(self, y: int) -> bool:
        """Return True if the given y value lies on a horizontal street.

        Args:
            y: Y coordinate.

        Returns:
            bool: Whether y is a grid line.
        """
        return y % self.cell_size == 0

    def is_vertical_street(self, x: int) -> bool:
        """Return True if the given x value lies on a vertical street.

        Args:
            x: X coordinate.

        Returns:
            bool: Whether x is a grid line.
        """
        return x % self.cell_size == 0

    def is_road(self, x: int, y: int) -> bool:
        """Return True if the point lies on any street.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            bool: Whether the point is drivable.
        """
        return self.is_horizontal_street(y) or self.is_vertical_street(x)

    def cell_of(self, x: int, y: int) -> Tuple[int, int]:
        """Return the (grid_x, grid_y) index of the cell containing a point.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Tuple[int, int]: Cell indices in 0..dimensions-1.
        """
        gx = min(x // self.cell_size, self.dimensions - 1)
        gy = min(y // self.cell_size, self.dimensions - 1)
        return gx, gy

    def cell_center(self, x: int, y: int) -> Tuple[int, int]:
        """Return the center point of the cell containing a point.

        Uses ``center_x = (grid_x // 100) * 100 + 50``.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Tuple[int, int]: Cell center coordinates.
        """
        gx, gy = self.cell_of(x, y)
        return gx * self.cell_size + self.half_cell, gy * self.cell_size + self.half_cell

    def locations(self) -> List[Tuple[int, int]]:
        """Return every grid location (intersection) on the map.

        Returns:
            List[Tuple[int, int]]: All lattice points.
        """
        cs = self.cell_size
        return [
            (x, y)
            for x in range(0, self.map_size + 1, cs)
            for y in range(0, self.map_size + 1, cs)
        ]

    def road_points(self, step: int = POINT_STEP) -> List[Tuple[int, int]]:
        """Return sampled points that lie on streets.

        Args:
            step: Sampling resolution.

        Returns:
            List[Tuple[int, int]]: Drivable sample points.
        """
        return [
            (x, y)
            for x in range(0, self.map_size + 1, step)
            for y in range(0, self.map_size + 1, step)
            if self.is_road(x, y)
        ]
