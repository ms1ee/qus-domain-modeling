"""Grid map and street-based path planning.

The city is an 800x800 coordinate plane divided into an 8x8 grid of 100x100
cells. Every grid line is a street; points whose x or y is a multiple of 100
lie on a street, and points where both are multiples of 100 are intersections
(restaurant and customer locations).
"""

import math

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIMENSION = MAP_SIZE // CELL_SIZE


class GridMap:
    """Describes the coordinate system and street layout of the city."""

    def __init__(self, map_size=MAP_SIZE, cell_size=CELL_SIZE):
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

    def contains(self, x, y):
        """Return True if the point lies inside the map bounds."""
        return 0 <= x <= self.map_size and 0 <= y <= self.map_size

    def is_street(self, x, y):
        """Return True if the point lies on a street (a grid line)."""
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def is_intersection(self, x, y):
        """Return True if the point is a grid intersection."""
        return x % self.cell_size == 0 and y % self.cell_size == 0

    def cell_of(self, x, y):
        """Return the (column, row) index of the cell containing the point."""
        col = min(x // self.cell_size, self.grid_dimension - 1)
        row = min(y // self.cell_size, self.grid_dimension - 1)
        return col, row

    def cell_center(self, value):
        """Return the center coordinate of the cell containing ``value``.

        Implements ``center = (value // 100) * 100 + 50``.
        """
        return (value // self.cell_size) * self.cell_size + self.cell_size // 2


class PathPlanner:
    """Computes street-following routes and per-tick movement.

    Routes always travel along streets using right-angle turns. Riders may
    share streets freely and never wait for one another, so no path conflict
    or deadlock can arise between riders.
    """

    def __init__(self, grid_map=None):
        """Create a planner bound to a grid map.

        Args:
            grid_map: Optional GridMap; a default 8x8 map is used otherwise.
        """
        self.grid_map = grid_map or GridMap()
        self.grid_dimension = self.grid_map.grid_dimension

    @staticmethod
    def next_position(x, y, tx, ty, speed):
        """Advance a position toward a target by at most ``speed`` units.

        Movement is horizontal first, then vertical (right-angle turn). When
        the rider is directly above or below the target, only vertical
        movement is used (straight-line special case).

        Args:
            x, y: Current coordinates.
            tx, ty: Target coordinates.
            speed: Maximum distance to move this tick.

        Returns:
            Tuple (new_x, new_y).
        """
        remaining = max(0, int(speed))
        while remaining > 0:
            if x != tx:
                step = min(remaining, abs(tx - x))
                x += step if tx > x else -step
                remaining -= step
            elif y != ty:
                step = min(remaining, abs(ty - y))
                y += step if ty > y else -step
                remaining -= step
            else:
                break
        return x, y

    @staticmethod
    def plan_route(start, end):
        """Return the corner points of a street route from ``start`` to ``end``.

        Args:
            start: Tuple (x, y).
            end: Tuple (x, y).

        Returns:
            List of (x, y) waypoints beginning with ``start`` and ending with
            ``end``. A straight route has two points, an L-shaped route three.
        """
        sx, sy = start
        ex, ey = end
        if sx == ex or sy == ey:
            return [(sx, sy), (ex, ey)]
        return [(sx, sy), (ex, sy), (ex, ey)]

    @staticmethod
    def route_length(route):
        """Return the total Manhattan length of a list of waypoints."""
        total = 0
        for (ax, ay), (bx, by) in zip(route, route[1:]):
            total += abs(bx - ax) + abs(by - ay)
        return total

    def plan_multi_stop(self, start, stops):
        """Build one continuous route that visits ``stops`` in order.

        Used for the restaurant-then-customer path of an order.

        Args:
            start: Tuple (x, y) where the rider currently is.
            stops: Ordered list of (x, y) destinations.

        Returns:
            List of waypoints starting at ``start``.
        """
        route = [tuple(start)]
        current = tuple(start)
        for stop in stops:
            leg = self.plan_route(current, stop)
            route.extend(leg[1:])
            current = tuple(stop)
        return route

    def optimize_stops(self, start, stops):
        """Greedily reorder stops by nearest Manhattan distance.

        Args:
            start: Tuple (x, y) origin.
            stops: List of (x, y) destinations.

        Returns:
            New list with the stops in a nearest-first visiting order.
        """
        remaining = list(stops)
        ordered = []
        current = tuple(start)
        while remaining:
            nxt = min(remaining,
                      key=lambda p: abs(p[0] - current[0]) + abs(p[1] - current[1]))
            ordered.append(nxt)
            remaining.remove(nxt)
            current = nxt
        return ordered

    @staticmethod
    def estimate_ticks(distance, speed):
        """Return the number of ticks needed to cover ``distance``."""
        if speed <= 0:
            raise ValueError("speed must be positive")
        return math.ceil(distance / speed)
