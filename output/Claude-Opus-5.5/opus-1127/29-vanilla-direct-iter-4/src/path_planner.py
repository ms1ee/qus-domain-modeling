"""Grid based path planning for riders.

The map is an 800x800 coordinate system split into an 8x8 grid of
100x100 cells.  Restaurants and customers are located at cell centres.
Riders move horizontally first and then vertically (right-angle turns);
when a rider is directly above or below its target it moves straight
vertically (the "special case").
"""

import math

CELL_SIZE = 100
MAP_SIZE = 800
GRID_DIM = MAP_SIZE // CELL_SIZE


class PathPlanner:
    """Collection of path planning helpers (all static/class methods)."""

    @staticmethod
    def to_grid_center_value(value):
        """Convert one coordinate to the centre of its grid cell.

        ``center = (v // 100) * 100 + 50``; values outside 0-800 are clamped
        and 800 is treated as belonging to the last cell.
        """
        v = int(value)
        if v < 0:
            v = 0
        if v >= MAP_SIZE:
            v = MAP_SIZE - 1
        return (v // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2

    @classmethod
    def to_grid_center(cls, pos):
        """Convert an (x, y) pair to its grid cell centre."""
        return (cls.to_grid_center_value(pos[0]),
                cls.to_grid_center_value(pos[1]))

    @staticmethod
    def grid_index(pos):
        """Return the (column, row) grid cell index of a position."""
        def idx(v):
            i = int(v) // CELL_SIZE
            return max(0, min(GRID_DIM - 1, i))
        return idx(pos[0]), idx(pos[1])

    @staticmethod
    def manhattan(a, b):
        """Manhattan (street) distance between two points."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def euclidean(a, b):
        """Euclidean distance between two points."""
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @staticmethod
    def is_on_street(pos):
        """True when the position lies on a grid line (a street)."""
        return pos[0] % CELL_SIZE == 0 or pos[1] % CELL_SIZE == 0

    @staticmethod
    def is_special_case(x, y, tx, ty):
        """True when the rider is directly above or below the target."""
        return x == tx and y != ty

    @staticmethod
    def plan_route(start, target):
        """Return the waypoints of the right-angle route start -> target."""
        sx, sy = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        points = [(sx, sy)]
        if sx != tx and sy != ty:
            points.append((tx, sy))
        if points[-1] != (tx, ty):
            points.append((tx, ty))
        return points

    @classmethod
    def plan_multi_route(cls, start, stops):
        """Plan a continuous route through several stops in order."""
        points = [(int(start[0]), int(start[1]))]
        for stop in stops:
            segment = cls.plan_route(points[-1], stop)
            points.extend(segment[1:])
        return points

    @classmethod
    def route_length(cls, points):
        """Total length of a polyline made of axis aligned segments."""
        total = 0
        for a, b in zip(points, points[1:]):
            total += cls.manhattan(a, b)
        return total

    @staticmethod
    def next_step(x, y, tx, ty, speed):
        """Advance one tick from (x, y) towards (tx, ty).

        Horizontal movement comes first; leftover movement budget is used
        to turn the corner vertically.  The rider never overshoots the
        target.  A non-positive speed is treated as 1 so that a rider
        always makes progress (deadlock avoidance).
        """
        budget = int(speed) if speed and int(speed) > 0 else 1
        x, y, tx, ty = int(x), int(y), int(tx), int(ty)
        if x != tx:
            d = min(budget, abs(tx - x))
            x += d if tx > x else -d
            budget -= d
        if budget > 0 and y != ty:
            d = min(budget, abs(ty - y))
            y += d if ty > y else -d
        return x, y
