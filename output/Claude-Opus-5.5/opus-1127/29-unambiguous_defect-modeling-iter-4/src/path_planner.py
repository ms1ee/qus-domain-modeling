"""Grid-based path planning restricted to streets."""

import math

from grid_map import CELL_SIZE


class Route:
    """A planned route: ordered list of axis-aligned waypoints."""

    def __init__(self, points, speed=50):
        self.points = list(points)
        self.speed = max(1, int(speed))

    @property
    def length(self):
        """Total route length in map units."""
        return PathPlanner.route_length(self.points)

    @property
    def estimated_time(self):
        """Estimated travel time in ticks."""
        return int(math.ceil(self.length / self.speed)) if self.points else 0

    def to_dict(self):
        """Serialise the route."""
        return {
            "points": [list(p) for p in self.points],
            "speed": self.speed,
            "length": self.length,
            "estimated_time": self.estimated_time,
        }


class PathPlanner:
    """Plans street-following routes on the 8x8 grid.

    Riders travel along streets (lines at multiples of 100). Destinations
    located in the middle of a cell are entered from the closest adjacent
    horizontal street. Riders do not block each other, so no path conflicts
    or deadlocks can occur.
    """

    @staticmethod
    def plan(start, target):
        """Plan a route from ``start`` to ``target``.

        Returns a list of waypoints including both start and target. Every
        consecutive pair of waypoints is horizontally or vertically aligned.
        """
        x, y = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        cs = CELL_SIZE
        points = [(x, y)]
        if (x, y) == (tx, ty):
            return points

        # Step 1: if inside a cell (e.g. at a restaurant), go to a horizontal
        # street, preferring the direction of the target.
        if x % cs and y % cs:
            if ty > y:
                ny = (y // cs + 1) * cs
            elif ty < y:
                ny = (y // cs) * cs
            else:
                ny = (y // cs) * cs if y % cs <= cs // 2 else (y // cs + 1) * cs
            y = ny
            points.append((x, y))

        # Entry street for the target.
        if ty % cs == 0:
            ey = ty
        elif y <= ty:
            ey = (ty // cs) * cs
        else:
            ey = (ty // cs + 1) * cs

        if not (y % cs == 0 and y == ey):
            # Need vertical travel -> must be on a vertical street.
            if x % cs:
                if tx % cs == 0:
                    nx = tx
                else:
                    lo = (tx // cs) * cs
                    hi = lo + cs
                    nx = lo if abs(x - lo) <= abs(x - hi) else hi
                x = nx
                points.append((x, y))
            y = ey
            points.append((x, y))
        if x != tx:
            x = tx
            points.append((x, y))
        if y != ty:
            y = ty
            points.append((x, y))
        return PathPlanner._dedupe(points)

    @staticmethod
    def plan_multi(start, targets):
        """Plan a continuous route through several destinations in order."""
        points = [(int(start[0]), int(start[1]))]
        current = points[0]
        for target in targets:
            leg = PathPlanner.plan(current, target)
            points.extend(leg[1:])
            current = (int(target[0]), int(target[1]))
        return PathPlanner._dedupe(points)

    @staticmethod
    def build_route(start, targets, speed=50):
        """Build a :class:`Route` through ``targets`` starting at ``start``."""
        return Route(PathPlanner.plan_multi(start, targets), speed)

    @staticmethod
    def route_length(points):
        """Sum of Manhattan distances between consecutive waypoints."""
        total = 0
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            total += abs(x2 - x1) + abs(y2 - y1)
        return total

    @staticmethod
    def distance(a, b):
        """Street distance between two points."""
        return PathPlanner.route_length(PathPlanner.plan(a, b))

    @staticmethod
    def is_special_case(start, target):
        """True when the start point is inside a cell directly above/below the target."""
        x, y = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        return x == tx and x % CELL_SIZE != 0 and y != ty

    @staticmethod
    def _dedupe(points):
        result = []
        for p in points:
            p = (int(p[0]), int(p[1]))
            if not result or result[-1] != p:
                result.append(p)
        return result
