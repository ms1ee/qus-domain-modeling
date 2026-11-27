"""Grid based path planning.

The map is 800x800 units divided in 8x8 cells of 100x100 units.  Streets
run along the grid lines (x or y a multiple of 100).  Restaurants and
customers are located at cell centres (``(v // 100) * 100 + 50``).  A rider
serves a location from its *access point*, which is the middle of the
street segment just below the cell centre: ``(cx, cy - 50)``.
"""

import math

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE


def manhattan(a, b):
    """Return the Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Route:
    """A planned route made of axis-aligned waypoints.

    Attributes:
        waypoints: list of (x, y) tuples, including the start point.
        length: total travelled distance in units.
        speed: rider speed used for the time estimate.
        estimated_time: ticks needed at ``speed`` (ceil).
    """

    def __init__(self, waypoints, speed=None):
        self.waypoints = [tuple(p) for p in waypoints]
        self.length = sum(manhattan(self.waypoints[i], self.waypoints[i + 1])
                          for i in range(len(self.waypoints) - 1))
        self.speed = speed
        if speed:
            self.estimated_time = int(math.ceil(self.length / float(speed)))
        else:
            self.estimated_time = 0

    def __repr__(self):
        return "Route(length=%d, waypoints=%r)" % (self.length, self.waypoints)


class PathPlanner:
    """Street-following path planner for the 8x8 grid."""

    @staticmethod
    def clamp(value, low=0, high=MAP_SIZE):
        """Clamp ``value`` to ``[low, high]``."""
        return max(low, min(high, int(value)))

    @staticmethod
    def to_grid_center_value(v):
        """Convert one input coordinate to the centre of its cell."""
        v = PathPlanner.clamp(v, 0, MAP_SIZE - 1)
        return (v // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2

    @staticmethod
    def to_grid_center(x, y):
        """Convert an input point to the centre of the grid cell it lies in.

        Boundary values (e.g. 800) are mapped into the last cell.
        """
        return (PathPlanner.to_grid_center_value(x),
                PathPlanner.to_grid_center_value(y))

    @staticmethod
    def cell_index(pos):
        """Return the (column, row) cell index of a point."""
        x = PathPlanner.clamp(pos[0], 0, MAP_SIZE - 1)
        y = PathPlanner.clamp(pos[1], 0, MAP_SIZE - 1)
        return x // CELL_SIZE, y // CELL_SIZE

    @staticmethod
    def access_point(pos):
        """Return the street point from which a cell-centre location is served."""
        cx, cy = PathPlanner.to_grid_center(pos[0], pos[1])
        return cx, cy - CELL_SIZE // 2

    @staticmethod
    def is_on_street(x, y):
        """Return True if the point lies on a street (a grid line)."""
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    @staticmethod
    def nearest_street_point(x, y):
        """Return the closest point on a street (axis aligned move)."""
        if PathPlanner.is_on_street(x, y):
            return x, y
        nx = int(round(x / float(CELL_SIZE))) * CELL_SIZE
        ny = int(round(y / float(CELL_SIZE))) * CELL_SIZE
        nx = PathPlanner.clamp(nx)
        ny = PathPlanner.clamp(ny)
        if abs(nx - x) <= abs(ny - y):
            return nx, y
        return x, ny

    @staticmethod
    def _plan_horizontal(start, target):
        """Plan assuming ``target`` lies on a horizontal street."""
        special = False
        pts = [tuple(start)]
        x, y = start
        tx, ty = target
        if not PathPlanner.is_on_street(x, y):
            x, y = PathPlanner.nearest_street_point(x, y)
            pts.append((x, y))
        if (x, y) == (tx, ty):
            return pts, special
        if y == ty:
            pts.append((tx, ty))
        elif x % CELL_SIZE == 0:
            pts.append((x, ty))
            pts.append((tx, ty))
        else:
            # On a horizontal street, must reach a vertical street first.
            if x == tx:
                special = True  # directly above / below the target
            if tx % CELL_SIZE == 0:
                vx = tx
            else:
                lo = (tx // CELL_SIZE) * CELL_SIZE
                hi = lo + CELL_SIZE
                if x <= lo:
                    vx = lo
                elif x >= hi:
                    vx = hi
                else:
                    vx = lo if (x - lo) <= (hi - x) else hi
            pts.append((vx, y))
            pts.append((vx, ty))
            pts.append((tx, ty))
        return pts, special

    @staticmethod
    def plan(start, target):
        """Plan a street path from ``start`` to ``target``.

        Returns:
            (waypoints, special_case) where waypoints includes the start and
            the target, and special_case is True when a detour was needed
            because the rider was directly above/below the target.
        """
        start = (int(start[0]), int(start[1]))
        target = (int(target[0]), int(target[1]))
        if target[1] % CELL_SIZE != 0 and target[0] % CELL_SIZE == 0:
            # Target on a vertical street: solve the mirrored problem.
            pts, special = PathPlanner._plan_horizontal(
                (start[1], start[0]), (target[1], target[0]))
            pts = [(p[1], p[0]) for p in pts]
        elif target[1] % CELL_SIZE != 0:
            target = PathPlanner.nearest_street_point(*target)
            pts, special = PathPlanner.plan(start, target)
            return pts, special
        else:
            pts, special = PathPlanner._plan_horizontal(start, target)
        cleaned = []
        for p in pts:
            if not cleaned or cleaned[-1] != p:
                cleaned.append(p)
        return cleaned, special

    @staticmethod
    def plan_multi(start, targets, speed=None):
        """Plan a continuous route through several targets in order."""
        waypoints = [tuple(start)]
        current = tuple(start)
        for t in targets:
            pts, _ = PathPlanner.plan(current, t)
            for p in pts[1:]:
                if waypoints[-1] != p:
                    waypoints.append(p)
            current = tuple(t)
        return Route(waypoints, speed)

    @staticmethod
    def street_distance(a, b):
        """Return the street path length between two street points."""
        pts, _ = PathPlanner.plan(a, b)
        return Route(pts).length
