"""Grid-based path planning.

Routes prefer streets (grid lines).  A route from a start point to a goal
cell center is built as:

1. a short vertical hop onto the horizontal street nearest the start
   (in the direction of the goal),
2. a horizontal run along that street to the vertical street bordering the
   goal cell (on the side facing the start),
3. a vertical run along that street to the goal's y coordinate,
4. a short horizontal hop into the goal cell center.

When the rider is directly above or below the target (same x), the route
leaves the block sideways onto the neighbouring street, travels vertically
and re-enters -- this is flagged as a *special case*.

Riders never block each other (streets have unlimited capacity), so path
conflicts and deadlocks cannot occur.
"""

from grid_map import CELL_SIZE, MAP_SIZE


class Waypoint:
    """A point along a route."""

    def __init__(self, x, y, sequence):
        self.x = x
        self.y = y
        self.sequence = sequence

    def __repr__(self):
        return "Waypoint(%d, %d, #%d)" % (self.x, self.y, self.sequence)


def manhattan(a, b):
    """Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Route:
    """A polyline route made of axis-aligned segments."""

    def __init__(self, points, special_case=False):
        self.points = [tuple(p) for p in points]
        self.special_case = special_case

    @property
    def total_distance(self):
        """Total length of the route in map units."""
        return sum(manhattan(self.points[i], self.points[i + 1])
                   for i in range(len(self.points) - 1))

    @property
    def waypoints(self):
        """Route points as :class:`Waypoint` objects."""
        return [Waypoint(p[0], p[1], i) for i, p in enumerate(self.points)]

    def estimated_time(self, speed):
        """Estimated ticks needed at ``speed`` units/tick (ceiling)."""
        if speed <= 0:
            return 0
        return -(-self.total_distance // speed)

    def extend(self, other):
        """Append another route that starts where this one ends."""
        pts = other.points
        if self.points and pts and self.points[-1] == pts[0]:
            pts = pts[1:]
        self.points = _simplify(self.points + list(pts))
        self.special_case = self.special_case or other.special_case
        return self

    def __repr__(self):
        return "Route(%s, dist=%d)" % (self.points, self.total_distance)


def _simplify(points):
    """Remove duplicate consecutive points and collinear middle points."""
    out = []
    for p in points:
        if out and out[-1] == p:
            continue
        out.append(p)
    i = 1
    while i < len(out) - 1:
        a, b, c = out[i - 1], out[i], out[i + 1]
        if (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1]):
            # Only collapse if b lies between a and c (no U-turn).
            if min(a[0], c[0]) <= b[0] <= max(a[0], c[0]) and \
                    min(a[1], c[1]) <= b[1] <= max(a[1], c[1]):
                out.pop(i)
                continue
        i += 1
    return out


class PathPlanner:
    """Street-preferring path planner on the 8x8 grid."""

    def __init__(self, cell_size=CELL_SIZE, map_size=MAP_SIZE):
        self.cell_size = cell_size
        self.map_size = map_size

    def _line_toward(self, value, target):
        """Nearest grid line to ``value`` lying toward ``target``."""
        cs = self.cell_size
        if value % cs == 0:
            return value
        lo = (value // cs) * cs
        hi = min(lo + cs, self.map_size)
        return hi if target > value else lo

    def plan(self, start, goal):
        """Plan a route from ``start`` to ``goal``; returns a :class:`Route`."""
        sx, sy = int(start[0]), int(start[1])
        gx, gy = int(goal[0]), int(goal[1])
        if (sx, sy) == (gx, gy):
            return Route([(sx, sy)], False)
        special = (sx == gx)
        hy = self._line_toward(sy, gy)
        vx = self._line_toward(gx, sx)
        points = [(sx, sy), (sx, hy), (vx, hy), (vx, gy), (gx, gy)]
        return Route(_simplify(points), special)

    def plan_multi(self, points):
        """Plan a continuous route through several destinations."""
        points = [tuple(p) for p in points]
        if not points:
            return Route([], False)
        route = Route([points[0]], False)
        for i in range(len(points) - 1):
            route.extend(self.plan(points[i], points[i + 1]))
        return route

    def distance(self, start, goal):
        """Street distance between two points."""
        return self.plan(start, goal).total_distance
