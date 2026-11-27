"""Grid-based path planning for riders.

Coordinate system
-----------------
The map is 800x800 units split into an 8x8 grid of 100x100 cells.  Lines with
``x % 100 == 0`` or ``y % 100 == 0`` are streets.  Restaurants and customers
are located at cell centers (``(v // 100) * 100 + 50``).  Riders always travel
along streets and only leave a street for the final "doorstep" leg into a
cell (and the first leg back out of it).
"""

CELL_SIZE = 100
MAP_SIZE = 800
GRID_DIM = MAP_SIZE // CELL_SIZE


class GridMap:
    """Static description of the grid map."""

    map_size = MAP_SIZE
    cell_size = CELL_SIZE
    grid_dimension = GRID_DIM


def clamp(value, low=0, high=MAP_SIZE):
    """Clamp ``value`` into ``[low, high]``."""
    return max(low, min(high, value))


def to_grid_center(value):
    """Convert a raw coordinate (0-800) to the center of its grid cell.

    ``center = (v // 100) * 100 + 50``; values out of range are clamped so
    the result is always within ``[50, 750]``.
    """
    v = clamp(int(value))
    center = (v // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2
    return min(center, MAP_SIZE - CELL_SIZE // 2)


def is_street(x, y):
    """Return True if the point lies on a street (grid line)."""
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def manhattan(a, b):
    """Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _choose_line(a, b):
    """Choose a grid line (multiple of 100) to travel along between a and b.

    Returns ``(line, special)`` where ``special`` is True when no grid line
    lies between ``a`` and ``b`` (e.g. rider directly above/below target)
    so a detour to a neighbouring street is required.
    """
    lo, hi = min(a, b), max(a, b)
    first = -(-lo // CELL_SIZE) * CELL_SIZE
    if first <= hi:
        candidates = range(first, hi + 1, CELL_SIZE)
        return min(candidates, key=lambda m: (abs(m - a), m)), False
    down = (a // CELL_SIZE) * CELL_SIZE
    up = down + CELL_SIZE
    candidates = [m for m in (down, up) if 0 <= m <= MAP_SIZE] or [down]
    best = min(candidates, key=lambda m: (abs(a - m) + abs(m - b), m))
    return best, True


class Route:
    """A planned route: waypoints plus distance and estimated time."""

    def __init__(self, start, waypoints, speed=None):
        self.start = tuple(start)
        self.waypoints = list(waypoints)
        self.total_distance = PathPlanner.route_length(start, waypoints)
        if speed and speed > 0:
            self.estimated_time = -(-self.total_distance // speed)
        else:
            self.estimated_time = None

    def to_dict(self):
        """Serialise the route."""
        return {
            "start": list(self.start),
            "waypoints": [list(p) for p in self.waypoints],
            "total_distance": self.total_distance,
            "estimated_time": self.estimated_time,
        }


class PathPlanner:
    """Street-first pathfinding with right-angle turns."""

    def __init__(self):
        self.special_case = False

    def plan(self, start, target):
        """Plan a route from ``start`` to ``target``.

        Returns the list of waypoints (excluding ``start``, including
        ``target``).  Every consecutive pair of points differs along a
        single axis.  ``self.special_case`` is set when a detour was needed.
        """
        self.special_case = False
        sx, sy = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        if (sx, sy) == (tx, ty):
            return []

        points = []
        cur = (sx, sy)

        if not is_street(sx, sy):
            same_cell = (not is_street(tx, ty)
                         and sx // CELL_SIZE == tx // CELL_SIZE
                         and sy // CELL_SIZE == ty // CELL_SIZE)
            if same_cell:
                return self._clean((sx, sy), [(tx, sy), (tx, ty)])
            base = (sy // CELL_SIZE) * CELL_SIZE
            if ty < sy:
                ny = base
            elif ty > sy:
                ny = base + CELL_SIZE
            else:
                ny = min((base, base + CELL_SIZE),
                         key=lambda m: (abs(m - sy), m))
            ny = clamp(ny)
            cur = (sx, ny)
            points.append(cur)

        if is_street(tx, ty):
            entry = (tx, ty)
        else:
            base = (ty // CELL_SIZE) * CELL_SIZE
            ey = min((base, base + CELL_SIZE),
                     key=lambda m: (abs(m - cur[1]), m))
            entry = (tx, clamp(ey))

        points.extend(self._street_path(cur, entry))
        if entry != (tx, ty):
            points.append((tx, ty))
        return self._clean((sx, sy), points)

    def plan_multi(self, points):
        """Plan a continuous route through several destinations."""
        result = []
        special = False
        if not points:
            return result
        cur = tuple(points[0])
        for nxt in points[1:]:
            seg = self.plan(cur, nxt)
            special = special or self.special_case
            result.extend(seg)
            cur = tuple(nxt)
        self.special_case = special
        return self._clean(tuple(points[0]), result)

    def _street_path(self, a, b):
        """Path between two street points using right-angle turns."""
        ax, ay = a
        bx, by = b
        if a == b:
            return []
        if ay == by and ay % CELL_SIZE == 0:
            return [(bx, by)]
        if ax == bx and ax % CELL_SIZE == 0:
            return [(bx, by)]
        if ax % CELL_SIZE == 0 and by % CELL_SIZE == 0:
            return [(ax, by), (bx, by)]
        if ay % CELL_SIZE == 0 and bx % CELL_SIZE == 0:
            return [(bx, ay), (bx, by)]
        if ay % CELL_SIZE == 0 and by % CELL_SIZE == 0:
            v, special = _choose_line(ax, bx)
            if special:
                self.special_case = True
            return [(v, ay), (v, by), (bx, by)]
        # both on vertical streets with different x
        h, special = _choose_line(ay, by)
        if special:
            self.special_case = True
        return [(ax, h), (bx, h), (bx, by)]

    @staticmethod
    def _clean(start, points):
        """Remove duplicates and merge collinear, same-direction segments."""
        out = []
        prev = tuple(start)
        for p in points:
            p = (int(p[0]), int(p[1]))
            if p == prev:
                continue
            if out:
                a = out[-2] if len(out) >= 2 else tuple(start)
                b = out[-1]
                if a[0] == b[0] == p[0]:
                    if min(a[1], p[1]) <= b[1] <= max(a[1], p[1]):
                        out[-1] = p
                        prev = p
                        continue
                elif a[1] == b[1] == p[1]:
                    if min(a[0], p[0]) <= b[0] <= max(a[0], p[0]):
                        out[-1] = p
                        prev = p
                        continue
            out.append(p)
            prev = p
        return out

    @staticmethod
    def route_length(start, waypoints):
        """Total Manhattan length of a route."""
        total = 0
        cur = tuple(start)
        for p in waypoints:
            total += manhattan(cur, p)
            cur = tuple(p)
        return total
