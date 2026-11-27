"""Grid map definition and street-based path planning."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

CELL_SIZE = 100
MAP_SIZE = 800
GRID_DIMENSION = MAP_SIZE // CELL_SIZE

Point = Tuple[int, int]


class GridMap:
    """An 8x8 grid of 100x100 cells covering an 800x800 coordinate space.

    Grid lines (x or y a multiple of the cell size) are streets; cell
    centres host restaurants and customers.
    """

    def __init__(self, width=MAP_SIZE, height=MAP_SIZE, cell_size=CELL_SIZE):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.grid_dimension = width // cell_size

    def clamp(self, value, upper=None):
        """Clamp a coordinate into the map range."""
        upper = self.width if upper is None else upper
        return max(0, min(int(value), upper))

    def to_cell_center(self, value):
        """Convert a raw coordinate into the centre of its grid cell."""
        v = max(0, min(int(value), self.width - 1))
        return (v // self.cell_size) * self.cell_size + self.cell_size // 2

    def cell_of(self, x, y):
        """Return (column, row) of the cell containing the point."""
        cx = max(0, min(int(x), self.width - 1)) // self.cell_size
        cy = max(0, min(int(y), self.height - 1)) // self.cell_size
        return cx, cy

    def is_street(self, x, y):
        """True if the point lies on a street (grid line)."""
        return x % self.cell_size == 0 or y % self.cell_size == 0


@dataclass
class Waypoint:
    """A single point on a route."""
    x: int
    y: int
    sequence: int


@dataclass
class Route:
    """A planned route made of axis-aligned segments."""
    waypoints: List[Waypoint] = field(default_factory=list)
    speed: int = 20
    length: int = 0
    estimated_time: int = 0

    def points(self) -> List[Point]:
        """Return the route as a list of (x, y) tuples."""
        return [(w.x, w.y) for w in self.waypoints]


def manhattan(a: Point, b: Point) -> int:
    """Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class PathPlanner:
    """Plans routes that travel along streets with right-angle turns."""

    def __init__(self, cell_size=CELL_SIZE, map_size=MAP_SIZE):
        self.cell_size = cell_size
        self.map_size = map_size

    # ------------------------------------------------------------------ utils
    def is_street(self, x, y):
        """True if (x, y) is on a grid line."""
        return x % self.cell_size == 0 or y % self.cell_size == 0

    @staticmethod
    def is_special_case(sx, sy, tx, ty):
        """Rider directly above or below its target (same column)."""
        return sx == tx and sy != ty

    def _best_line(self, a, b):
        """Choose a grid line minimising |a-l| + |l-b|."""
        cs = self.cell_size
        cands = set()
        for v in (a, b):
            cands.add((v // cs) * cs)
            cands.add(-(-v // cs) * cs)
        cands = {max(0, min(c, self.map_size)) for c in cands}
        return min(cands, key=lambda l: (abs(a - l) + abs(l - b), abs(a - l), l))

    @staticmethod
    def _dedupe(points, start):
        result = []
        prev = start
        for p in points:
            if p != prev:
                result.append(p)
                prev = p
        return result

    def _street_route(self, x, y, ex, ey):
        cs = self.cell_size
        if (x, y) == (ex, ey):
            return []
        on_h, on_v = y % cs == 0, x % cs == 0
        e_h, e_v = ey % cs == 0, ex % cs == 0
        if on_h and e_h and y == ey:
            return [(ex, ey)]
        if on_v and e_v and x == ex:
            return [(ex, ey)]
        if on_v and e_h:
            return [(x, ey), (ex, ey)]
        if on_h and e_v:
            return [(ex, y), (ex, ey)]
        if on_v:
            yh = self._best_line(y, ey)
            return [(x, yh), (ex, yh), (ex, ey)]
        xv = self._best_line(x, ex)
        return [(xv, y), (xv, ey), (ex, ey)]

    # ---------------------------------------------------------------- planning
    def plan(self, sx, sy, tx, ty) -> List[Point]:
        """Plan a path from (sx, sy) to (tx, ty).

        Returns the list of waypoints (excluding the start). Consecutive
        waypoints are always axis-aligned.
        """
        cs = self.cell_size
        sx, sy, tx, ty = int(sx), int(sy), int(tx), int(ty)
        if (sx, sy) == (tx, ty):
            return []
        # Both inside the same cell: move directly inside the cell.
        if (not self.is_street(sx, sy) and not self.is_street(tx, ty)
                and sx // cs == tx // cs and sy // cs == ty // cs):
            return self._dedupe([(sx, ty), (tx, ty)], (sx, sy))
        points = []
        x, y = sx, sy
        if not self.is_street(x, y):
            # Exit the cell to the street on its top edge.
            y = (y // cs) * cs
            points.append((x, y))
        if self.is_street(tx, ty):
            entry, final = (tx, ty), None
        else:
            entry, final = (tx, (ty // cs) * cs), (tx, ty)
        points.extend(self._street_route(x, y, entry[0], entry[1]))
        if final is not None:
            points.append(final)
        return self._dedupe(points, (sx, sy))

    def path_length(self, start: Point, points: List[Point]) -> int:
        """Total Manhattan length of a path."""
        total, prev = 0, start
        for p in points:
            total += manhattan(prev, p)
            prev = p
        return total

    def plan_multi(self, start: Point, targets: List[Point]):
        """Plan a continuous path visiting several destinations in order.

        Returns (points, length).
        """
        points, pos = [], start
        for t in targets:
            seg = self.plan(pos[0], pos[1], t[0], t[1])
            points.extend(seg)
            pos = t
        return points, self.path_length(start, points)

    def build_route(self, start: Point, points: List[Point], speed: int) -> Route:
        """Wrap a list of points into a Route object."""
        all_pts = [start] + list(points)
        wps = [Waypoint(p[0], p[1], i) for i, p in enumerate(all_pts)]
        length = self.path_length(start, points)
        est = -(-length // speed) if speed > 0 else 0
        return Route(waypoints=wps, speed=speed, length=length,
                     estimated_time=est)


def first_axis_step(cur: Point, target: Point) -> Optional[Point]:
    """Helper: direction vector toward target (x first, then y)."""
    dx, dy = target[0] - cur[0], target[1] - cur[1]
    if dx:
        return (1 if dx > 0 else -1, 0)
    if dy:
        return (0, 1 if dy > 0 else -1)
    return None
