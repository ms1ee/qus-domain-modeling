"""Grid based path planning for riders."""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE


def to_grid_center(value):
    """Convert a raw coordinate (0-800) into the center of its grid cell.

    ``center = (v // 100) * 100 + 50``; the boundary value 800 is clamped
    into the last cell so the result always lies inside the map.
    """
    v = int(value)
    v = max(0, min(MAP_SIZE - 1, v))
    return (v // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2


def cell_index(value):
    """Return the grid index (0-7) for a coordinate."""
    return max(0, min(GRID_DIM - 1, int(value) // CELL_SIZE))


class PathPlanner:
    """Right angle (Manhattan) path planning on the 8x8 grid.

    The rider first travels horizontally until it is aligned with the target
    column, then vertically.  When the rider is directly above or below the
    target (same x) the special case of pure vertical movement applies.
    Riders do not block each other, so paths can never deadlock.
    """

    @staticmethod
    def is_special_case(start, target):
        """True when the rider is directly above/below the target."""
        return start[0] == target[0] and start[1] != target[1]

    @staticmethod
    def plan_path(start, target):
        """Return the list of waypoints from ``start`` to ``target``."""
        start = (int(start[0]), int(start[1]))
        target = (int(target[0]), int(target[1]))
        if start == target:
            return [start]
        if start[0] == target[0] or start[1] == target[1]:
            return [start, target]
        corner = (target[0], start[1])
        return [start, corner, target]

    @staticmethod
    def plan_multi(start, destinations):
        """Plan a continuous path through several destinations."""
        path = [(int(start[0]), int(start[1]))]
        current = path[0]
        for dest in destinations:
            seg = PathPlanner.plan_path(current, dest)
            path.extend(seg[1:])
            current = (int(dest[0]), int(dest[1]))
        return path

    @staticmethod
    def path_length(path):
        """Total Manhattan length of a waypoint path."""
        total = 0
        for a, b in zip(path, path[1:]):
            total += abs(a[0] - b[0]) + abs(a[1] - b[1])
        return total

    @staticmethod
    def step(x, y, target, speed):
        """Advance from (x, y) toward ``target`` by at most ``speed`` units.

        Returns ``(new_x, new_y, special_case)``.
        """
        special = PathPlanner.is_special_case((x, y), target)
        remaining = max(0, int(speed))
        tx, ty = int(target[0]), int(target[1])
        x, y = int(x), int(y)
        # horizontal leg first
        if remaining and x != tx:
            d = min(remaining, abs(tx - x))
            x += d if tx > x else -d
            remaining -= d
        # vertical leg
        if remaining and x == tx and y != ty:
            d = min(remaining, abs(ty - y))
            y += d if ty > y else -d
            remaining -= d
        return x, y, special

    @staticmethod
    def sample_points(path, step=10):
        """Yield points along a waypoint path every ``step`` units."""
        if not path:
            return
        yield path[0]
        for a, b in zip(path, path[1:]):
            x, y = a
            while (x, y) != tuple(b):
                x, y, _ = PathPlanner.step(x, y, b, step)
                yield (x, y)
