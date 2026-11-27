"""Grid based path planning for riders."""

import math

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE


def _clamp(value, low, high):
    return max(low, min(high, value))


class PathPlanner:
    """Plans right-angle routes that prefer travelling along streets.

    Streets are the horizontal/vertical lines at multiples of 100.  A route
    from an arbitrary point first moves vertically onto the nearest
    horizontal street, travels horizontally along that street to the target
    column, then moves vertically to the target.  When the rider is directly
    above or below the target (special case) it moves straight vertically.
    """

    @staticmethod
    def to_cell_center(x, y):
        """Convert a coordinate pair to the centre of its grid cell."""
        x = _clamp(int(x), 0, MAP_SIZE - 1)
        y = _clamp(int(y), 0, MAP_SIZE - 1)
        return ((x // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2,
                (y // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2)

    @staticmethod
    def to_cell(x, y):
        """Return the (col, row) grid cell index of a coordinate."""
        col = _clamp(int(x) // CELL_SIZE, 0, GRID_DIM - 1)
        row = _clamp(int(y) // CELL_SIZE, 0, GRID_DIM - 1)
        return col, row

    @staticmethod
    def is_vertical_special(start, end):
        """True if the start is directly above or below the end point."""
        return start[0] == end[0] and start[1] != end[1]

    @staticmethod
    def nearest_street(value):
        """Return the nearest street line (multiple of 100) to ``value``."""
        return _clamp(((int(value) + CELL_SIZE // 2) // CELL_SIZE) * CELL_SIZE,
                      0, MAP_SIZE)

    @staticmethod
    def plan_route(start, end):
        """Return the list of waypoints (excluding ``start``) to ``end``.

        Every consecutive segment is axis aligned.
        """
        start = (int(start[0]), int(start[1]))
        end = (int(end[0]), int(end[1]))
        if start == end:
            return []
        sx, sy = start
        tx, ty = end
        if sx == tx or sy == ty:
            return [end]
        street_y = PathPlanner.nearest_street(sy)
        candidates = [(sx, street_y), (tx, street_y), (tx, ty)]
        route = []
        prev = start
        for pt in candidates:
            if pt != prev:
                route.append(pt)
                prev = pt
        return route

    @staticmethod
    def multi_route(start, destinations):
        """Plan a continuous route through several destinations in order."""
        route = []
        current = (int(start[0]), int(start[1]))
        for dest in destinations:
            route.extend(PathPlanner.plan_route(current, dest))
            current = (int(dest[0]), int(dest[1]))
        return route

    @staticmethod
    def route_length(start, waypoints):
        """Total Manhattan length of a route."""
        total = 0
        prev = start
        for pt in waypoints:
            total += abs(pt[0] - prev[0]) + abs(pt[1] - prev[1])
            prev = pt
        return total

    @staticmethod
    def estimate_ticks(length, speed):
        """Number of ticks needed to travel ``length`` at ``speed``."""
        if speed <= 0:
            return 0
        return int(math.ceil(length / float(speed)))

    @staticmethod
    def sample_points(start, waypoints, step=10):
        """Yield points along a route every ``step`` units (for drawing)."""
        points = [tuple(start)]
        prev = tuple(start)
        for pt in waypoints:
            dx = pt[0] - prev[0]
            dy = pt[1] - prev[1]
            dist = abs(dx) + abs(dy)
            n = max(1, dist // step)
            for i in range(1, n + 1):
                points.append((prev[0] + dx * i // n, prev[1] + dy * i // n))
            prev = pt
        return points

    @staticmethod
    def euclidean(a, b):
        """Euclidean distance between two points."""
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
