"""Grid-based path planning."""

import math

from gridmap import CELL_SIZE, GridMap


class Route:
    """A polyline route made of axis-aligned segments."""

    def __init__(self, points, speed=20):
        self.points = [tuple(p) for p in points]
        self.speed = speed

    @property
    def length(self):
        total = 0
        for (x1, y1), (x2, y2) in zip(self.points, self.points[1:]):
            total += abs(x2 - x1) + abs(y2 - y1)
        return total

    @property
    def estimated_time(self):
        if self.speed <= 0:
            return 0
        return int(math.ceil(self.length / float(self.speed)))

    def __repr__(self):
        return "Route(points=%r, length=%d)" % (self.points, self.length)


class PathPlanner:
    """Plans routes that prefer streets (grid lines).

    Riders never block each other (roads have unlimited capacity), so
    path conflicts and deadlocks cannot occur; every route is a finite
    sequence of axis-aligned segments.
    """

    def __init__(self, cell_size=CELL_SIZE, grid_map=None):
        self.cell_size = cell_size
        self.grid_map = grid_map or GridMap(cell_size=cell_size)

    def is_on_street(self, x, y):
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def plan(self, start, end, speed=20):
        """Plan a street-following route from ``start`` to ``end``."""
        sx, sy = int(start[0]), int(start[1])
        tx, ty = int(end[0]), int(end[1])
        c = self.cell_size
        points = [(sx, sy)]
        x, y = sx, sy
        # Special case: rider is off-street -> move to nearest vertical street.
        if x % c != 0 and y % c != 0:
            x = int(round(x / float(c))) * c
            points.append((x, y))
        if x == tx:
            # Directly above/below the target: straight vertical move.
            points.append((tx, ty))
        elif y == ty and y % c == 0:
            points.append((tx, ty))
        elif x % c == 0:
            if ty % c == 0:
                points.append((x, ty))
                points.append((tx, ty))
            else:
                # target off-street: go horizontally along nearest street row
                ny = int(round(y / float(c))) * c if y % c else y
                points.append((x, ny))
                points.append((tx, ny))
                points.append((tx, ty))
        else:  # on a horizontal street
            if tx % c == 0:
                points.append((tx, y))
                points.append((tx, ty))
            else:
                nx = int(round(x / float(c))) * c
                points.append((nx, y))
                points.append((nx, ty))
                points.append((tx, ty))
        return Route(self._dedupe(points), speed)

    def plan_multi(self, start, destinations, speed=20):
        """Plan a continuous route through several destinations."""
        points = [tuple(start)]
        cur = tuple(start)
        for dest in destinations:
            leg = self.plan(cur, dest, speed)
            points.extend(leg.points[1:])
            cur = tuple(dest)
        return Route(self._dedupe(points), speed)

    @staticmethod
    def _dedupe(points):
        result = []
        for p in points:
            p = (int(p[0]), int(p[1]))
            if not result or result[-1] != p:
                result.append(p)
        return result
