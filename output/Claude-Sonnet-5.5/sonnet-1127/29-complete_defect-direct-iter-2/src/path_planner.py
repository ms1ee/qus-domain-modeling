"""Grid path planning."""

CELL = 100
SIZE = 800


def to_center(v):
    """Convert a coordinate to its grid cell center."""
    v = max(0, min(SIZE, int(v)))
    return min(v // CELL, SIZE // CELL - 1) * CELL + CELL // 2


class PathPlanner:
    """Right-angle path planner (horizontal first, then vertical)."""

    @staticmethod
    def waypoints(start, end):
        """Return corner points from start to end."""
        (sx, sy), (ex, ey) = start, end
        pts = [(sx, sy)]
        if sx != ex and sy != ey:
            pts.append((ex, sy))
        if (ex, ey) != pts[-1]:
            pts.append((ex, ey))
        return pts

    @staticmethod
    def route(points):
        """Multi-destination route through successive points."""
        full = [points[0]]
        for a, b in zip(points, points[1:]):
            full.extend(PathPlanner.waypoints(a, b)[1:])
        return full

    @staticmethod
    def step(x, y, tx, ty, speed):
        """Move up to `speed` units toward target along axes."""
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
