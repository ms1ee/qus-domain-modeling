"""Grid based path planning for riders."""

MAP_MIN = 0
MAP_MAX = 800
CELL = 100


def clamp(value, low=MAP_MIN, high=MAP_MAX):
    """Clamp ``value`` to [low, high]."""
    return max(low, min(high, value))


def to_grid_center(value):
    """Convert a raw coordinate (0-800) to the centre of its grid cell.

    ``center = (v // 100) * 100 + 50``; 800 is mapped into the last cell.
    """
    value = clamp(int(value))
    cell = min(value // CELL, (MAP_MAX // CELL) - 1)
    return cell * CELL + CELL // 2


class PathPlanner:
    """Grid based path finding (L-shaped routes, horizontal first)."""

    @staticmethod
    def manhattan(a, b):
        """Manhattan distance between two points."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def euclidean(a, b):
        """Euclidean distance between two points."""
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5

    @staticmethod
    def is_vertical_special_case(start, target):
        """True when the target is directly above or below the start."""
        return start[0] == target[0] and start[1] != target[1]

    @staticmethod
    def compute_path(start, target):
        """Return list of waypoints from ``start`` to ``target``.

        Movement is horizontal first, then vertical (right-angle turn).
        When the target is directly above/below only a vertical segment
        is produced.
        """
        start = (int(start[0]), int(start[1]))
        target = (int(target[0]), int(target[1]))
        path = [start]
        if start == target:
            return path
        if start[0] != target[0] and start[1] != target[1]:
            path.append((target[0], start[1]))
        path.append(target)
        return path

    @classmethod
    def compute_multi_path(cls, points):
        """Continuous path through several destinations."""
        if not points:
            return []
        path = [tuple(points[0])]
        for nxt in points[1:]:
            segment = cls.compute_path(path[-1], nxt)
            path.extend(segment[1:])
        return path

    @classmethod
    def path_length(cls, path):
        """Total length of a waypoint path."""
        return sum(cls.manhattan(path[i], path[i + 1])
                   for i in range(len(path) - 1))

    @staticmethod
    def step(pos, target, speed):
        """Advance from ``pos`` towards ``target`` by at most ``speed``.

        Horizontal movement is consumed first, then vertical.  Never
        overshoots the target.  Returns the new (x, y).
        """
        x, y = int(pos[0]), int(pos[1])
        tx, ty = int(target[0]), int(target[1])
        budget = max(0, int(speed))
        dx = tx - x
        if dx != 0 and budget > 0:
            move = min(abs(dx), budget)
            x += move if dx > 0 else -move
            budget -= move
        dy = ty - y
        if dy != 0 and budget > 0:
            move = min(abs(dy), budget)
            y += move if dy > 0 else -move
        return clamp(x), clamp(y)
