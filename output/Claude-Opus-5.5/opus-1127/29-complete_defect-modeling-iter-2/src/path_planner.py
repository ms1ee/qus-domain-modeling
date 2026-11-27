"""Grid-based path planning along streets.

Streets are the grid lines (x or y a multiple of the cell size).  Riders
leave their current location towards the nearest horizontal street, travel
along streets and finally enter the destination cell.  When the rider is
directly above or below the target (same non-street x column) a detour via
the nearest vertical street is used (special case).  Riders never block each
other, which avoids path conflicts and deadlocks by construction.
"""

import math

from grid_map import CELL_SIZE, MAP_SIZE


class RoutePoint:
    """A waypoint on a route."""

    def __init__(self, x, y, sequence):
        self.x = x
        self.y = y
        self.sequence = sequence

    def __repr__(self):
        return "RoutePoint(%d, %d, #%d)" % (self.x, self.y, self.sequence)


class Route:
    """A connected sequence of waypoints with distance and time estimate."""

    def __init__(self, points, speed, order_id=None):
        self.points = [RoutePoint(x, y, i) for i, (x, y) in enumerate(points)]
        self.order_id = order_id
        self.speed = speed
        self.total_distance = PathPlanner.path_length(points)
        self.estimated_time = (int(math.ceil(self.total_distance / float(speed)))
                               if speed and speed > 0 else 0)

    def as_tuples(self):
        """Return the waypoints as a list of (x, y) tuples."""
        return [(p.x, p.y) for p in self.points]


class PathPlanner:
    """Plans right-angle routes along the street grid."""

    def __init__(self, cell_size=CELL_SIZE, map_size=MAP_SIZE):
        self.cell_size = cell_size
        self.map_size = map_size

    # ------------------------------------------------------------------ utils
    def _clamp(self, v):
        return max(0, min(self.map_size, int(v)))

    def nearest_street(self, v):
        """Nearest street line coordinate to ``v``."""
        c = self.cell_size
        return self._clamp(((int(v) + c // 2) // c) * c)

    def _street_towards(self, px, qx):
        """Vertical street from px heading towards qx."""
        c = self.cell_size
        if px % c == 0:
            return px
        if qx % c == 0:
            return qx
        if qx > px:
            return self._clamp(((px // c) + 1) * c)
        if qx < px:
            return self._clamp((px // c) * c)
        return self.nearest_street(px)

    @staticmethod
    def path_length(points):
        """Manhattan length of a polyline."""
        total = 0
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            total += abs(x2 - x1) + abs(y2 - y1)
        return total

    @staticmethod
    def _clean(points):
        """Remove duplicate and collinear intermediate points."""
        dedup = []
        for p in points:
            if not dedup or dedup[-1] != p:
                dedup.append(p)
        if len(dedup) < 3:
            return dedup
        out = [dedup[0]]
        for i in range(1, len(dedup) - 1):
            a, b, c = out[-1], dedup[i], dedup[i + 1]
            collinear = (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1])
            between = (min(a[0], c[0]) <= b[0] <= max(a[0], c[0]) and
                       min(a[1], c[1]) <= b[1] <= max(a[1], c[1]))
            if collinear and between:
                continue
            out.append(b)
        out.append(dedup[-1])
        return out

    # --------------------------------------------------------------- planning
    def plan_path_with_flag(self, start, end):
        """Plan a path; return (points, special_case_flag)."""
        sx, sy = int(start[0]), int(start[1])
        tx, ty = int(end[0]), int(end[1])
        c = self.cell_size
        if (sx, sy) == (tx, ty):
            return [(sx, sy)], False
        # Same street line: straight movement.
        if (sy == ty and sy % c == 0) or (sx == tx and sx % c == 0):
            return [(sx, sy), (tx, ty)], False

        points = [(sx, sy)]
        special = False
        # Exit to a horizontal street.
        if sy % c == 0:
            p = (sx, sy)
        else:
            p = (sx, self.nearest_street(sy))
        points.append(p)
        # Entry point on a horizontal street near the target.
        if ty % c == 0:
            q = (tx, ty)
        else:
            q = (tx, self.nearest_street(ty))
        px, py = p
        qx, qy = q
        if py != qy:
            if px == qx and px % c != 0:
                special = True  # directly above / below the target
            vx = self._street_towards(px, qx)
            points.append((vx, py))
            points.append((vx, qy))
        points.append(q)
        points.append((tx, ty))
        return self._clean(points), special

    def plan_path(self, start, end):
        """Plan a street-following path from ``start`` to ``end``."""
        return self.plan_path_with_flag(start, end)[0]

    def is_special_case(self, start, end):
        """True if the path needs the above/below detour."""
        return self.plan_path_with_flag(start, end)[1]

    def distance(self, start, end):
        """Length of the planned path between two points."""
        return self.path_length(self.plan_path(start, end))

    def plan_route(self, start, destinations, speed, order_id=None):
        """Plan a continuous multi-destination route and return a Route."""
        points = [tuple(start)]
        current = tuple(start)
        for dest in destinations:
            seg = self.plan_path(current, dest)
            points.extend(seg[1:])
            current = tuple(dest)
        return Route(self._clean(points) if len(points) > 1 else points,
                     speed, order_id)
