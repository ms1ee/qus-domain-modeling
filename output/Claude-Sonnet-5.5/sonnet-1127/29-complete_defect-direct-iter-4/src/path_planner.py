"""Grid-based path planning."""

CELL = 100


def to_center(v):
    """Convert a coordinate (0-800) to its grid cell center."""
    g = min(max(int(v) // CELL, 0), 7)
    return g * CELL + CELL // 2


class PathPlanner:
    """Plans right-angle paths on the grid."""

    @staticmethod
    def plan(start, target):
        """Return waypoints from start to target (horizontal then vertical).

        If the rider is directly above/below the target only a vertical
        leg is produced.
        """
        sx, sy = start
        tx, ty = target
        pts = [(sx, sy)]
        if sx != tx:
            pts.append((tx, sy))
        if sy != ty:
            pts.append((tx, ty))
        return pts

    @staticmethod
    def plan_multi(start, targets):
        """Continuous path through several destinations."""
        path = [tuple(start)]
        cur = tuple(start)
        for t in targets:
            seg = PathPlanner.plan(cur, tuple(t))
            path.extend(seg[1:])
            cur = tuple(t)
        return path

    @staticmethod
    def step(pos, target, speed):
        """Move from pos toward target by at most speed units."""
        x, y = pos
        tx, ty = target
        budget = speed
        if x != tx:
            d = min(budget, abs(tx - x))
            x += d if tx > x else -d
            budget -= d
        if budget > 0 and y != ty:
            d = min(budget, abs(ty - y))
            y += d if ty > y else -d
        return x, y

    @staticmethod
    def distance(a, b):
        """Manhattan distance."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
