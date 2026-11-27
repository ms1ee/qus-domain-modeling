"""Grid map definition and grid-based path planning.

Streets run along every line where x or y is a multiple of the cell size.
Restaurants and customers are located at cell centres, and riders reach
them through the midpoint of one of the four streets surrounding the cell.
"""

import math

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIMENSION = MAP_SIZE // CELL_SIZE


def manhattan(a, b):
    """Return the Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class GridMap:
    """8x8 grid over an 800x800 coordinate system."""

    def __init__(self, map_size=MAP_SIZE, cell_size=CELL_SIZE):
        self.map_size = int(map_size)
        self.cell_size = int(cell_size)
        self.grid_dimension = self.map_size // self.cell_size

    def clamp(self, value):
        """Clamp a coordinate to [0, map_size]."""
        return max(0, min(self.map_size, int(round(value))))

    def to_grid_center(self, value):
        """Convert an input coordinate to the centre of its grid cell.

        ``center = (v // 100) * 100 + 50``; the value ``map_size`` (and
        anything beyond) is mapped into the last cell.
        """
        v = max(0, min(self.map_size - 1, int(value)))
        return (v // self.cell_size) * self.cell_size + self.cell_size // 2

    def to_grid_cell(self, value):
        """Return the grid cell index (0..dimension-1) of a coordinate."""
        v = max(0, min(self.map_size - 1, int(value)))
        return v // self.cell_size

    def is_on_street(self, x, y):
        """True when the point lies on a street (grid line)."""
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def in_bounds(self, x, y):
        """True when the point lies inside the map."""
        return 0 <= x <= self.map_size and 0 <= y <= self.map_size


DEFAULT_GRID = GridMap()


def to_grid_center(value):
    """Module-level helper using the default grid."""
    return DEFAULT_GRID.to_grid_center(value)


class Route:
    """A planned route: ordered waypoints with length and estimated time."""

    def __init__(self, waypoints, speed=1):
        self.waypoints = [tuple(p) for p in waypoints]
        self.speed = max(1, int(speed))

    @property
    def length(self):
        """Total route length in map units."""
        return sum(manhattan(self.waypoints[i], self.waypoints[i + 1])
                   for i in range(len(self.waypoints) - 1))

    @property
    def estimated_time(self):
        """Estimated number of ticks needed to travel the route."""
        return int(math.ceil(self.length / float(self.speed)))

    def __repr__(self):
        return "Route(%s, length=%d)" % (self.waypoints, self.length)


class PathPlanner:
    """Plans street-following paths on the grid.

    Riders never block each other (streets have unlimited capacity), so
    planned paths are conflict- and deadlock-free by construction.
    """

    def __init__(self, grid=None):
        self.grid = grid or DEFAULT_GRID

    # ------------------------------------------------------------------ utils
    def _norm(self, p):
        return (self.grid.clamp(p[0]), self.grid.clamp(p[1]))

    @staticmethod
    def simplify(points):
        """Remove duplicate and collinear intermediate waypoints."""
        out = []
        for p in points:
            p = tuple(p)
            if out and out[-1] == p:
                continue
            if len(out) >= 2:
                a, b = out[-2], out[-1]
                if (a[0] == b[0] == p[0]) or (a[1] == b[1] == p[1]):
                    out[-1] = p
                    continue
            out.append(p)
        return out

    @staticmethod
    def length_of(points):
        """Length of a polyline of axis-aligned segments."""
        return sum(manhattan(points[i], points[i + 1])
                   for i in range(len(points) - 1))

    def _anchors(self, p):
        """Intersections reachable straight along the street of ``p``."""
        cs = self.grid.cell_size
        x, y = p
        if x % cs == 0 and y % cs == 0:
            cands = [(x, y)]
        elif x % cs == 0:
            lo = (y // cs) * cs
            cands = [(x, lo), (x, lo + cs)]
        else:
            lo = (x // cs) * cs
            cands = [(lo, y), (lo + cs, y)]
        return [c for c in cands if self.grid.in_bounds(*c)]

    def _snap_points(self, p):
        """Nearest street points for an off-street location."""
        cs = self.grid.cell_size
        x, y = p
        lx = (x // cs) * cs
        ly = (y // cs) * cs
        cands = [(lx, y), (lx + cs, y), (x, ly), (x, ly + cs)]
        return [c for c in cands if self.grid.in_bounds(*c)]

    # --------------------------------------------------------------- planning
    def plan_path(self, start, end):
        """Return the shortest street path from ``start`` to ``end``.

        The returned list contains ``start`` and ``end`` and only right-angle
        turns. Off-street endpoints are first snapped to the nearest street.
        """
        start = self._norm(start)
        end = self._norm(end)
        if start == end:
            return [start]
        g = self.grid
        cs = g.cell_size
        if not g.is_on_street(*start):
            best = None
            for s in self._snap_points(start):
                cand = self.simplify([start] + self.plan_path(s, end))
                if best is None or self.length_of(cand) < self.length_of(best):
                    best = cand
            return best
        if not g.is_on_street(*end):
            best = None
            for e in self._snap_points(end):
                cand = self.simplify(self.plan_path(start, e) + [end])
                if best is None or self.length_of(cand) < self.length_of(best):
                    best = cand
            return best
        sx, sy = start
        ex, ey = end
        if sx % cs == 0 and sx == ex:
            return [start, end]
        if sy % cs == 0 and sy == ey:
            return [start, end]
        best = None
        best_len = None
        for a in self._anchors(start):
            for b in self._anchors(end):
                for corner in ((b[0], a[1]), (a[0], b[1])):
                    cand = self.simplify([start, a, corner, b, end])
                    length = self.length_of(cand)
                    if best is None or length < best_len:
                        best, best_len = cand, length
        return best

    def plan_route(self, start, end, speed=1):
        """Plan a path and wrap it into a :class:`Route`."""
        return Route(self.plan_path(start, end), speed)

    def path_length(self, start, end):
        """Length of the planned path between two points."""
        return self.length_of(self.plan_path(start, end))

    def access_points(self, center):
        """Street midpoints surrounding a cell centre."""
        cx, cy = int(center[0]), int(center[1])
        h = self.grid.cell_size // 2
        cands = [(cx - h, cy), (cx + h, cy), (cx, cy - h), (cx, cy + h)]
        return [c for c in cands if self.grid.in_bounds(*c)]

    def best_access_point(self, from_pos, center):
        """Return ``(point, path_length)`` of the closest access point."""
        best = None
        for p in self.access_points(center):
            length = self.path_length(from_pos, p)
            if best is None or length < best[1]:
                best = (p, length)
        if best is None:
            p = self._norm(center)
            best = (p, self.path_length(from_pos, p))
        return best

    def is_special_case(self, start, end):
        """True if a detour is needed (e.g. target directly above/below)."""
        cs = self.grid.cell_size
        sx, sy = self._norm(start)
        ex, ey = self._norm(end)
        if not self.grid.is_on_street(sx, sy):
            return True
        if sx == ex and sx % cs != 0 and sy != ey:
            return True
        if sy == ey and sy % cs != 0 and sx != ex:
            return True
        return False
