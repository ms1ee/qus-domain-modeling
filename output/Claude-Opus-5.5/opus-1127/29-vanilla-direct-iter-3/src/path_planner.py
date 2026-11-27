"""Grid-based path planning for riders.

The map is an 800x800 coordinate system divided into an 8x8 grid of
100x100 cells.  Riders move only horizontally or vertically (right-angle
turns).  The planner produces axis-aligned waypoint lists.  Because every
plan is computed independently and riders never block each other, the
planner is free of path conflicts and deadlocks.
"""

import math

MAP_SIZE = 800
CELL_SIZE = 100
GRID_SIZE = MAP_SIZE // CELL_SIZE


class PathPlanner:
    """Collection of path-finding helpers (all static)."""

    @staticmethod
    def clamp(value):
        """Clamp a coordinate into the valid map range 0..800."""
        return max(0, min(MAP_SIZE, int(value)))

    @staticmethod
    def to_grid_center(x, y):
        """Convert raw coordinates into the centre of their grid cell.

        ``center = (v // 100) * 100 + 50``.  The boundary value 800 belongs
        to the last cell, so it maps to 750.
        """
        def conv(v):
            v = max(0, min(MAP_SIZE - 1, int(v)))
            return (v // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2
        return conv(x), conv(y)

    @staticmethod
    def grid_cell(x, y):
        """Return the (column, row) grid cell index of a coordinate."""
        col = min(GRID_SIZE - 1, max(0, int(x) // CELL_SIZE))
        row = min(GRID_SIZE - 1, max(0, int(y) // CELL_SIZE))
        return col, row

    @staticmethod
    def is_street(x, y):
        """Return True if the point is a road point.

        Points where both coordinates are integer hundreds are
        restaurant/customer locations; everything else is road.
        """
        return not (int(x) % CELL_SIZE == 0 and int(y) % CELL_SIZE == 0)

    @staticmethod
    def is_special_case(start, target):
        """Return True when the rider is directly above or below the target.

        That is, both points lie in the same grid column but are not on
        the same horizontal line.
        """
        sx, sy = start
        tx, ty = target
        if sy == ty:
            return False
        return PathPlanner.grid_cell(sx, sy)[0] == PathPlanner.grid_cell(tx, ty)[0]

    @staticmethod
    def plan_path(start, target):
        """Plan an axis-aligned path from ``start`` to ``target``.

        Returns a list of waypoints (excluding ``start``) ending in
        ``target``.  Returns an empty list when already at the target.

        * Aligned points: straight line.
        * Directly above/below (same grid column): vertical first, then a
          short horizontal adjustment.
        * Otherwise: horizontal along the street first, then vertical.
        """
        sx, sy = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        if (sx, sy) == (tx, ty):
            return []
        if sx == tx or sy == ty:
            return [(tx, ty)]
        if PathPlanner.is_special_case((sx, sy), (tx, ty)):
            return [(sx, ty), (tx, ty)]
        return [(tx, sy), (tx, ty)]

    @staticmethod
    def plan_route(start, destinations):
        """Plan a continuous multi-destination route.

        Returns the full polyline including ``start``.
        """
        points = [(int(start[0]), int(start[1]))]
        current = points[0]
        for dest in destinations:
            for wp in PathPlanner.plan_path(current, dest):
                points.append(wp)
            current = (int(dest[0]), int(dest[1]))
        return points

    @staticmethod
    def path_length(points):
        """Total Manhattan length of a polyline."""
        total = 0
        for a, b in zip(points, points[1:]):
            total += abs(a[0] - b[0]) + abs(a[1] - b[1])
        return total

    @staticmethod
    def euclidean(a, b):
        """Euclidean distance between two points."""
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
