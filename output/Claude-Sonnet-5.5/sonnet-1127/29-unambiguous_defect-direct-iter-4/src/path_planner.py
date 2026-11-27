"""Grid-based path planning."""

CELL = 100
SIZE = 800


def to_center(v):
    """Convert coordinate to grid cell center."""
    v = max(0, min(SIZE - 1, int(v)))
    return (v // CELL) * CELL + CELL // 2


def center_pos(x, y):
    """Convert a point to its cell center."""
    return (to_center(x), to_center(y))


class PathPlanner:
    """Right-angle path planner."""

    @staticmethod
    def route(start, *targets):
        """Waypoints through targets; moves vertically first then horizontally
        alternately chosen so that the path follows streets where possible."""
        pts = [tuple(start)]
        cur = tuple(start)
        for t in targets:
            t = tuple(t)
            if cur[0] != t[0] and cur[1] != t[1]:
                pts.append((cur[0], t[1]) if cur[0] % CELL == 0 else (t[0], cur[1]))
            if pts[-1] != t:
                pts.append(t)
            cur = t
        return pts

    @staticmethod
    def step(pos, target, speed):
        """Advance pos toward target by speed units (x axis first, or
        y first when already aligned on a vertical street)."""
        x, y = pos
        tx, ty = target
        left = speed
        order = ("x", "y") if x % CELL != 0 or x == tx else ("y", "x")
        if x % CELL == 0 and x != tx:
            order = ("y", "x")
        for axis in order:
            if left <= 0:
                break
            if axis == "x":
                d = min(left, abs(tx - x))
                x += d if tx > x else -d
            else:
                d = min(left, abs(ty - y))
                y += d if ty > y else -d
            left -= d
        return (x, y)

    @staticmethod
    def distance(a, b):
        """Manhattan distance."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
