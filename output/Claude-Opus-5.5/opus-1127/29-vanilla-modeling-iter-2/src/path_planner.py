"""Grid-based path planning (street-first Manhattan routing)."""

import math

from grid_map import CELL_SIZE, cell_index, clamp, is_street, nearest_street


def _street_toward(target, current):
    """Return the street line adjacent to ``target`` closest to ``current``."""
    target = int(target)
    if is_street(target):
        return target
    low = (target // CELL_SIZE) * CELL_SIZE
    high = clamp(low + CELL_SIZE)
    return low if abs(current - low) <= abs(current - high) else high


class Route:
    """A sequence of waypoints and its estimated travel time."""

    def __init__(self, points, speed=10):
        self.points = list(points)
        self.length = PathPlanner.path_length(self.points)
        self.estimated_time = PathPlanner.estimate_time(self.length, speed)

    def __repr__(self):
        return "Route(points=%r, length=%r, estimated_time=%r)" % (
            self.points, self.length, self.estimated_time)


class PathPlanner:
    """Plans routes on the 8x8 street grid.

    Riders first move onto the nearest street, travel along streets with
    right-angle turns, and finally step into the target cell centre.
    """

    def __init__(self, grid=None):
        self.grid = grid

    @staticmethod
    def is_directly_vertical(start, target):
        """Special case: rider is directly above or below the target."""
        return int(start[0]) == int(target[0]) and int(start[1]) != int(target[1])

    def plan(self, start, target):
        """Return a list of waypoints from ``start`` to ``target`` (inclusive)."""
        sx, sy = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        points = [(sx, sy)]

        def add(p):
            if p != points[-1]:
                points.append(p)

        if (sx, sy) == (tx, ty):
            return points

        same_cell = (cell_index(sx) == cell_index(tx)
                     and cell_index(sy) == cell_index(ty)
                     and not is_street(sx) and not is_street(sy))
        if same_cell:
            add((tx, sy))
            add((tx, ty))
            return points

        on_h = is_street(sy)
        on_v = is_street(sx)
        if not on_h and not on_v:
            ny = nearest_street(sy)
            nx = nearest_street(sx)
            if abs(ny - sy) <= abs(nx - sx):
                add((sx, ny))
                on_h = True
            else:
                add((nx, sy))
                on_v = True

        cx, cy = points[-1]
        if is_street(cy):
            tsx = _street_toward(tx, cx)
            add((tsx, cy))
            add((tsx, ty))
            add((tx, ty))
        else:
            tsy = _street_toward(ty, cy)
            add((cx, tsy))
            add((tx, tsy))
            add((tx, ty))
        return points

    def plan_multi(self, start, targets):
        """Plan a continuous path through several destinations."""
        points = [(int(start[0]), int(start[1]))]
        for target in targets:
            segment = self.plan(points[-1], target)
            points.extend(segment[1:])
        return points

    @staticmethod
    def path_length(points):
        """Return the total Manhattan length of a polyline."""
        total = 0
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            total += abs(x2 - x1) + abs(y2 - y1)
        return total

    @staticmethod
    def estimate_time(length, speed):
        """Return the number of ticks needed to travel ``length``."""
        if speed <= 0:
            return 0 if length == 0 else -1
        return int(math.ceil(length / float(speed)))

    def build_route(self, start, targets, speed=10):
        """Return a :class:`Route` through ``targets``."""
        return Route(self.plan_multi(start, targets), speed)
