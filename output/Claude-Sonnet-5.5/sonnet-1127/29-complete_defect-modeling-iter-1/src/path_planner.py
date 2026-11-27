"""Grid-based path planning."""
from gridmap import GRID


class PathPlanner:
    """Right-angle path planner along streets."""

    def __init__(self, grid=GRID):
        self.grid = grid

    def step(self, x, y, tx, ty, speed):
        """Move up to speed units toward target: horizontal first, then
        vertical. If aligned in x (directly above/below) go vertical."""
        remaining = speed
        if x != tx and remaining > 0:
            d = min(remaining, abs(tx - x))
            x += d if tx > x else -d
            remaining -= d
        if y != ty and remaining > 0:
            d = min(remaining, abs(ty - y))
            y += d if ty > y else -d
        return x, y

    def waypoints(self, points):
        """Expand a list of points into an L-shaped polyline."""
        out = [points[0]]
        for (px, py) in points[1:]:
            lx, ly = out[-1]
            if lx != px and ly != py:
                out.append((px, ly))
            if out[-1] != (px, py):
                out.append((px, py))
        return out

    def route_cells(self, points):
        """Return ordered grid cells (cx, cy) crossed by the route."""
        wp = self.waypoints(points)
        cells = []

        def add(x, y):
            c = (self.grid.cell_index(x), self.grid.cell_index(y))
            if not cells or cells[-1] != c:
                cells.append(c)

        add(*wp[0])
        for (ax, ay), (bx, by) in zip(wp, wp[1:]):
            n = max(abs(bx - ax), abs(by - ay))
            for i in range(10, n + 10, 10):
                f = min(i, n)
                add(ax + (bx - ax) * f // n, ay + (by - ay) * f // n)
        return cells

    @staticmethod
    def length(points):
        """Manhattan length of a route."""
        return sum(abs(b[0] - a[0]) + abs(b[1] - a[1])
                   for a, b in zip(points, points[1:]))
