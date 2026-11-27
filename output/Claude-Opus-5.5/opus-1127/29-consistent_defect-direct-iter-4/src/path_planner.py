"""Grid based path planning for riders.

The map is an 800x800 coordinate system split into 8x8 cells of
100x100 units.  Lines whose coordinate is a multiple of 100 are
streets.  Restaurants and customers are located at cell centres.
"""

import math

GRID_SIZE = 100
MAP_SIZE = 800
GRID_COUNT = MAP_SIZE // GRID_SIZE


def to_grid_cell(value):
    """Return the grid cell index (0-7) for a raw coordinate.

    Values outside the map are clamped onto the boundary cells.
    """
    try:
        v = int(value)
    except (TypeError, ValueError):
        v = 0
    v = max(0, min(v, MAP_SIZE))
    return min(v // GRID_SIZE, GRID_COUNT - 1)


def to_grid_center(value):
    """Convert a raw coordinate into the centre of its grid cell.

    ``center = (value // 100) * 100 + 50`` with boundary clamping.
    """
    return to_grid_cell(value) * GRID_SIZE + GRID_SIZE // 2


def to_grid_corner(value):
    """Convert a raw coordinate into the top-left corner of its grid cell."""
    return to_grid_cell(value) * GRID_SIZE


class PathPlanner:
    """Grid based pathfinding helper (L-shaped routes along streets)."""

    @staticmethod
    def is_vertical_special(start, target):
        """Return True if the start is directly above or below the target."""
        return start[0] == target[0] and start[1] != target[1]

    @staticmethod
    def plan_route(start, target):
        """Plan a list of waypoints from ``start`` to ``target``.

        Movement is horizontal and vertical only, with at most one
        right-angle turn.  If the rider is currently on a horizontal
        street it travels horizontally first; if it is only on a
        vertical street it travels vertically first.
        """
        sx, sy = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        if (sx, sy) == (tx, ty):
            return []
        if sx == tx or sy == ty:
            return [(tx, ty)]
        on_horizontal = sy % GRID_SIZE == 0
        on_vertical = sx % GRID_SIZE == 0
        if on_horizontal or not on_vertical:
            corner = (tx, sy)
        else:
            corner = (sx, ty)
        return [corner, (tx, ty)]

    @staticmethod
    def plan_full_route(start, restaurant, customer):
        """Plan the full multi-destination route start->restaurant->customer.

        Returns a list of points including the start point.
        """
        points = [(int(start[0]), int(start[1]))]
        first = PathPlanner.plan_route(start, restaurant)
        points.extend(first)
        second = PathPlanner.plan_route(restaurant, customer)
        points.extend(second)
        return points

    @staticmethod
    def route_length(points):
        """Return the total Manhattan length of a list of points."""
        total = 0
        for a, b in zip(points, points[1:]):
            total += abs(a[0] - b[0]) + abs(a[1] - b[1])
        return total

    @staticmethod
    def advance(x, y, route, budget):
        """Move along ``route`` by at most ``budget`` units.

        Returns ``(x, y, remaining_route, moved_distance)``.
        """
        route = list(route)
        moved = 0
        while route and budget > 0:
            wx, wy = route[0]
            dist = abs(wx - x) + abs(wy - y)
            if dist <= budget:
                x, y = wx, wy
                budget -= dist
                moved += dist
                route.pop(0)
                continue
            if wx != x:
                step = budget if wx > x else -budget
                x += step
            else:
                step = budget if wy > y else -budget
                y += step
            moved += budget
            budget = 0
        return x, y, route, moved

    @staticmethod
    def euclidean(a, b):
        """Euclidean distance between two points."""
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    @staticmethod
    def manhattan(a, b):
        """Manhattan distance between two points."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
