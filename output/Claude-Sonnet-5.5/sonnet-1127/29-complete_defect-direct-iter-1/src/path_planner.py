"""Grid based path planning."""

GRID = 100
SIZE = 800


def to_center(v):
    """Convert a coordinate to its grid cell centre."""
    v = max(0, min(int(v), SIZE))
    return min(v // GRID, 7) * GRID + 50


class PathPlanner:
    """Simple right-angle path planner."""

    @staticmethod
    def route(start, end):
        """Waypoints from start to end (horizontal then vertical)."""
        pts = [tuple(start)]
        corner = (end[0], start[1])
        if corner != pts[-1] and corner != tuple(end):
            pts.append(corner)
        if tuple(end) != pts[-1]:
            pts.append(tuple(end))
        return pts

    @staticmethod
    def distance(a, b):
        """Manhattan distance."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def step(pos, target, speed):
        """Advance up to speed units toward target; returns new (x, y)."""
        x, y = pos
        left = speed
        dx = target[0] - x
        if dx and left > 0:
            m = min(abs(dx), left)
            x += m if dx > 0 else -m
            left -= m
        dy = target[1] - y
        if dy and left > 0:
            m = min(abs(dy), left)
            y += m if dy > 0 else -m
        return x, y
