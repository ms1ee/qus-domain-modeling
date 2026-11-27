"""Grid based path planning.

The map is 800x800 units split into 8x8 cells of 100x100 units.  Lines where
x or y is a multiple of 100 are streets; cell centres (x % 100 == 50) are the
restaurant / customer locations.  Paths are built from axis aligned segments
that prefer travelling along streets.
"""

import math

MAP_SIZE = 800
CELL_SIZE = 100


class PathPlanner:
    """Pathfinding helpers (all static)."""

    @staticmethod
    def clamp(v, lo=0, hi=MAP_SIZE):
        """Clamp ``v`` into [lo, hi]."""
        return max(lo, min(hi, v))

    @staticmethod
    def to_grid_center(x, y):
        """Convert a coordinate to the centre of its grid cell.

        ``center = (v // 100) * 100 + 50``; values are clamped so that the
        boundary value 800 maps to the last cell (750).
        """
        def conv(v):
            v = int(v)
            v = PathPlanner.clamp(v, 0, MAP_SIZE - 1)
            return (v // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2
        return conv(x), conv(y)

    @staticmethod
    def grid_cell(x, y):
        """Return the (column, row) index of the cell containing (x, y)."""
        cx = PathPlanner.clamp(int(x), 0, MAP_SIZE - 1) // CELL_SIZE
        cy = PathPlanner.clamp(int(y), 0, MAP_SIZE - 1) // CELL_SIZE
        return cx, cy

    @staticmethod
    def is_street(v):
        """True if coordinate value ``v`` lies on a street line."""
        return v % CELL_SIZE == 0

    @staticmethod
    def street_toward(v, target):
        """Street line adjacent to ``v`` in the direction of ``target``."""
        if v % CELL_SIZE == 0:
            return PathPlanner.clamp(v)
        if target > v:
            s = (v // CELL_SIZE + 1) * CELL_SIZE
        else:
            s = (v // CELL_SIZE) * CELL_SIZE
        return PathPlanner.clamp(s)

    @staticmethod
    def _clean(start, points):
        """Remove duplicate and collinear intermediate waypoints."""
        result = []
        prev = start
        for p in points:
            if p == prev:
                continue
            result.append(p)
            prev = p
        # remove collinear middle points
        cleaned = []
        pts = [start] + result
        for i in range(1, len(pts)):
            if i + 1 < len(pts):
                a, b, c = pts[i - 1], pts[i], pts[i + 1]
                if (a[0] == b[0] == c[0] and (b[1] - a[1]) * (c[1] - b[1]) > 0) or \
                        (a[1] == b[1] == c[1] and (b[0] - a[0]) * (c[0] - b[0]) > 0):
                    continue
            cleaned.append(pts[i])
        return cleaned

    @staticmethod
    def plan(start, end):
        """Plan a path from ``start`` to ``end``.

        Returns a list of waypoints (excluding ``start``, including ``end``);
        each consecutive pair of points forms an axis-aligned segment.

        Strategy:
          * already on a common street -> straight line.
          * otherwise: hop onto the horizontal street next to the start,
            travel to the vertical street next to the end, travel along it to
            the horizontal street next to the end, then enter the destination.
          * when the start is directly above/below the end (same x off a
            street) this produces a detour via the neighbouring vertical
            street (special case handling).
        """
        sx, sy = int(start[0]), int(start[1])
        ex, ey = int(end[0]), int(end[1])
        if (sx, sy) == (ex, ey):
            return []
        if sx == ex and PathPlanner.is_street(sx):
            return [(ex, ey)]
        if sy == ey and PathPlanner.is_street(sy):
            return [(ex, ey)]
        yh = PathPlanner.street_toward(sy, ey)
        xv = PathPlanner.street_toward(ex, sx)
        ye = PathPlanner.street_toward(ey, sy)
        raw = [(sx, yh), (xv, yh), (xv, ye), (ex, ye), (ex, ey)]
        return PathPlanner._clean((sx, sy), raw)

    @staticmethod
    def plan_multi(points):
        """Plan a continuous path through several destinations.

        ``points[0]`` is the start; returns the concatenated waypoint list.
        """
        path = []
        if not points:
            return path
        cur = tuple(points[0])
        for p in points[1:]:
            p = (int(p[0]), int(p[1]))
            path.extend(PathPlanner.plan(cur, p))
            cur = p
        return path

    @staticmethod
    def path_length(start, path):
        """Total Manhattan length of ``path`` starting from ``start``."""
        total = 0
        cur = start
        for p in path:
            total += abs(p[0] - cur[0]) + abs(p[1] - cur[1])
            cur = p
        return total

    @staticmethod
    def route_distance(start, end):
        """Length of the planned path between two points."""
        return PathPlanner.path_length(tuple(start), PathPlanner.plan(start, end))

    @staticmethod
    def euclidean(a, b):
        """Euclidean distance between two points."""
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    @staticmethod
    def estimate_ticks(length, speed):
        """Number of ticks required to cover ``length`` at ``speed``."""
        if speed <= 0:
            return 0
        return int(math.ceil(length / speed))
