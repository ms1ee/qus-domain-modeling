"""Grid based path planning."""

CELL = 100
MAP_SIZE = 800


def to_center(v):
    """Convert a raw coordinate (0-800) to its grid cell center."""
    cell = int(v) // CELL
    cell = max(0, min(MAP_SIZE // CELL - 1, cell))
    return cell * CELL + CELL // 2


class PathPlanner:
    """Street-preferring right-angle path planner."""

    @staticmethod
    def horizontal_first(pos):
        """Decide the first axis: follow a street if on one."""
        x, y = pos
        if y % CELL == 0:
            return True
        if x % CELL == 0:
            return False
        return True

    def plan(self, start, end):
        """Return list of waypoints from start to end (inclusive)."""
        sx, sy = start
        ex, ey = end
        pts = [(sx, sy)]
        if self.horizontal_first(start):
            corner = (ex, sy)
        else:
            corner = (sx, ey)
        if corner != pts[-1] and corner != (ex, ey):
            pts.append(corner)
        if (ex, ey) != pts[-1]:
            pts.append((ex, ey))
        return pts

    def distance(self, a, b):
        """Manhattan distance."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def step(self, pos, target, speed):
        """Move up to speed units from pos toward target."""
        x, y = pos
        tx, ty = target
        left = speed
        axes = ["x", "y"] if self.horizontal_first(pos) else ["y", "x"]
        for axis in axes:
            if left <= 0:
                break
            if axis == "x":
                d = min(left, abs(tx - x))
                x += d if tx > x else -d
            else:
                d = min(left, abs(ty - y))
                y += d if ty > y else -d
            left -= d
        return x, y
