"""Grid map and path planning."""

CELL = 100
DIM = 8


class GridMap:
    """8x8 grid of 100-unit cells."""

    def __init__(self):
        self.width = 800
        self.height = 800
        self.cellSize = CELL
        self.gridDimension = DIM

    @staticmethod
    def center(v):
        """Convert a coordinate to its grid cell center."""
        v = max(0, min(799, int(v)))
        return (v // CELL) * CELL + 50


class PathPlanner:
    """Right-angle path planning."""

    def __init__(self, grid=None):
        self.grid = grid or GridMap()

    def plan(self, start, end):
        """Return corner points from start to end (horizontal first)."""
        pts = [tuple(start)]
        if start[0] != end[0] and start[1] != end[1]:
            pts.append((end[0], start[1]))
        if tuple(end) != pts[-1]:
            pts.append(tuple(end))
        return pts

    def next_position(self, pos, target, speed):
        """Advance from pos toward target by at most speed units."""
        x, y = pos
        tx, ty = target
        if x != tx:
            step = min(speed, abs(tx - x))
            x += step if tx > x else -step
        elif y != ty:
            step = min(speed, abs(ty - y))
            y += step if ty > y else -step
        return x, y

    @staticmethod
    def distance(a, b):
        """Manhattan distance."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
