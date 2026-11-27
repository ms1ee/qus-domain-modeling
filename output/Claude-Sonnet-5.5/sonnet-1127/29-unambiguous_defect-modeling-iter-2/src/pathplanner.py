"""Grid based path planning."""

CELL = 100
SIZE = 800


def to_center(v):
    """Convert a raw coordinate to its grid cell center."""
    try:
        v = int(v)
    except (TypeError, ValueError):
        v = 0
    v = max(0, min(SIZE - 1, v))
    return (v // CELL) * CELL + CELL // 2


def to_cell(v):
    """Grid cell index of a coordinate."""
    return max(0, min(SIZE // CELL - 1, int(v) // CELL))


class PathPlanner:
    """Manhattan style planner: horizontal first, then vertical."""

    @staticmethod
    def distance(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def waypoints(points):
        """Right-angle waypoints through a sequence of points."""
        if not points:
            return []
        out = [tuple(points[0])]
        for p in points[1:]:
            cur = out[-1]
            if cur[0] != p[0] and cur[1] != p[1]:
                out.append((p[0], cur[1]))
            if out[-1] != tuple(p):
                out.append(tuple(p))
        return out

    @staticmethod
    def step(pos, target, budget):
        """Move up to budget units toward target; returns new position."""
        x, y = pos
        tx, ty = target
        if x != tx:
            d = min(budget, abs(tx - x))
            x += d if tx > x else -d
            budget -= d
        if budget > 0 and y != ty:
            d = min(budget, abs(ty - y))
            y += d if ty > y else -d
        return (x, y)
