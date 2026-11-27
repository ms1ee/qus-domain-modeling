"""Grid based path planning for riders.

The map is 800x800 units split into an 8x8 grid of 100x100 cells.
Grid lines (x or y multiple of 100) are streets. Restaurants and
customers are located at the centre of cells.
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE


def _clamp(value, low=0, high=MAP_SIZE):
    return max(low, min(high, int(value)))


def _floor_street(v):
    return _clamp((int(v) // CELL_SIZE) * CELL_SIZE)


def _ceil_street(v):
    v = int(v)
    if v % CELL_SIZE == 0:
        return _clamp(v)
    return _clamp((v // CELL_SIZE + 1) * CELL_SIZE)


class PathPlanner:
    """Path finding utilities working on the street grid."""

    @staticmethod
    def clamp(value):
        """Clamp a coordinate into the map range 0..800."""
        return _clamp(value)

    @staticmethod
    def to_grid_center(x, y):
        """Convert raw coordinates to the centre of their grid cell.

        ``center = (v // 100) * 100 + 50`` with boundary handling so that
        800 maps to the last cell (750).
        """
        def conv(v):
            v = _clamp(v)
            c = (v // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2
            return min(c, MAP_SIZE - CELL_SIZE // 2)
        return (conv(x), conv(y))

    @staticmethod
    def grid_index(x, y):
        """Return the (col, row) grid cell index (0..7) of a coordinate."""
        gx = min(_clamp(x) // CELL_SIZE, GRID_DIM - 1)
        gy = min(_clamp(y) // CELL_SIZE, GRID_DIM - 1)
        return (gx, gy)

    @staticmethod
    def is_on_street(x, y):
        """Return True if the point lies on a street (grid line)."""
        return int(x) % CELL_SIZE == 0 or int(y) % CELL_SIZE == 0

    @staticmethod
    def is_special_case(start, target):
        """Return True when the start is directly above/below the target."""
        return int(start[0]) == int(target[0]) and int(start[1]) != int(target[1])

    @staticmethod
    def manhattan(a, b):
        """Manhattan distance between two points."""
        return abs(int(a[0]) - int(b[0])) + abs(int(a[1]) - int(b[1]))

    @staticmethod
    def _dedupe(start, points):
        result = []
        prev = (int(start[0]), int(start[1]))
        for p in points:
            p = (int(p[0]), int(p[1]))
            if p == prev:
                continue
            # remove collinear intermediate points
            if result:
                a = result[-2] if len(result) >= 2 else (int(start[0]), int(start[1]))
                b = result[-1]
                if (a[0] == b[0] == p[0]) or (a[1] == b[1] == p[1]):
                    # b is between a and p on the same line only if monotonic
                    if (min(a[0], p[0]) <= b[0] <= max(a[0], p[0])
                            and min(a[1], p[1]) <= b[1] <= max(a[1], p[1])):
                        result[-1] = p
                        prev = p
                        continue
            result.append(p)
            prev = p
        return result

    @classmethod
    def plan_path(cls, start, target):
        """Plan a street-prioritised path from ``start`` to ``target``.

        Returns a list of axis aligned waypoints (excluding the start,
        including the target). Strategy:

        1. Leave the current cell vertically to the nearest horizontal
           street in the direction of the target.
        2. Travel along that street to the vertical street adjacent to the
           target cell (on the side facing the start).
        3. Travel along the vertical street to the target's row.
        4. Enter the target cell horizontally.

        When the rider is directly above or below the target (same x), the
        rider sidesteps onto the neighbouring vertical street (special case).
        """
        sx, sy = _clamp(start[0]), _clamp(start[1])
        tx, ty = _clamp(target[0]), _clamp(target[1])
        if (sx, sy) == (tx, ty):
            return []

        # Same cell: move directly with a right-angle turn.
        if cls.grid_index(sx, sy) == cls.grid_index(tx, ty) and \
                not cls.is_on_street(sx, sy):
            return cls._dedupe((sx, sy), [(tx, sy), (tx, ty)])

        # Step 1: reach a horizontal street.
        if sy % CELL_SIZE == 0:
            ys = sy
        elif ty > sy:
            ys = _ceil_street(sy)
        else:
            ys = _floor_street(sy)

        points = [(sx, ys)]

        if ty == ys:
            points.append((tx, ty))
            return cls._dedupe((sx, sy), points)

        # Step 2: choose the vertical street adjacent to the target.
        if tx % CELL_SIZE == 0:
            xs = tx
        elif sx < tx:
            xs = _floor_street(tx)
        elif sx > tx:
            xs = _ceil_street(tx)
        else:
            # Special case: directly above/below; sidestep to nearer street.
            xs = _floor_street(tx)

        points.append((xs, ys))
        points.append((xs, ty))
        points.append((tx, ty))
        return cls._dedupe((sx, sy), points)

    @classmethod
    def plan_route(cls, start, destinations):
        """Plan a continuous route through several destinations.

        Returns ``(waypoints, segment_lengths)`` where waypoints excludes
        the start point.
        """
        waypoints = []
        lengths = []
        current = (int(start[0]), int(start[1]))
        for dest in destinations:
            seg = cls.plan_path(current, dest)
            lengths.append(cls.path_length(current, seg))
            waypoints.extend(seg)
            current = (int(dest[0]), int(dest[1]))
        return waypoints, lengths

    @classmethod
    def path_length(cls, start, waypoints):
        """Total length of the path starting at ``start``."""
        total = 0
        prev = start
        for p in waypoints:
            total += cls.manhattan(prev, p)
            prev = p
        return total
