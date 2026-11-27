"""Grid-based path planning for riders.

The map is 800x800 units split into 8x8 cells of 100x100 units.  Lines with
x or y equal to a multiple of 100 are *streets*.  Routes are made of
axis-aligned segments; when possible the rider first reaches a street, then
travels along it, and finally enters the target cell.
"""

import math

CELL_SIZE = 100
MAP_SIZE = 800


class Route:
    """A planned route made of axis-aligned waypoints."""

    def __init__(self, waypoints, speed=10, special_case=False):
        self.waypoints = [tuple(p) for p in waypoints]
        self.speed = speed
        self.special_case = special_case

    @property
    def length(self):
        """Total route length (Manhattan, since segments are axis-aligned)."""
        total = 0
        for a, b in zip(self.waypoints, self.waypoints[1:]):
            total += abs(b[0] - a[0]) + abs(b[1] - a[1])
        return total

    @property
    def estimated_time(self):
        """Estimated number of ticks to traverse the route."""
        if self.speed <= 0:
            return 0
        return int(math.ceil(self.length / float(self.speed)))

    def __repr__(self):
        return "Route(%r, speed=%r)" % (self.waypoints, self.speed)


class PathPlanner:
    """Plans street-first routes on the grid."""

    CELL_SIZE = CELL_SIZE
    MAP_SIZE = MAP_SIZE

    @classmethod
    def is_on_street(cls, x, y):
        """Return True if the point lies on a street line."""
        return x % cls.CELL_SIZE == 0 or y % cls.CELL_SIZE == 0

    @classmethod
    def _street_line(cls, value, toward):
        """Pick the street line adjacent to ``value`` in direction ``toward``."""
        if value % cls.CELL_SIZE == 0:
            return value
        lower = (value // cls.CELL_SIZE) * cls.CELL_SIZE
        upper = lower + cls.CELL_SIZE
        result = upper if toward > value else lower
        return max(0, min(cls.MAP_SIZE, result))

    @classmethod
    def plan(cls, start, end, speed=10):
        """Plan a route from ``start`` to ``end``.

        Special case: if the rider is directly above or below the target
        (same x coordinate) it moves straight vertically and the route is
        flagged with ``special_case=True``.
        """
        sx, sy = int(start[0]), int(start[1])
        tx, ty = int(end[0]), int(end[1])
        points = [(sx, sy)]
        special = False
        if (sx, sy) == (tx, ty):
            return Route(points, speed, special)
        if sx == tx:
            special = True
            points.append((tx, ty))
        elif sy == ty:
            points.append((tx, ty))
        else:
            street_y = cls._street_line(sy, ty)
            for p in ((sx, street_y), (tx, street_y), (tx, ty)):
                if p != points[-1]:
                    points.append(p)
        return Route(points, speed, special)

    @classmethod
    def plan_multi(cls, start, destinations, speed=10):
        """Plan a continuous route through several destinations."""
        points = [tuple(start)]
        special = False
        current = tuple(start)
        for dest in destinations:
            leg = cls.plan(current, dest, speed)
            special = special or leg.special_case
            for p in leg.waypoints[1:]:
                if p != points[-1]:
                    points.append(p)
            current = tuple(dest)
        return Route(points, speed, special)

    @staticmethod
    def segment_points(a, b, step=25):
        """Sample points along the axis-aligned segment from ``a`` to ``b``."""
        ax, ay = a
        bx, by = b
        pts = [(ax, ay)]
        dist = abs(bx - ax) + abs(by - ay)
        if dist == 0:
            return pts
        n = max(1, int(math.ceil(dist / float(step))))
        for i in range(1, n + 1):
            f = i / float(n)
            pts.append((ax + (bx - ax) * f, ay + (by - ay) * f))
        return pts
