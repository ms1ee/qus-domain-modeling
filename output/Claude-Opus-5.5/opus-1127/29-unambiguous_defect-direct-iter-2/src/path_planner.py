"""Grid based path planning.

The map is an 800x800 coordinate system split into 8x8 cells of 100x100.
Lines with ``x % 100 == 0`` or ``y % 100 == 0`` are streets. Restaurants
and customers are located at cell centres (``... 50``). Riders travel
along streets and only leave a street for the final stretch into a
cell centre (and the first stretch out of one).
"""

MAP_SIZE = 800
CELL_SIZE = 100


def _clamp(value, low=0, high=MAP_SIZE):
    return max(low, min(high, value))


def manhattan(a, b):
    """Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class PathPlanner:
    """Street-first path planner with right-angle turns."""

    def __init__(self):
        self.last_special = False

    # ------------------------------------------------------------------ #
    # Coordinate helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def to_center(value):
        """Convert a raw coordinate to the centre of its grid cell.

        ``center = (v // 100) * 100 + 50``; values are clamped to 0..800
        and the boundary value 800 maps to the last cell (750).
        """
        v = _clamp(int(value))
        center = (v // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2
        if center > MAP_SIZE:
            center = MAP_SIZE - CELL_SIZE // 2
        return center

    @classmethod
    def to_center_point(cls, pos):
        """Convert an (x, y) pair to the centre point of its grid cell."""
        return (cls.to_center(pos[0]), cls.to_center(pos[1]))

    @staticmethod
    def to_cell(pos):
        """Return the (column, row) grid cell index (0..7) for a point."""
        cx = min(int(pos[0]) // CELL_SIZE, MAP_SIZE // CELL_SIZE - 1)
        cy = min(int(pos[1]) // CELL_SIZE, MAP_SIZE // CELL_SIZE - 1)
        return (max(cx, 0), max(cy, 0))

    @staticmethod
    def is_on_street(x, y):
        """Return True if the point lies on a street line."""
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    # ------------------------------------------------------------------ #
    # Planning
    # ------------------------------------------------------------------ #
    def plan(self, start, target):
        """Plan a path from ``start`` to ``target``.

        Returns a list of waypoints (excluding the start point). Each
        consecutive pair of points differs in only one axis, so the path
        consists of straight segments and right-angle turns.
        ``self.last_special`` is set when the "directly above/below"
        special case required a detour.
        """
        self.last_special = False
        sx, sy = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        if (sx, sy) == (tx, ty):
            return []
        pts = []

        # 1. Leave a cell interior by stepping onto a horizontal street.
        if not self.is_on_street(sx, sy):
            base = (sy // CELL_SIZE) * CELL_SIZE
            if ty > sy:
                ny = base + CELL_SIZE
            else:
                ny = base
            ny = _clamp(ny)
            sy = ny
            pts.append((sx, sy))

        # 2. Determine the horizontal street used to enter the target.
        if ty % CELL_SIZE == 0:
            ey = ty
        else:
            base = (ty // CELL_SIZE) * CELL_SIZE
            ey = base if sy <= ty else base + CELL_SIZE
            ey = _clamp(ey)

        # 3. Travel along streets to (tx, ey).
        if sy == ey and sy % CELL_SIZE == 0:
            pts.append((tx, ey))
        else:
            if sx % CELL_SIZE == 0:
                vx = sx
            else:
                # On a horizontal street but not on a vertical one.
                low = _clamp((sx // CELL_SIZE) * CELL_SIZE)
                high = _clamp((sx // CELL_SIZE + 1) * CELL_SIZE)
                vx = min((low, high),
                         key=lambda c: (abs(sx - c) + abs(c - tx), c))
                if sx == tx:
                    # Directly above/below the target: detour required.
                    self.last_special = True
                pts.append((vx, sy))
            pts.append((vx, ey))
            pts.append((tx, ey))

        # 4. Final stretch into the target.
        pts.append((tx, ty))

        # Remove duplicates / zero-length segments.
        cleaned = []
        prev = (int(start[0]), int(start[1]))
        for p in pts:
            if p != prev:
                cleaned.append(p)
                prev = p
        return cleaned

    def plan_route(self, start, targets):
        """Plan a continuous multi-destination route.

        Returns the full list of points including the start point.
        """
        route = [(int(start[0]), int(start[1]))]
        pos = route[0]
        for t in targets:
            pts = self.plan(pos, t)
            route.extend(pts)
            pos = (int(t[0]), int(t[1]))
        return route

    @staticmethod
    def path_length(start, points):
        """Length of the polyline ``start -> points...``."""
        total = 0
        prev = start
        for p in points:
            total += manhattan(prev, p)
            prev = p
        return total

    @staticmethod
    def route_length(route):
        """Length of a full route (list of points including the start)."""
        if not route:
            return 0
        return PathPlanner.path_length(route[0], route[1:])
