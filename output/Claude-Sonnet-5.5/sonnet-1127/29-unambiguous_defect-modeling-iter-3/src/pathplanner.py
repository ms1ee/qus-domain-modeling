"""Grid map and path planning."""


class GridMap:
    """8x8 grid, 100-unit cells."""

    def __init__(self, width=800, height=800, cell_size=100):
        self.width = width
        self.height = height
        self.cell_size = cell_size

    def center(self, v):
        """Convert a coordinate to its cell center, clamped to the map."""
        v = max(0, min(int(v), self.width - 1))
        return (v // self.cell_size) * self.cell_size + self.cell_size // 2


class PathPlanner:
    """Right-angle path planning."""

    def __init__(self, grid=None):
        self.grid = grid or GridMap()

    def plan(self, start, *targets):
        """Return a list of waypoints through targets using L-shaped legs."""
        pts = [tuple(start)]
        cur = tuple(start)
        for t in targets:
            t = tuple(t)
            if cur[0] != t[0] and cur[1] != t[1]:
                pts.append((t[0], cur[1]))
            if pts[-1] != t:
                pts.append(t)
            cur = t
        return pts

    @staticmethod
    def length(points):
        """Manhattan length of a polyline."""
        return sum(abs(a[0] - b[0]) + abs(a[1] - b[1])
                   for a, b in zip(points, points[1:]))
