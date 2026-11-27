"""Grid-based path planning on an 800x800 map made of 100x100 cells.

Streets are the grid lines (x or y being a multiple of 100). Restaurants and
customers live at cell centres. Riders leave a cell centre onto the nearest
useful street, travel along streets (straight lines and right-angle turns)
and finally enter the destination cell centre.
"""

GRID_SIZE = 100
GRID_COUNT = 8
MAP_SIZE = GRID_SIZE * GRID_COUNT


def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class PathPlanner:
    """Collection of path-planning helpers (all static)."""

    @staticmethod
    def validate_coordinate(value):
        """Validate a single raw coordinate (integer in 0..800)."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("coordinate must be an integer: %r" % (value,))
        if value < 0 or value > MAP_SIZE:
            raise ValueError("coordinate out of range 0-%d: %d"
                             % (MAP_SIZE, value))
        return value

    @staticmethod
    def to_grid_index(value):
        """Convert a raw coordinate into a grid index 0..7 (800 -> 7)."""
        PathPlanner.validate_coordinate(value)
        return min(value // GRID_SIZE, GRID_COUNT - 1)

    @staticmethod
    def to_grid_center(x, y):
        """Convert raw coordinates into the centre of their grid cell."""
        gx = PathPlanner.to_grid_index(x)
        gy = PathPlanner.to_grid_index(y)
        return (gx * GRID_SIZE + GRID_SIZE // 2,
                gy * GRID_SIZE + GRID_SIZE // 2)

    @staticmethod
    def is_on_vertical_street(p):
        return p[0] % GRID_SIZE == 0

    @staticmethod
    def is_on_horizontal_street(p):
        return p[1] % GRID_SIZE == 0

    @staticmethod
    def is_on_street(p):
        """Return True if the point lies on a street line."""
        return (PathPlanner.is_on_vertical_street(p)
                or PathPlanner.is_on_horizontal_street(p))

    @staticmethod
    def same_cell(a, b):
        """Return True if two off-street points are inside the same cell."""
        return (a[0] // GRID_SIZE == b[0] // GRID_SIZE
                and a[1] // GRID_SIZE == b[1] // GRID_SIZE)

    @staticmethod
    def is_vertically_aligned(a, b):
        """Special case: target directly above or below (same column)."""
        return (a[0] == b[0] and a[1] != b[1]
                and not PathPlanner.is_on_vertical_street(a))

    @staticmethod
    def _projections(p):
        """Candidate street entry points for point ``p``."""
        x, y = int(p[0]), int(p[1])
        if PathPlanner.is_on_street((x, y)):
            return [(x, y)]
        opts = []
        fx = (x // GRID_SIZE) * GRID_SIZE
        fy = (y // GRID_SIZE) * GRID_SIZE
        for vx in (fx, fx + GRID_SIZE):
            if 0 <= vx <= MAP_SIZE:
                opts.append((vx, y))
        for vy in (fy, fy + GRID_SIZE):
            if 0 <= vy <= MAP_SIZE:
                opts.append((x, vy))
        return opts

    @staticmethod
    def _best_line(p, q):
        """Pick a street line (multiple of 100) minimising |p-h|+|q-h|."""
        cands = set()
        for v in (p, q):
            f = (v // GRID_SIZE) * GRID_SIZE
            for c in (f, f + GRID_SIZE):
                if 0 <= c <= MAP_SIZE:
                    cands.add(c)
        return min(sorted(cands), key=lambda h: (abs(p - h) + abs(q - h),
                                                 abs(p - h)))

    @staticmethod
    def _dedup(start, points):
        out = []
        prev = start
        for pt in points:
            pt = (int(pt[0]), int(pt[1]))
            if pt != prev:
                out.append(pt)
                prev = pt
        return out

    @staticmethod
    def _street_route(a, b):
        """Route between two street points along streets only."""
        if a == b:
            return []
        on_v = PathPlanner.is_on_vertical_street
        on_h = PathPlanner.is_on_horizontal_street
        if on_v(a) and on_v(b) and a[0] == b[0]:
            return [b]
        if on_h(a) and on_h(b) and a[1] == b[1]:
            return [b]
        if on_v(a) and on_h(b):
            return PathPlanner._dedup(a, [(a[0], b[1]), b])
        if on_h(a) and on_v(b):
            return PathPlanner._dedup(a, [(b[0], a[1]), b])
        if on_v(a) and on_v(b):
            h = PathPlanner._best_line(a[1], b[1])
            return PathPlanner._dedup(a, [(a[0], h), (b[0], h), b])
        v = PathPlanner._best_line(a[0], b[0])
        return PathPlanner._dedup(a, [(v, a[1]), (v, b[1]), b])

    @staticmethod
    def route_length(start, waypoints):
        """Total Manhattan length of ``start`` followed by ``waypoints``."""
        total = 0
        prev = start
        for pt in waypoints:
            total += _manhattan(prev, pt)
            prev = pt
        return total

    @staticmethod
    def plan(start, end):
        """Plan a street-following route.

        Returns a list of waypoints (excluding ``start``, including ``end``).
        Every segment is horizontal or vertical.
        """
        start = (int(start[0]), int(start[1]))
        end = (int(end[0]), int(end[1]))
        if start == end:
            return []
        if (not PathPlanner.is_on_street(start)
                and not PathPlanner.is_on_street(end)
                and PathPlanner.same_cell(start, end)):
            return PathPlanner._dedup(start, [(end[0], start[1]), end])
        best = None
        best_len = None
        for s1 in PathPlanner._projections(start):
            for t1 in PathPlanner._projections(end):
                route = PathPlanner._dedup(
                    start, [s1] + PathPlanner._street_route(s1, t1) + [end])
                length = PathPlanner.route_length(start, route)
                if best is None or length < best_len:
                    best, best_len = route, length
        return best or [end]

    @staticmethod
    def path_length(start, end):
        """Length of the planned route between two points."""
        return PathPlanner.route_length(
            (int(start[0]), int(start[1])), PathPlanner.plan(start, end))
