"""Grid based path planning.

The map is 800x800 units, split into an 8x8 grid of 100x100 cells.
Lines at multiples of 100 are treated as streets.  Restaurants and
customers sit at cell centres (``x*100 + 50``).
"""

import math

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = 8


class GridMap:
    """Static description of the map geometry."""

    def __init__(self, map_size=MAP_SIZE, cell_size=CELL_SIZE):
        self.map_size = map_size
        self.cell_size = cell_size
        self.grid_dimension = map_size // cell_size

    def cell_of(self, x, y):
        """Return the (col, row) cell index containing point (x, y)."""
        return (_clamp_cell(x), _clamp_cell(y))


def _clamp_cell(v):
    """Return the cell index for coordinate ``v`` (clamped to 0..7)."""
    return min(max(int(v) // CELL_SIZE, 0), GRID_DIM - 1)


def to_grid_center(value):
    """Convert a raw coordinate (0-800) to the centre of its grid cell.

    ``center = (v // 100) * 100 + 50``; the boundary value 800 maps to the
    last cell (750).

    Raises:
        ValueError: if value is not an integer in range 0..800.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Coordinate must be an integer: %r" % (value,))
    if value < 0 or value > MAP_SIZE:
        raise ValueError("Coordinate out of range 0-800: %d" % value)
    return _clamp_cell(value) * CELL_SIZE + CELL_SIZE // 2


class Route:
    """A planned route: list of points (including start), speed, time."""

    def __init__(self, points, speed):
        self.points = list(points)
        self.speed = speed
        self.length = PathPlanner.path_length(self.points)
        self.estimated_time = (int(math.ceil(self.length / float(speed)))
                               if speed > 0 else 0)

    def __repr__(self):
        return "Route(points=%r, speed=%r, time=%r)" % (
            self.points, self.speed, self.estimated_time)


class PathPlanner:
    """Street-preferring Manhattan path planner."""

    grid_map = GridMap()

    @staticmethod
    def nearest_street(v):
        """Return the street line (multiple of 100) closest to ``v``."""
        s = ((int(v) + CELL_SIZE // 2) // CELL_SIZE) * CELL_SIZE
        return min(max(s, 0), MAP_SIZE)

    @staticmethod
    def is_special_case(start, target):
        """True when the rider is directly above/below the target.

        That is: same grid column (or identical x) but different y.
        """
        sx, sy = start
        tx, ty = target
        if sy == ty:
            return False
        return sx == tx or _clamp_cell(sx) == _clamp_cell(tx)

    @classmethod
    def plan_route(cls, start, target):
        """Return the waypoints (excluding start) from ``start`` to ``target``.

        Strategy:
          * already aligned on x or y -> straight line;
          * directly above/below (same column) -> vertical then horizontal;
          * otherwise -> go to nearest horizontal street, follow it to the
            target column, then go vertically to the target.
        """
        start = (int(start[0]), int(start[1]))
        target = (int(target[0]), int(target[1]))
        if start == target:
            return []
        sx, sy = start
        tx, ty = target
        if sx == tx or sy == ty:
            return [target]
        if cls.is_special_case(start, target):
            raw = [(sx, ty), (tx, ty)]
        else:
            street_y = cls.nearest_street(sy)
            raw = [(sx, street_y), (tx, street_y), (tx, ty)]
        points = []
        prev = start
        for p in raw:
            if p != prev:
                points.append(p)
                prev = p
        return points

    @classmethod
    def plan_multi(cls, start, targets, speed):
        """Plan a continuous route through several destinations.

        Returns:
            Route whose points include the start point.
        """
        points = [(int(start[0]), int(start[1]))]
        current = points[0]
        for t in targets:
            seg = cls.plan_route(current, t)
            points.extend(seg)
            current = (int(t[0]), int(t[1]))
        return Route(points, speed)

    @staticmethod
    def path_length(points):
        """Manhattan length of a polyline."""
        total = 0
        for a, b in zip(points, points[1:]):
            total += abs(a[0] - b[0]) + abs(a[1] - b[1])
        return total

    @staticmethod
    def cells_on_path(points):
        """Return the set of (col, row) cells touched by the polyline."""
        cells = set()
        if not points:
            return cells
        cells.add((_clamp_cell(points[0][0]), _clamp_cell(points[0][1])))
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            steps = max(abs(bx - ax), abs(by - ay))
            n = max(steps // 10, 1)
            for i in range(n + 1):
                x = ax + (bx - ax) * i / n
                y = ay + (by - ay) * i / n
                cells.add((_clamp_cell(x), _clamp_cell(y)))
        return cells
