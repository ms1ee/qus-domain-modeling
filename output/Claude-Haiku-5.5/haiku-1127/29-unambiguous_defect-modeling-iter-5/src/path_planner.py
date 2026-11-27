"""Grid-based path planning for the 8x8 delivery map.

The map is an 800x800 coordinate system divided into an 8x8 grid of
100x100 cells. Streets lie on the grid lines (any coordinate that is a
multiple of 100). Restaurants and customers are located on street
intersections. Routes are right-angle paths that always travel along streets.
"""

import math

GRID_SIZE = 8
CELL_SIZE = 100
MAP_SIZE = GRID_SIZE * CELL_SIZE


def manhattan(a, b):
    """Return the Manhattan distance between two ``(x, y)`` points.

    Args:
        a: First point as a sequence ``(x, y)``.
        b: Second point as a sequence ``(x, y)``.

    Returns:
        Integer Manhattan distance.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Route:
    """A planned right-angle route.

    Attributes:
        waypoints (list[tuple[int, int]]): Ordered points, including the start
            point and the destination.
        total_distance (int): Total Manhattan length of the route.
        estimated_time (int): Estimated number of ticks needed to travel it.
    """

    def __init__(self, waypoints, total_distance, estimated_time):
        """Create a route.

        Args:
            waypoints: Ordered list of ``(x, y)`` points.
            total_distance: Total route length in map units.
            estimated_time: Estimated travel time in ticks.
        """
        self.waypoints = list(waypoints)
        self.total_distance = total_distance
        self.estimated_time = estimated_time


class Grid:
    """Description of the grid used by the simulator.

    Attributes:
        width (int): Number of cells horizontally.
        height (int): Number of cells vertically.
        cell_size (int): Edge length of one cell in map units.
    """

    def __init__(self, width=GRID_SIZE, height=GRID_SIZE, cell_size=CELL_SIZE):
        """Create a grid description.

        Args:
            width: Number of cells horizontally.
            height: Number of cells vertically.
            cell_size: Edge length of each cell.
        """
        self.width = width
        self.height = height
        self.cell_size = cell_size

    @property
    def map_size(self):
        """Return the side length of the map in map units."""
        return self.width * self.cell_size

    def cell_type(self, x, y):
        """Classify a point of the map.

        Args:
            x: X coordinate (0..map_size).
            y: Y coordinate (0..map_size).

        Returns:
            ``"intersection"``, ``"street"`` or ``"block"``.

        Raises:
            ValueError: If the point lies outside the map.
        """
        if not (0 <= x <= self.map_size and 0 <= y <= self.map_size):
            raise ValueError(f"point ({x}, {y}) is outside the map")
        on_x = x % self.cell_size == 0
        on_y = y % self.cell_size == 0
        if on_x and on_y:
            return "intersection"
        if on_x or on_y:
            return "street"
        return "block"


class PathPlanner:
    """Plans right-angle, street-following routes on the grid.

    Attributes:
        grid_size (int): Number of cells per axis.
        cell_size (int): Edge length of one cell.
        map_size (int): Side length of the map.
        grid (Grid): Grid description.
    """

    def __init__(self, grid_size=GRID_SIZE, cell_size=CELL_SIZE):
        """Create a planner.

        Args:
            grid_size: Number of cells per axis.
            cell_size: Edge length of one cell in map units.
        """
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.map_size = grid_size * cell_size
        self.grid = Grid(grid_size, grid_size, cell_size)

    def is_valid_point(self, x, y):
        """Return True if ``(x, y)`` lies within the map bounds."""
        return 0 <= x <= self.map_size and 0 <= y <= self.map_size

    def is_on_street(self, x, y):
        """Return True if ``(x, y)`` lies on a street (grid line)."""
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def is_intersection(self, x, y):
        """Return True if ``(x, y)`` is a street intersection."""
        return x % self.cell_size == 0 and y % self.cell_size == 0

    def snap_axis(self, value):
        """Snap one coordinate to the nearest grid line within the map.

        Args:
            value: Raw coordinate (any number).

        Returns:
            Integer coordinate that is a multiple of the cell size.
        """
        value = min(max(int(value), 0), self.map_size)
        snapped = int(round(value / self.cell_size)) * self.cell_size
        return min(max(snapped, 0), self.map_size)

    def snap(self, x, y):
        """Transform raw coordinates into a valid street intersection.

        Args:
            x: Raw X coordinate.
            y: Raw Y coordinate.

        Returns:
            Tuple ``(x, y)`` of snapped integer coordinates.
        """
        return self.snap_axis(x), self.snap_axis(y)

    def plan(self, start, end, speed=1):
        """Plan a right-angle route from ``start`` to ``end``.

        The route follows the street the start point lies on, then turns at
        most once to reach the destination intersection. Straight routes are
        produced when start and end share a street.

        Args:
            start: Current ``(x, y)`` position, which must lie on a street.
            end: Destination ``(x, y)`` intersection.
            speed: Units travelled per tick, used for the time estimate.

        Returns:
            A :class:`Route` describing the path.

        Raises:
            ValueError: If the points are outside the map, the destination is
                not an intersection, or the start is not on a street.
        """
        sx, sy = start
        ex, ey = end
        if not self.is_valid_point(sx, sy) or not self.is_valid_point(ex, ey):
            raise ValueError(f"route points outside map: {start} -> {end}")
        if not self.is_intersection(ex, ey):
            raise ValueError("destination must be a street intersection")
        if (sx, sy) == (ex, ey):
            return Route([(sx, sy)], 0, 0)

        c = self.cell_size
        if sy % c == 0:
            corner = (ex, sy)  # travel along the current horizontal street first
        elif sx % c == 0:
            corner = (sx, ey)  # travel along the current vertical street first
        else:
            raise ValueError(f"start point {start} is not on a street")

        waypoints = [(sx, sy)]
        if corner != waypoints[-1] and corner != (ex, ey):
            waypoints.append(corner)
        waypoints.append((ex, ey))

        total = sum(manhattan(waypoints[i], waypoints[i + 1])
                    for i in range(len(waypoints) - 1))
        speed = max(1, int(speed))
        estimated = math.ceil(total / speed)
        return Route(waypoints, total, estimated)
