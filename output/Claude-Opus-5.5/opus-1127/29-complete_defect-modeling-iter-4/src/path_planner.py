"""Grid-based path planning.

The map is 800x800 units divided into 8x8 cells of 100x100.  Streets run
along the grid lines (coordinates that are multiples of 100).  Restaurants
and customers sit at cell centres (multiples of 100 plus 50).
"""

import math

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIMENSION = MAP_SIZE // CELL_SIZE


def clamp(value, low=0, high=MAP_SIZE):
    """Clamp ``value`` into [low, high]."""
    return max(low, min(high, value))


def to_grid_index(value):
    """Convert a coordinate (0-800) to a grid index (0-7)."""
    value = clamp(int(value), 0, MAP_SIZE - 1)
    return value // CELL_SIZE


def to_grid_center(value):
    """Convert a coordinate to the centre of the containing cell.

    ``center = (v // 100) * 100 + 50``; the boundary value 800 is mapped
    into the last cell.
    """
    return to_grid_index(value) * CELL_SIZE + CELL_SIZE // 2


def manhattan(a, b):
    """Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Location:
    """Simple 2D point."""

    def __init__(self, x, y):
        self.x = int(x)
        self.y = int(y)

    def as_tuple(self):
        return (self.x, self.y)

    def __repr__(self):
        return "Location({}, {})".format(self.x, self.y)


class Route:
    """A planned polyline route made of axis-aligned segments."""

    def __init__(self, waypoints, speed=100, special_case=False):
        self.waypoints = [tuple(p) for p in waypoints]
        self.speed = max(1, int(speed))
        self.special_case = special_case

    @property
    def length(self):
        total = 0
        for a, b in zip(self.waypoints, self.waypoints[1:]):
            total += manhattan(a, b)
        return total

    @property
    def estimated_time(self):
        return int(math.ceil(self.length / float(self.speed)))

    def __repr__(self):
        return "Route({}, length={})".format(self.waypoints, self.length)


class PathPlanner:
    """Plans street-first routes on the grid."""

    def __init__(self, cell_size=CELL_SIZE, map_size=MAP_SIZE):
        self.cell_size = cell_size
        self.map_size = map_size

    def on_street(self, value):
        """True if the coordinate lies on a grid line (street)."""
        return value % self.cell_size == 0

    def _street_toward(self, start, end):
        """Choose the horizontal street line to use from ``start``."""
        if self.on_street(start):
            return start
        low = (start // self.cell_size) * self.cell_size
        high = low + self.cell_size
        if end > start:
            street = high
        elif end < start:
            street = low
        else:
            street = low if start - low <= high - start else high
        return clamp(street, 0, self.map_size)

    @staticmethod
    def _simplify(points):
        """Remove duplicate and collinear intermediate points."""
        result = []
        for p in points:
            if result and result[-1] == p:
                continue
            if len(result) >= 2:
                a, b = result[-2], result[-1]
                if (a[0] == b[0] == p[0]) or (a[1] == b[1] == p[1]):
                    result[-1] = p
                    continue
            result.append(p)
        return result

    def plan(self, start, end, speed=100):
        """Plan a route from ``start`` to ``end``.

        Strategy: move vertically to the nearest horizontal street toward
        the target, travel along it, then turn into the destination.
        Special case: when the start is directly above/below the target
        (same x) the rider goes straight.

        :return: Route
        """
        sx, sy = int(start[0]), int(start[1])
        ex, ey = int(end[0]), int(end[1])
        special = False
        if (sx, sy) == (ex, ey):
            points = [(sx, sy)]
        elif sx == ex:
            special = True
            points = [(sx, sy), (ex, ey)]
        elif sy == ey and self.on_street(sy):
            points = [(sx, sy), (ex, ey)]
        else:
            street_y = self._street_toward(sy, ey)
            points = [(sx, sy), (sx, street_y), (ex, street_y), (ex, ey)]
        return Route(self._simplify(points), speed=speed, special_case=special)

    def plan_multi(self, start, stops, speed=100):
        """Plan a continuous route through several destinations."""
        points = [tuple(start)]
        special = False
        current = tuple(start)
        for stop in stops:
            leg = self.plan(current, stop, speed)
            special = special or leg.special_case
            points.extend(leg.waypoints[1:])
            current = tuple(stop)
        # Keep stops as explicit waypoints; only drop exact duplicates.
        cleaned = []
        for p in points:
            if not cleaned or cleaned[-1] != p:
                cleaned.append(p)
        return Route(cleaned, speed=speed, special_case=special)
