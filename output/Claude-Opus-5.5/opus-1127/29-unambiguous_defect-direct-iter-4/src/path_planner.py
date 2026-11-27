"""Grid based path planning.

The map is 800x800 units split into an 8x8 grid of 100x100 cells.
Lines with x or y equal to a multiple of 100 are streets; cell centres
(x % 100 == 50 and y % 100 == 50) are restaurant/customer locations.
Riders only travel along streets, except for the last/first leg entering
or leaving a cell centre (a straight vertical move from the street).
"""

from config import MAP_SIZE, CELL_SIZE, GRID_SIZE


class PathPlanner:
    """Collection of path finding helpers (all static/class methods)."""

    @staticmethod
    def clamp(value):
        """Clamp a coordinate to the map range 0..800."""
        return max(0, min(MAP_SIZE, int(value)))

    @staticmethod
    def is_road(x, y):
        """Return True if (x, y) lies on a street."""
        return int(x) % CELL_SIZE == 0 or int(y) % CELL_SIZE == 0

    @staticmethod
    def grid_index(value):
        """Return the grid cell index (0..7) for a coordinate."""
        value = PathPlanner.clamp(value)
        return min(value // CELL_SIZE, GRID_SIZE - 1)

    @staticmethod
    def to_grid_center(x, y):
        """Convert arbitrary coordinates to the centre of their grid cell."""
        gx = PathPlanner.grid_index(x)
        gy = PathPlanner.grid_index(y)
        return (gx * CELL_SIZE + CELL_SIZE // 2, gy * CELL_SIZE + CELL_SIZE // 2)

    @staticmethod
    def snap_to_road(x, y):
        """Return the nearest street point to (x, y)."""
        x = PathPlanner.clamp(x)
        y = PathPlanner.clamp(y)
        if PathPlanner.is_road(x, y):
            return (x, y)
        ny = PathPlanner.clamp(((y + CELL_SIZE // 2) // CELL_SIZE) * CELL_SIZE)
        return (x, ny)

    @staticmethod
    def manhattan(a, b):
        """Manhattan distance between two points."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def path_length(start, waypoints):
        """Total length of a polyline starting at ``start``."""
        total = 0
        cur = tuple(start)
        for wp in waypoints:
            total += PathPlanner.manhattan(cur, wp)
            cur = tuple(wp)
        return total

    @staticmethod
    def _dedupe(start, waypoints):
        """Remove waypoints identical to the previous point."""
        result = []
        prev = tuple(start)
        for wp in waypoints:
            wp = (int(wp[0]), int(wp[1]))
            if wp != prev:
                result.append(wp)
                prev = wp
        return result

    @staticmethod
    def _street_candidates(*values):
        """Street lines (floor/ceil multiples of 100) around the given values."""
        cands = set()
        for v in values:
            low = (int(v) // CELL_SIZE) * CELL_SIZE
            high = low if int(v) % CELL_SIZE == 0 else low + CELL_SIZE
            cands.add(PathPlanner.clamp(low))
            cands.add(PathPlanner.clamp(high))
        return sorted(cands)

    @classmethod
    def _road_route(cls, a, b):
        """Route between two street points travelling only along streets."""
        a = (int(a[0]), int(a[1]))
        b = (int(b[0]), int(b[1]))
        if a == b:
            return []
        x1, y1 = a
        x2, y2 = b
        a_h, a_v = y1 % CELL_SIZE == 0, x1 % CELL_SIZE == 0
        b_h, b_v = y2 % CELL_SIZE == 0, x2 % CELL_SIZE == 0
        options = []
        if a_h and b_h and y1 == y2:
            options.append([b])
        if a_v and b_v and x1 == x2:
            options.append([b])
        if a_h and b_v:
            options.append([(x2, y1), b])
        if a_v and b_h:
            options.append([(x1, y2), b])
        if a_h and b_h:
            for vx in cls._street_candidates(x1, x2):
                options.append([(vx, y1), (vx, y2), b])
        if a_v and b_v:
            for hy in cls._street_candidates(y1, y2):
                options.append([(x1, hy), (x2, hy), b])
        if not options:
            # Should not happen for valid road points; fall back to L-shape.
            options.append([(x2, y1), b])
        best = min(options, key=lambda o: (cls.path_length(a, o), len(o)))
        return cls._dedupe(a, best)

    @classmethod
    def plan(cls, start, target):
        """Plan a street-following path from ``start`` to ``target``.

        Returns a list of waypoints (excluding ``start``). Consecutive
        waypoints are always connected by horizontal or vertical segments.
        """
        start = (cls.clamp(start[0]), cls.clamp(start[1]))
        target = (cls.clamp(target[0]), cls.clamp(target[1]))
        if start == target:
            return []
        waypoints = []
        cx, cy = start
        tx, ty = target

        # Leave a cell centre (or other off-road point) vertically to a street.
        if not cls.is_road(cx, cy):
            base = (cy // CELL_SIZE) * CELL_SIZE
            if ty < cy:
                ny = base
            elif ty > cy:
                ny = base + CELL_SIZE
            else:
                ny = base if (cy - base) <= (base + CELL_SIZE - cy) else base + CELL_SIZE
            ny = cls.clamp(ny)
            waypoints.append((cx, ny))
            cy = ny

        # Determine the street entry point for the target.
        if cls.is_road(tx, ty):
            entry, final = (tx, ty), None
        else:
            base = (ty // CELL_SIZE) * CELL_SIZE
            hy = base if abs(cy - base) <= abs(cy - (base + CELL_SIZE)) else base + CELL_SIZE
            entry, final = (tx, cls.clamp(hy)), (tx, ty)

        waypoints.extend(cls._road_route((cx, cy), entry))
        if final is not None:
            waypoints.append(final)
        return cls._dedupe(start, waypoints)

    @classmethod
    def plan_multi(cls, start, stops):
        """Plan a continuous path through several destinations in order."""
        path = []
        cur = (cls.clamp(start[0]), cls.clamp(start[1]))
        for stop in stops:
            leg = cls.plan(cur, stop)
            path.extend(leg)
            cur = (cls.clamp(stop[0]), cls.clamp(stop[1]))
        return cls._dedupe(start, path)

    @classmethod
    def is_detour(cls, start, waypoints):
        """True when the path is longer than the Manhattan distance
        (special case, e.g. target directly above/below inside a cell)."""
        if not waypoints:
            return False
        return cls.path_length(start, waypoints) > cls.manhattan(start, waypoints[-1])
