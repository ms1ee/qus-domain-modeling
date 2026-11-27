"""Grid based path planning along streets."""

import math
from dataclasses import dataclass, field

from grid_map import CELL_SIZE, MAP_SIZE, clamp


@dataclass
class Route:
    """A planned route: waypoints (excluding start), distance and time."""
    start: tuple = (0, 0)
    waypoints: list = field(default_factory=list)
    distance: int = 0
    estimated_time: int = 0


def _floor_line(v):
    return (int(v) // CELL_SIZE) * CELL_SIZE


def _ceil_line(v):
    f = _floor_line(v)
    return f if f == v else f + CELL_SIZE


def manhattan(a, b):
    """Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class PathPlanner:
    """Plans right-angle routes that stay on streets whenever possible.

    Only the first leg (leaving a cell centre) and the last leg (entering
    the target cell centre) leave the street network.
    """

    @staticmethod
    def is_special_case(start, target):
        """Rider directly above/below the target, not on a vertical street."""
        sx, sy = start
        tx, ty = target
        return sx == tx and sy != ty and sx % CELL_SIZE != 0

    def plan(self, start, target):
        """Return list of waypoints from ``start`` to ``target`` (start excluded)."""
        start = (int(start[0]), int(start[1]))
        target = (int(target[0]), int(target[1]))
        if start == target:
            return []
        sx, sy = start
        tx, ty = target
        points = []

        # Access point on the street next to the target.
        if tx % CELL_SIZE == 0 or ty % CELL_SIZE == 0:
            access = target
            final_leg = False
        else:
            lo = _floor_line(ty)
            hi = lo + CELL_SIZE
            ay = lo if abs(sy - lo) <= abs(sy - hi) else hi
            access = (tx, ay)
            final_leg = True

        # Leave the current cell centre to reach a street.
        current = start
        if sx % CELL_SIZE != 0 and sy % CELL_SIZE != 0:
            lo = _floor_line(sy)
            hi = min(lo + CELL_SIZE, MAP_SIZE)
            ref = access[1]
            if ref < sy:
                ey = lo
            elif ref > sy:
                ey = hi
            else:
                ey = lo if sy - lo <= hi - sy else hi
            current = (sx, ey)
            points.append(current)

        points.extend(self._street_route(current, access))
        if final_leg:
            points.append(target)
        return self._compress(start, points)

    def _street_route(self, p, a):
        """Route between two points that both lie on streets."""
        if p == a:
            return []
        px, py = p
        ax, ay = a
        ph = py % CELL_SIZE == 0
        pv = px % CELL_SIZE == 0
        ah = ay % CELL_SIZE == 0
        av = ax % CELL_SIZE == 0
        if ph and ah and py == ay:
            return [a]
        if pv and av and px == ax:
            return [a]
        if ph and av:
            return [(ax, py), a]
        if pv and ah:
            return [(px, ay), a]
        if ph and ah:
            cands = {clamp(_floor_line(px)), clamp(_ceil_line(px)),
                     clamp(_floor_line(ax)), clamp(_ceil_line(ax))}
            vx = min(cands, key=lambda v: (abs(px - v) + abs(v - ax), v))
            return [(vx, py), (vx, ay), a]
        cands = {clamp(_floor_line(py)), clamp(_ceil_line(py)),
                 clamp(_floor_line(ay)), clamp(_ceil_line(ay))}
        hy = min(cands, key=lambda v: (abs(py - v) + abs(v - ay), v))
        return [(px, hy), (ax, hy), a]

    @staticmethod
    def _compress(start, points):
        """Remove duplicate and redundant (collinear, in-between) waypoints."""
        dedup = []
        prev = start
        for p in points:
            if p != prev:
                dedup.append(p)
                prev = p
        full = [start] + dedup
        result = []
        last_kept = start
        for i in range(1, len(full)):
            if i < len(full) - 1:
                a, b, c = last_kept, full[i], full[i + 1]
                if a[0] == b[0] == c[0] and \
                        min(a[1], c[1]) <= b[1] <= max(a[1], c[1]):
                    continue
                if a[1] == b[1] == c[1] and \
                        min(a[0], c[0]) <= b[0] <= max(a[0], c[0]):
                    continue
            result.append(full[i])
            last_kept = full[i]
        return result

    @staticmethod
    def path_length(start, waypoints):
        """Total Manhattan length of a waypoint list starting at ``start``."""
        total = 0
        prev = start
        for p in waypoints:
            total += manhattan(prev, p)
            prev = p
        return total

    def distance(self, start, target):
        """Street distance between two points."""
        return self.path_length(start, self.plan(start, target))

    def plan_multi(self, start, targets, speed=None):
        """Plan a continuous route through several destinations."""
        waypoints = []
        current = (int(start[0]), int(start[1]))
        for t in targets:
            leg = self.plan(current, t)
            waypoints.extend(leg)
            current = (int(t[0]), int(t[1]))
        dist = self.path_length(start, waypoints)
        est = int(math.ceil(dist / speed)) if speed else 0
        return Route(start=tuple(start), waypoints=waypoints,
                     distance=dist, estimated_time=est)
