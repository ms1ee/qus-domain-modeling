"""Grid based path planning on the 800x800 map.

Streets run along every multiple of 100 on both axes. Restaurants and
customers sit on street intersections (top-left corner of grid cells).
"""

MAP_SIZE = 800
CELL_SIZE = 100


class PathPlanner:
    """Street-first pathfinding utilities."""

    @staticmethod
    def clamp(value):
        """Clamp a coordinate into the map range 0..800."""
        return max(0, min(MAP_SIZE, int(value)))

    @staticmethod
    def to_grid(pos):
        """Convert a raw coordinate pair to the top-left corner of its cell."""
        x, y = pos
        x = PathPlanner.clamp(x)
        y = PathPlanner.clamp(y)
        return ((x // CELL_SIZE) * CELL_SIZE, (y // CELL_SIZE) * CELL_SIZE)

    @staticmethod
    def to_center(pos):
        """Return the centre point of the grid cell containing ``pos``."""
        x, y = pos
        x = min(PathPlanner.clamp(x), MAP_SIZE - 1)
        y = min(PathPlanner.clamp(y), MAP_SIZE - 1)
        return ((x // CELL_SIZE) * CELL_SIZE + 50,
                (y // CELL_SIZE) * CELL_SIZE + 50)

    @staticmethod
    def on_street(x, y):
        """True if the point lies on a street (x or y on a grid line)."""
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    @staticmethod
    def manhattan(a, b):
        """Manhattan distance between two points."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def euclidean(a, b):
        """Euclidean distance between two points."""
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5

    @staticmethod
    def _snap_toward(value, target):
        """Snap a value to a grid line in the direction of ``target``."""
        if value % CELL_SIZE == 0:
            return value
        lower = (value // CELL_SIZE) * CELL_SIZE
        upper = lower + CELL_SIZE
        if target > value:
            snapped = upper
        elif target < value:
            snapped = lower
        else:
            snapped = lower if value - lower <= upper - value else upper
        return PathPlanner.clamp(snapped)

    @staticmethod
    def plan(start, target):
        """Plan an axis-aligned path from ``start`` to ``target``.

        Returns ``(points, special_case)`` where ``points`` is the list of
        waypoints (including start and target) and ``special_case`` is True
        when part of the route had to leave the street network.
        """
        sx, sy = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        points = [(sx, sy)]
        special = False
        x, y = sx, sy
        if (x, y) != (tx, ty):
            if not PathPlanner.on_street(x, y):
                # Off-street: move vertically onto the nearest street first.
                special = True
                ny = PathPlanner._snap_toward(y, ty)
                points.append((x, ny))
                y = ny
            if y % CELL_SIZE == 0:
                # On a horizontal street: go horizontal, then vertical.
                points.append((tx, y))
                points.append((tx, ty))
                if y != ty and tx % CELL_SIZE != 0:
                    special = True
            else:
                # On a vertical street: go vertical, then horizontal.
                points.append((x, ty))
                points.append((tx, ty))
                if x != tx and ty % CELL_SIZE != 0:
                    special = True
        cleaned = []
        for p in points:
            if not cleaned or cleaned[-1] != p:
                cleaned.append(p)
        return cleaned, special

    @staticmethod
    def plan_multi(start, targets):
        """Plan a continuous route through several destinations."""
        route = [tuple(start)]
        special = False
        current = tuple(start)
        for t in targets:
            pts, sp = PathPlanner.plan(current, t)
            special = special or sp
            route.extend(pts[1:])
            current = tuple(t)
        return route, special

    @staticmethod
    def path_length(points):
        """Total length of a polyline of axis-aligned segments."""
        return sum(PathPlanner.manhattan(points[i], points[i + 1])
                   for i in range(len(points) - 1))
