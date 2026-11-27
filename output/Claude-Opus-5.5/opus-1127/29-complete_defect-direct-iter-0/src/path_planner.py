"""Grid based path planning for riders.

The map is 800x800 units split into an 8x8 grid of 100x100 cells.
Grid lines (x or y multiple of 100) are treated as streets, and riders
prefer to travel along them.  Every path consists only of horizontal and
vertical segments (right-angle turns).

Riders do not block each other on the map, and every path is computed
deterministically from (start, end), so path conflicts and deadlocks
cannot occur.
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE


class PathPlanner:
    """Collection of grid pathfinding helpers."""

    @staticmethod
    def clamp(v, low=0, high=MAP_SIZE):
        """Clamp ``v`` into [low, high]."""
        return max(low, min(high, int(v)))

    @staticmethod
    def to_grid_index(v):
        """Convert a raw coordinate (0-800) into a grid index (0-7)."""
        v = PathPlanner.clamp(v)
        return min(v, MAP_SIZE - 1) // CELL_SIZE

    @staticmethod
    def to_grid_center(v):
        """Convert a raw coordinate into the centre of its grid cell.

        ``center = (v // 100) * 100 + 50``; the boundary value 800 is
        mapped to the last cell (750).
        """
        return PathPlanner.to_grid_index(v) * CELL_SIZE + CELL_SIZE // 2

    @staticmethod
    def point_to_center(point):
        """Convert an (x, y) point into its cell-centre point."""
        return (PathPlanner.to_grid_center(point[0]),
                PathPlanner.to_grid_center(point[1]))

    @staticmethod
    def is_on_street(x, y):
        """Return True if the point lies on a street (grid line)."""
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    @staticmethod
    def _street_toward(v, target):
        """Nearest grid line from ``v`` in the direction of ``target``."""
        if v % CELL_SIZE == 0:
            return v
        if target > v:
            return min(MAP_SIZE, (v // CELL_SIZE + 1) * CELL_SIZE)
        return (v // CELL_SIZE) * CELL_SIZE

    @staticmethod
    def is_special_case(start, end):
        """Return True when start and end share a column or row."""
        sx, sy = start
        ex, ey = end
        return (sx == ex) != (sy == ey)

    @staticmethod
    def find_path(start, end):
        """Return the list of waypoints from ``start`` to ``end``.

        The start point itself is not included; the end point is the last
        waypoint.  Returns an empty list when start == end.
        """
        sx, sy = int(start[0]), int(start[1])
        ex, ey = int(end[0]), int(end[1])
        if (sx, sy) == (ex, ey):
            return []
        if sx == ex:
            # Directly above/below: use the vertical street to the left.
            if sx % CELL_SIZE == 0:
                pts = [(ex, ey)]
            else:
                xs = (sx // CELL_SIZE) * CELL_SIZE
                pts = [(xs, sy), (xs, ey), (ex, ey)]
        elif sy == ey:
            if sy % CELL_SIZE == 0:
                pts = [(ex, ey)]
            else:
                ys = (sy // CELL_SIZE) * CELL_SIZE
                pts = [(sx, ys), (ex, ys), (ex, ey)]
        else:
            ys = PathPlanner._street_toward(sy, ey)
            pts = [(sx, ys), (ex, ys), (ex, ey)]
        result = []
        prev = (sx, sy)
        for p in pts:
            if p != prev:
                result.append(p)
                prev = p
        return result

    @staticmethod
    def find_multi_path(start, stops):
        """Continuous path visiting each stop in order (e.g. restaurant,
        then customer)."""
        path = []
        cur = tuple(start)
        for stop in stops:
            path.extend(PathPlanner.find_path(cur, stop))
            cur = tuple(stop)
        return path

    @staticmethod
    def path_length(start, waypoints):
        """Manhattan length of the path starting at ``start``."""
        total = 0
        cx, cy = start
        for x, y in waypoints:
            total += abs(x - cx) + abs(y - cy)
            cx, cy = x, y
        return total

    @staticmethod
    def manhattan(a, b):
        """Manhattan distance between two points."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
