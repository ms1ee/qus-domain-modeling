"""Coordinate and grid helpers for the 800x800 map.

The map is an 8x8 grid of 100x100 cells. Points whose coordinates are both
multiples of 100 are street intersections (restaurant and customer
locations). Streets run along every line where x or y is a multiple of 100.
"""

import config


def clamp(value, low, high):
    """Clamp value into the closed interval [low, high].

    Args:
        value: Number to clamp.
        low: Lower bound.
        high: Upper bound.

    Returns:
        The clamped value.
    """
    return max(low, min(high, value))


def snap_to_grid(value):
    """Snap a raw coordinate to the nearest intersection line.

    The input is first clamped to the map range, then rounded to the nearest
    multiple of CELL_SIZE.

    Args:
        value: Raw integer coordinate (0-800 expected; out-of-range values
            are clamped).

    Returns:
        The snapped coordinate, a multiple of CELL_SIZE within [0, MAP_SIZE].
    """
    value = clamp(int(value), 0, config.MAP_SIZE)
    half = config.CELL_SIZE // 2
    snapped = ((value + half) // config.CELL_SIZE) * config.CELL_SIZE
    return clamp(snapped, 0, config.MAP_SIZE)


def cell_index(value):
    """Return the grid cell index (0..GRID_DIM-1) containing a coordinate.

    Args:
        value: Coordinate in map units.

    Returns:
        Integer cell index along that axis.
    """
    value = clamp(int(value), 0, config.MAP_SIZE)
    return min(value // config.CELL_SIZE, config.GRID_DIM - 1)


def cell_center(value):
    """Return the grid cell center for a coordinate.

    Implements center = (grid // 100) * 100 + 50.

    Args:
        value: Coordinate in map units.

    Returns:
        Center coordinate of the containing cell.
    """
    return cell_index(value) * config.CELL_SIZE + config.CELL_SIZE // 2


def is_road(x, y):
    """Check whether a point lies on a street.

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        True if the point is inside the map and on a grid line.
    """
    if not (0 <= x <= config.MAP_SIZE and 0 <= y <= config.MAP_SIZE):
        return False
    return x % config.CELL_SIZE == 0 or y % config.CELL_SIZE == 0


def is_intersection(x, y):
    """Check whether a point is a street intersection (restaurant/customer spot).

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        True if both coordinates are multiples of CELL_SIZE within the map.
    """
    return (
        0 <= x <= config.MAP_SIZE
        and 0 <= y <= config.MAP_SIZE
        and x % config.CELL_SIZE == 0
        and y % config.CELL_SIZE == 0
    )


def manhattan(a, b):
    """Return the Manhattan distance between two points.

    Args:
        a: (x, y) tuple.
        b: (x, y) tuple.

    Returns:
        Integer distance |dx| + |dy|.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def all_intersections():
    """Return every intersection point of the map.

    Returns:
        List of (x, y) tuples for the 9x9 intersection lattice.
    """
    count = config.GRID_DIM + 1
    return [
        (i * config.CELL_SIZE, j * config.CELL_SIZE)
        for i in range(count)
        for j in range(count)
    ]


class MapGrid:
    """Description of the street grid used by the path planner and display."""

    def __init__(self, size=config.MAP_SIZE, cell_size=config.CELL_SIZE):
        """Create a grid description.

        Args:
            size: Map side length in units.
            cell_size: Side length of one grid cell in units.
        """
        self.size = size
        self.cell_size = cell_size

    @property
    def grid_dim(self):
        """Number of cells along one axis."""
        return self.size // self.cell_size

    def contains(self, x, y):
        """Return True if (x, y) lies inside the map bounds."""
        return 0 <= x <= self.size and 0 <= y <= self.size

    def is_road(self, x, y):
        """Return True if (x, y) lies on a street of this grid."""
        if not self.contains(x, y):
            return False
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def intersections(self):
        """Return all intersection points of this grid."""
        count = self.grid_dim + 1
        return [
            (i * self.cell_size, j * self.cell_size)
            for i in range(count)
            for j in range(count)
        ]

    def cell_of(self, x, y):
        """Return the (column, row) cell index containing (x, y)."""
        return cell_index(x), cell_index(y)
