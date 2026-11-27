"""Grid-based path planning that prefers moving along streets."""

import math

from grid_map import CELL_SIZE, MAP_SIZE

DEFAULT_SPEED = 50


def manhattan(a, b):
    """Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class RoutePoint:
    """A waypoint in a route."""

    def __init__(self, x, y, sequence):
        self.x = x
        self.y = y
        self.sequence = sequence

    def as_tuple(self):
        """Return (x, y)."""
        return (self.x, self.y)

    def __repr__(self):
        return "RoutePoint(%d, %d, #%d)" % (self.x, self.y, self.sequence)


class Route:
    """A sequence of axis-aligned waypoints with distance/time estimates."""

    def __init__(self, points, speed=DEFAULT_SPEED, special_case=False):
        self.points = [RoutePoint(p[0], p[1], i) for i, p in enumerate(points)]
        self.total_distance = sum(
            manhattan(points[i], points[i + 1]) for i in range(len(points) - 1))
        self.speed = speed
        self.estimated_time = (int(math.ceil(self.total_distance / speed))
                               if speed and speed > 0 else 0)
        self.special_case = special_case

    def waypoints(self):
        """Return the waypoints as a list of (x, y) tuples."""
        return [p.as_tuple() for p in self.points]


def _dedupe(points):
    result = []
    for p in points:
        p = (int(p[0]), int(p[1]))
        if not result or result[-1] != p:
            result.append(p)
    return result


class PathPlanner:
    """Plans paths on the 8x8 grid.

    Streets are the grid lines (x or y a multiple of 100). A rider leaves its
    current position onto the nearest street, travels along streets and
    finally enters the target cell. Riders do not block each other (streets
    have unlimited capacity), so no path conflicts or deadlocks can occur.
    """

    def __init__(self, grid_map=None):
        self.grid_map = grid_map

    @staticmethod
    def nearest_street(value, toward=None):
        """Return the street line coordinate nearest to ``value``.

        If ``toward`` is given, the street in the direction of ``toward`` is
        chosen. Values already on a street are returned unchanged.
        """
        if value % CELL_SIZE == 0:
            return value
        low = (value // CELL_SIZE) * CELL_SIZE
        high = min(low + CELL_SIZE, MAP_SIZE)
        if toward is not None and toward != value:
            return high if toward > value else low
        return low if value - low <= high - value else high

    def _waypoints(self, start, end):
        """Return (waypoints, special_case) from start to end."""
        sx, sy = start
        tx, ty = end
        if (sx, sy) == (tx, ty):
            return [start], False
        special = False
        if sx == tx:
            # Special case: target directly above or below.
            if sx % CELL_SIZE == 0:
                pts = [start, end]
            else:
                xs = self.nearest_street(sx)
                pts = [start, (xs, sy), (xs, ty), end]
                special = True
        elif sy == ty:
            if sy % CELL_SIZE == 0:
                pts = [start, end]
            else:
                ys = self.nearest_street(sy)
                pts = [start, (sx, ys), (tx, ys), end]
        else:
            ys = self.nearest_street(sy, ty)
            pts = [start, (sx, ys), (tx, ys), end]
        return _dedupe(pts), special

    def plan(self, start, end, speed=DEFAULT_SPEED):
        """Plan a route from ``start`` to ``end``."""
        pts, special = self._waypoints(tuple(start), tuple(end))
        return Route(pts, speed, special)

    def plan_multi(self, start, destinations, speed=DEFAULT_SPEED):
        """Plan a continuous route through several destinations in order."""
        pts = [tuple(start)]
        special = False
        current = tuple(start)
        for dest in destinations:
            seg, sp = self._waypoints(current, tuple(dest))
            pts.extend(seg[1:])
            special = special or sp
            current = tuple(dest)
        return Route(_dedupe(pts), speed, special)
