"""Grid based path planning."""
import math

CELL = 100
SIZE = 800


class GridMap:
    """8x8 grid map of 100-unit cells."""
    width = SIZE
    height = SIZE
    cell_size = CELL


class Route:
    """A list of waypoints and estimated time."""

    def __init__(self, waypoints, estimated_time):
        self.waypoints = waypoints
        self.estimated_time = estimated_time


def to_center(v):
    """Convert coordinate to its grid cell center."""
    v = max(0, min(SIZE - 1, int(v)))
    return (v // CELL) * CELL + 50


class PathPlanner:
    """Plans right-angle routes."""

    def plan(self, start, targets, speed=10):
        """Route from start through targets (horizontal first, then vertical)."""
        pts = [tuple(start)]
        cur = tuple(start)
        for t in targets:
            t = tuple(t)
            if cur[0] != t[0] and cur[1] != t[1]:
                pts.append((t[0], cur[1]))
            if cur != t:
                pts.append(t)
            cur = t
        length = sum(abs(a[0] - b[0]) + abs(a[1] - b[1])
                     for a, b in zip(pts, pts[1:]))
        return Route(pts, int(math.ceil(length / float(speed))) if speed else 0)

    def step(self, x, y, tx, ty, budget):
        """Advance up to budget units toward target. Returns (x, y)."""
        if x != tx:
            d = min(budget, abs(tx - x))
            x += d if tx > x else -d
            budget -= d
        if budget > 0 and y != ty:
            d = min(budget, abs(ty - y))
            y += d if ty > y else -d
        return x, y
