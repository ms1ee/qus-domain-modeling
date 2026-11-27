"""Grid path planning."""


class PathPlanner:
    """Axis-aligned (right-angle) path planner."""

    @staticmethod
    def plan(start, end, horizontal_first=True):
        """Return list of waypoints from start to end (inclusive)."""
        sx, sy = start
        ex, ey = end
        if sx == ex or sy == ey:
            return [(sx, sy), (ex, ey)]
        corner = (ex, sy) if horizontal_first else (sx, ey)
        return [(sx, sy), corner, (ex, ey)]

    @staticmethod
    def distance(a, b):
        """Manhattan distance."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def step(pos, target, speed):
        """Move up to speed units toward target: horizontal first, then vertical."""
        x, y = pos
        tx, ty = target
        left = speed
        if x != tx:
            d = min(left, abs(tx - x))
            x += d if tx > x else -d
            left -= d
        if left > 0 and y != ty:
            d = min(left, abs(ty - y))
            y += d if ty > y else -d
        return x, y
