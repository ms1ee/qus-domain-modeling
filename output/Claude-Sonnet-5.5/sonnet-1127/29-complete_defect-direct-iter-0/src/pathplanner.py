"""Grid based path planning."""

GRID = 100
SIZE = 800


def center(v):
    """Convert coordinate to grid cell centre."""
    v = max(0, min(SIZE, int(v)))
    cell = min(v // GRID, SIZE // GRID - 1)
    return cell * GRID + GRID // 2


class PathPlanner:
    """Right-angle path planner."""

    @staticmethod
    def plan(start, end):
        """Waypoints from start to end: horizontal first, then vertical."""
        pts = [tuple(start)]
        corner = (end[0], start[1])
        if corner != pts[-1]:
            pts.append(corner)
        if tuple(end) != pts[-1]:
            pts.append(tuple(end))
        return pts

    @staticmethod
    def step(pos, target, speed):
        """Advance pos towards target by up to speed units."""
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

    @staticmethod
    def distance(a, b):
        """Manhattan distance."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
