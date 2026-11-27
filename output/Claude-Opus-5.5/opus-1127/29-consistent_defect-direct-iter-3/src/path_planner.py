"""Grid based path planning.

The map is an 800x800 coordinate system split into 100x100 cells.  Lines
where ``x`` or ``y`` is a multiple of 100 are streets.  Paths produced by
:class:`PathPlanner` are made of axis aligned segments (straight lines and
right angle turns) that prefer to run along streets.
"""

MAP_SIZE = 800
CELL_SIZE = 100


def _clamp(value, low=0, high=MAP_SIZE):
    """Clamp ``value`` into ``[low, high]``."""
    return max(low, min(high, value))


def nearest_street(value):
    """Return the street coordinate (multiple of 100) closest to ``value``."""
    return _clamp(((int(value) + CELL_SIZE // 2) // CELL_SIZE) * CELL_SIZE)


class PathPlanner:
    """Path finding logic for riders."""

    @staticmethod
    def is_on_street(x, y):
        """Return True if the point lies on a street line."""
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    @staticmethod
    def is_special_case(start, end):
        """Return True if the rider is directly above/below (or level with)
        the target while not standing on a street that connects them."""
        sx, sy = int(start[0]), int(start[1])
        ex, ey = int(end[0]), int(end[1])
        if (sx, sy) == (ex, ey):
            return False
        if sx == ex and sx % CELL_SIZE != 0:
            return True
        if sy == ey and sy % CELL_SIZE != 0:
            return True
        return False

    @staticmethod
    def _cleanup(start, points):
        """Remove consecutive duplicates and points equal to the start."""
        result = []
        prev = (int(start[0]), int(start[1]))
        for p in points:
            p = (int(p[0]), int(p[1]))
            if p != prev:
                result.append(p)
                prev = p
        return result

    @staticmethod
    def plan_path(start, end):
        """Plan a street-preferring path from ``start`` to ``end``.

        Returns a list of waypoints (tuples), excluding the start point and
        ending with ``end``.  Consecutive waypoints are always axis aligned.
        An empty list is returned when start equals end.
        """
        sx, sy = int(start[0]), int(start[1])
        ex, ey = int(end[0]), int(end[1])
        if (sx, sy) == (ex, ey):
            return []

        # Special case: directly above / below the target.
        if sx == ex:
            if sx % CELL_SIZE == 0:
                return [(ex, ey)]
            vx = nearest_street(sx)
            return PathPlanner._cleanup(start, [(vx, sy), (vx, ey), (ex, ey)])
        # Special case: directly left / right of the target.
        if sy == ey:
            if sy % CELL_SIZE == 0:
                return [(ex, ey)]
            hy = nearest_street(sy)
            return PathPlanner._cleanup(start, [(sx, hy), (ex, hy), (ex, ey)])

        # Standard right-angle paths along streets.
        if sy % CELL_SIZE == 0 and ex % CELL_SIZE == 0:
            return PathPlanner._cleanup(start, [(ex, sy), (ex, ey)])
        if sx % CELL_SIZE == 0 and ey % CELL_SIZE == 0:
            return PathPlanner._cleanup(start, [(sx, ey), (ex, ey)])

        # General case: reach the nearest horizontal street, ride along it
        # to the vertical street closest to the target, then approach.
        hy = nearest_street(sy)
        vx = nearest_street(ex)
        points = [(sx, hy), (vx, hy), (vx, ey), (ex, ey)]
        return PathPlanner._cleanup(start, points)

    @staticmethod
    def plan_multi(start, stops):
        """Plan a continuous path visiting every point in ``stops``."""
        path = []
        current = (int(start[0]), int(start[1]))
        for stop in stops:
            segment = PathPlanner.plan_path(current, stop)
            path.extend(segment)
            current = (int(stop[0]), int(stop[1]))
        return path

    @staticmethod
    def path_length(start, path):
        """Return the Manhattan length of a path starting at ``start``."""
        total = 0
        cx, cy = int(start[0]), int(start[1])
        for x, y in path:
            total += abs(x - cx) + abs(y - cy)
            cx, cy = x, y
        return total
