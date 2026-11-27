"""Grid-based path planning."""


class PathPlanner:
    """Plans right-angle paths on the grid."""

    def __init__(self, grid_size=8, cell_size=100):
        self.grid_size = grid_size
        self.cell_size = cell_size

    def next_step(self, x, y, tx, ty, speed):
        """Return the next position moving horizontally first, then vertically."""
        if x != tx:
            d = min(speed, abs(tx - x))
            return x + (d if tx > x else -d), y
        if y != ty:
            d = min(speed, abs(ty - y))
            return x, y + (d if ty > y else -d)
        return x, y

    def path(self, points, speed=100):
        """Return list of positions through successive points."""
        out = [points[0]]
        x, y = points[0]
        for tx, ty in points[1:]:
            while (x, y) != (tx, ty):
                x, y = self.next_step(x, y, tx, ty, speed)
                out.append((x, y))
        return out
