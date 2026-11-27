"""Grid based path planning along streets."""

import math

from grid_map import CELL_SIZE, MAP_SIZE


def path_length(points):
    """Total Manhattan length of a poly-line."""
    total = 0
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        total += abs(bx - ax) + abs(by - ay)
    return total


class PathPoint:
    """A waypoint of a route."""

    __slots__ = ("x", "y", "sequence")

    def __init__(self, x, y, sequence=0):
        self.x = int(x)
        self.y = int(y)
        self.sequence = sequence

    def as_tuple(self):
        """Return (x, y)."""
        return (self.x, self.y)

    def __repr__(self):
        return "PathPoint(%d, %d, #%d)" % (self.x, self.y, self.sequence)


class Route:
    """A planned route: ordered waypoints plus distance and time estimate."""

    def __init__(self, points, speed=50, stops=None):
        pts = [(int(x), int(y)) for x, y in points]
        self.points = [PathPoint(x, y, i) for i, (x, y) in enumerate(pts)]
        self.speed = max(1, int(speed))
        self.stops = list(stops or [])
        self.total_distance = path_length(pts)
        self.estimated_time = int(math.ceil(self.total_distance / self.speed))

    @property
    def coordinates(self):
        """Waypoints as a list of tuples."""
        return [p.as_tuple() for p in self.points]

    def to_dict(self):
        """Serializable representation."""
        return {"points": self.coordinates, "speed": self.speed,
                "total_distance": self.total_distance,
                "estimated_time": self.estimated_time}


class PathPlanner:
    """Plans paths that follow streets (grid lines).

    Restaurants/customers sit at cell centers and are reached by a short
    vertical spur from the horizontal street directly above or below them.
    """

    def __init__(self, cell_size=CELL_SIZE, map_size=MAP_SIZE):
        self.cell_size = cell_size
        self.map_size = map_size

    def is_on_street(self, x, y):
        """True if the point lies on a grid line."""
        return x % self.cell_size == 0 or y % self.cell_size == 0

    @staticmethod
    def is_directly_above_or_below(start, target):
        """Special case: same x, different y."""
        return start[0] == target[0] and start[1] != target[1]

    def _clamp(self, v):
        return max(0, min(self.map_size, v))

    def _line_toward(self, a, b):
        """Nearest grid line from ``a`` in the direction of ``b``."""
        cs = self.cell_size
        if a % cs == 0:
            return a
        if b > a:
            return self._clamp((a // cs + 1) * cs)
        return self._clamp((a // cs) * cs)

    def _street_route(self, p, e):
        """Route between two points that both lie on streets."""
        px, py = p
        ex, ey = e
        if p == e:
            return []
        cs = self.cell_size
        p_h, p_v = py % cs == 0, px % cs == 0
        e_h, e_v = ey % cs == 0, ex % cs == 0
        if p_h and e_h and py == ey:
            return [e]
        if p_v and e_v and px == ex:
            return [e]
        if p_v and e_h:
            return [(px, ey), e]
        if p_h and e_v:
            return [(ex, py), e]
        if p_h and e_h:
            v = self._line_toward(px, ex)
            return [(v, py), (v, ey), e]
        h = self._line_toward(py, ey)
        return [(px, h), (ex, h), e]

    @staticmethod
    def _simplify(points):
        """Remove duplicate and collinear intermediate points."""
        dedup = []
        for pt in points:
            if not dedup or dedup[-1] != pt:
                dedup.append(pt)
        if len(dedup) < 3:
            return dedup
        result = [dedup[0]]
        for i in range(1, len(dedup) - 1):
            a, b, c = result[-1], dedup[i], dedup[i + 1]
            if a[0] == b[0] == c[0] and min(a[1], c[1]) <= b[1] <= max(a[1], c[1]):
                continue
            if a[1] == b[1] == c[1] and min(a[0], c[0]) <= b[0] <= max(a[0], c[0]):
                continue
            result.append(b)
        result.append(dedup[-1])
        return result

    def find_path(self, start, target):
        """Return a list of waypoints (including start) from start to target."""
        sx, sy = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        cs = self.cell_size
        points = [(sx, sy)]
        if (sx, sy) == (tx, ty):
            return points
        cur = (sx, sy)
        if not self.is_on_street(sx, sy):
            # leave the cell vertically towards the target
            cur = (sx, self._line_toward(sy, ty))
            points.append(cur)
            if cur == (tx, ty):
                return self._simplify(points)
        if self.is_on_street(tx, ty):
            entry, spur = (tx, ty), False
        else:
            if cur[1] < ty:
                ey = (ty // cs) * cs
            elif cur[1] > ty:
                ey = (ty // cs + 1) * cs
            else:
                ey = (ty // cs) * cs
            entry, spur = (tx, self._clamp(ey)), True
        points.extend(self._street_route(cur, entry))
        if spur:
            points.append((tx, ty))
        return self._simplify(points)

    def distance(self, start, target):
        """Street distance between two points."""
        return path_length(self.find_path(start, target))

    def plan_route(self, start, destinations, speed=50):
        """Plan a continuous route through several destinations."""
        points = [(int(start[0]), int(start[1]))]
        cur = points[0]
        for dest in destinations:
            seg = self.find_path(cur, dest)
            points.extend(seg[1:])
            cur = (int(dest[0]), int(dest[1]))
        return Route(self._simplify(points) if len(points) > 1 else points,
                     speed, stops=[tuple(d) for d in destinations])
