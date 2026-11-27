"""Grid based path planning.

The map is 800x800 units split into 8x8 cells of 100x100.  Grid lines
(coordinates that are multiples of 100) are *streets*.  Riders prefer to
travel along streets: they leave their current block to the nearest
street, travel along horizontal and vertical streets with right-angle
turns, and finally enter the destination block.
"""


class PathPlanner:
    """Path planning helper for grid based movement."""

    GRID = 100
    SIZE = 800

    @staticmethod
    def to_grid_center(c):
        """Convert a raw coordinate (0-800) to its grid cell centre."""
        c = int(c)
        c = max(0, min(PathPlanner.SIZE - 1, c))
        return (c // PathPlanner.GRID) * PathPlanner.GRID + PathPlanner.GRID // 2

    @staticmethod
    def to_grid_index(c):
        """Return the grid index (0-7) of a coordinate."""
        c = max(0, int(c))
        return min(PathPlanner.SIZE // PathPlanner.GRID - 1, c // PathPlanner.GRID)

    @classmethod
    def cell_of(cls, x, y):
        """Return the (gx, gy) grid cell containing a point."""
        return cls.to_grid_index(x), cls.to_grid_index(y)

    @staticmethod
    def is_on_street(x, y):
        """True if the point lies on a street (grid line)."""
        return int(x) % PathPlanner.GRID == 0 or int(y) % PathPlanner.GRID == 0

    @staticmethod
    def nearest_street(c, toward):
        """Nearest street coordinate to ``c``; ties broken toward ``toward``."""
        g = PathPlanner.GRID
        if c % g == 0:
            return c
        lower = (c // g) * g
        upper = lower + g
        dl, du = c - lower, upper - c
        if dl < du:
            s = lower
        elif du < dl:
            s = upper
        else:
            s = upper if toward > c else lower
        return max(0, min(PathPlanner.SIZE, s))

    @staticmethod
    def _simplify(start, pts):
        """Remove duplicate and collinear waypoints."""
        full = [tuple(start)]
        for p in pts:
            p = (int(p[0]), int(p[1]))
            if p == full[-1]:
                continue
            if len(full) >= 2:
                a, b = full[-2], full[-1]
                if (a[0] == b[0] == p[0]) or (a[1] == b[1] == p[1]):
                    full[-1] = p
                    if len(full) >= 2 and full[-1] == full[-2]:
                        full.pop()
                    continue
            full.append(p)
        return full[1:]

    def plan(self, start, target):
        """Plan a path from ``start`` to ``target``.

        :return: tuple ``(waypoints, special_case)``; waypoints exclude the
                 start point.  ``special_case`` is True when the target is
                 directly above or below the start in another cell, in which
                 case the rider detours onto a parallel street.
        """
        sx, sy = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        if (sx, sy) == (tx, ty):
            return [], False
        if self.cell_of(sx, sy) == self.cell_of(tx, ty):
            pts = [(tx, sy), (tx, ty)]
            special = False
        else:
            hy = self.nearest_street(sy, ty)
            vx = self.nearest_street(tx, sx)
            pts = [(sx, hy), (vx, hy), (vx, ty), (tx, ty)]
            special = sx == tx
        return self._simplify((sx, sy), pts), special

    def plan_route(self, points):
        """Plan a continuous route through several destinations.

        :param points: list of points; the first is the start.
        :return: list of waypoints including the start point.
        """
        if not points:
            return []
        route = [(int(points[0][0]), int(points[0][1]))]
        for target in points[1:]:
            wps, _ = self.plan(route[-1], target)
            route.extend(wps)
        return route

    @staticmethod
    def path_length(points):
        """Total Manhattan length of a polyline."""
        total = 0
        for a, b in zip(points, points[1:]):
            total += abs(a[0] - b[0]) + abs(a[1] - b[1])
        return total

    def distance(self, start, target):
        """Length of the planned path between two points."""
        wps, _ = self.plan(start, target)
        return self.path_length([tuple(start)] + wps)
