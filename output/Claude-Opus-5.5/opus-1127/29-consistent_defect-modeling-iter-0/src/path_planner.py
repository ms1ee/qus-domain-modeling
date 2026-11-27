"""Grid based path planning.

Routes consist of axis-aligned waypoints, preferring streets (lines where x or
y is a multiple of the cell size).  Riders never block each other, so there
are no path conflicts or deadlocks: every rider can always progress along its
own route.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple

try:
    from . import config
except ImportError:  # pragma: no cover
    import config


@dataclass
class Waypoint:
    """A single point on a route."""
    x: int
    y: int
    sequence: int = 0


@dataclass
class Route:
    """A full route with its estimated travel time."""
    start: Tuple[int, int]
    waypoints: List[Waypoint] = field(default_factory=list)
    length: int = 0
    estimated_time: int = 0

    def points(self):
        """Return the route as a list of (x, y) including the start."""
        return [self.start] + [(w.x, w.y) for w in self.waypoints]


class PathPlanner:
    """Computes street-preferring axis-aligned routes."""

    def __init__(self, cell_size=config.CELL_SIZE, map_size=config.MAP_SIZE):
        self.cell_size = cell_size
        self.map_size = map_size

    @staticmethod
    def _pt(p):
        return int(p[0]), int(p[1])

    def is_on_street(self, x, y):
        """True when x or y aligns with a grid line."""
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def is_vertical_special(self, start, end):
        """Special case: the rider is directly above or below the target."""
        sx, sy = self._pt(start)
        ex, ey = self._pt(end)
        return sx == ex and sy != ey

    def nearest_street(self, value):
        """Return the nearest grid line coordinate to ``value``."""
        line = int(round(value / self.cell_size)) * self.cell_size
        return min(max(line, 0), self.map_size)

    def plan_route(self, start, end):
        """Return waypoints (excluding start, including end) from start to end."""
        sx, sy = self._pt(start)
        ex, ey = self._pt(end)
        if (sx, sy) == (ex, ey):
            return []
        if sx == ex or sy == ey:
            # straight line (includes the directly above/below special case)
            return [(ex, ey)]
        if sy % self.cell_size == 0:
            pts = [(ex, sy), (ex, ey)]
        elif sx % self.cell_size == 0:
            pts = [(sx, ey), (ex, ey)]
        else:
            street_y = self.nearest_street(sy)
            pts = [(sx, street_y), (ex, street_y), (ex, ey)]
        return self._dedupe((sx, sy), pts)

    @staticmethod
    def _dedupe(start, pts):
        out = []
        prev = start
        for p in pts:
            if p != prev:
                out.append(p)
                prev = p
        return out

    def plan_multi(self, start, stops):
        """Plan a continuous route visiting all ``stops`` in order."""
        cur = self._pt(start)
        out = []
        for stop in stops:
            stop = self._pt(stop)
            out.extend(self.plan_route(cur, stop))
            cur = stop
        return out

    def route_length(self, start, waypoints):
        """Manhattan length of a route."""
        total = 0
        cx, cy = self._pt(start)
        for p in waypoints:
            px, py = self._pt(p)
            total += abs(px - cx) + abs(py - cy)
            cx, cy = px, py
        return total

    def estimate_time(self, start, waypoints, speed):
        """Number of ticks required to traverse a route at ``speed``."""
        if speed <= 0:
            return 0
        return int(math.ceil(self.route_length(start, waypoints) / speed))

    def build_route(self, start, stops, speed):
        """Build a Route object visiting ``stops``."""
        pts = self.plan_multi(start, stops)
        wps = [Waypoint(x, y, i) for i, (x, y) in enumerate(pts)]
        length = self.route_length(start, pts)
        est = int(math.ceil(length / speed)) if speed > 0 else 0
        return Route(self._pt(start), wps, length, est)
