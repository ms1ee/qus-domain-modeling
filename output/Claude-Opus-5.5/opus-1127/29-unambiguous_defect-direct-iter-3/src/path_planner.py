"""Grid-based path planning.

The map is 800x800 units split into 8x8 cells of 100x100 units.  Streets
run along the grid lines (x or y multiple of 100).  Restaurants and
customers are located at cell centres (``(v // 100) * 100 + 50``).

A route always consists of axis-aligned segments that follow streets and
finally step 50 units into the target cell centre.  Riders never block each
other (streets have unlimited capacity), so path conflicts and deadlocks
cannot occur.
"""

CELL = 100
HALF = 50
MAP_SIZE = 800


class PathPlanner:
    """Path planning helper (all methods are static / class methods)."""

    CELL = CELL
    MAP_SIZE = MAP_SIZE

    @staticmethod
    def to_center(value):
        """Convert a raw coordinate (0-800) to its grid cell centre."""
        v = int(value)
        v = max(0, min(v, MAP_SIZE - 1))
        return (v // CELL) * CELL + HALF

    @classmethod
    def to_grid_center(cls, pos):
        """Convert an ``(x, y)`` pair to the centre of its grid cell."""
        return (cls.to_center(pos[0]), cls.to_center(pos[1]))

    @staticmethod
    def is_on_street(x, y):
        """True if the point lies on a street (grid line)."""
        return x % CELL == 0 or y % CELL == 0

    @classmethod
    def plan_with_info(cls, start, target):
        """Plan a street route from ``start`` to ``target``.

        Returns ``(waypoints, special_case)`` where ``waypoints`` excludes the
        start point and ends at the target, and ``special_case`` is True if
        the rider was directly above/below the target and had to detour to a
        side street.
        """
        x, y = int(round(start[0])), int(round(start[1]))
        tx, ty = int(round(target[0])), int(round(target[1]))
        special = False
        if (x, y) == (tx, ty):
            return [], False
        pts = []

        on_h = y % CELL == 0
        on_v = x % CELL == 0
        if not on_h and not on_v:
            if (x // CELL, y // CELL) == (tx // CELL, ty // CELL):
                # Same cell interior: simple L-shaped move.
                pts = [(tx, y), (tx, ty)]
                return cls._clean((x, y), pts), False
            # Step out of the cell onto the nearest horizontal street
            # in the direction of the target.
            if ty > y:
                ny = (y // CELL + 1) * CELL
            else:
                ny = (y // CELL) * CELL
            pts.append((x, ny))
            y = ny

        # Horizontal street adjacent to the target from which we enter it.
        ey = ty - HALF if y <= ty else ty + HALF

        if y == ey:
            pts.append((tx, ey))
            pts.append((tx, ty))
        else:
            if x % CELL != 0:
                if tx > x:
                    nx = (x // CELL + 1) * CELL
                elif tx < x:
                    nx = (x // CELL) * CELL
                else:
                    # Directly above/below the target: detour via side street.
                    special = True
                    nx = (x // CELL) * CELL
                pts.append((nx, y))
                x = nx
            pts.append((x, ey))
            pts.append((tx, ey))
            pts.append((tx, ty))
        return cls._clean(start, pts), special

    @classmethod
    def plan(cls, start, target):
        """Return only the waypoints of :meth:`plan_with_info`."""
        return cls.plan_with_info(start, target)[0]

    @staticmethod
    def _clean(start, pts):
        """Remove duplicate consecutive points (and points equal to start)."""
        result = []
        prev = (int(round(start[0])), int(round(start[1])))
        for p in pts:
            p = (int(p[0]), int(p[1]))
            if p != prev:
                result.append(p)
                prev = p
        return result

    @staticmethod
    def polyline_length(points):
        """Total Manhattan length of a polyline."""
        total = 0
        for a, b in zip(points, points[1:]):
            total += abs(a[0] - b[0]) + abs(a[1] - b[1])
        return total

    @classmethod
    def path_length(cls, start, target):
        """Length of the planned route from ``start`` to ``target``."""
        pts = [tuple(start)] + cls.plan(start, target)
        return cls.polyline_length(pts)

    @staticmethod
    def sample_polyline(points, step=HALF):
        """Return points sampled every ``step`` units along the polyline."""
        if not points:
            return []
        samples = [tuple(points[0])]
        for a, b in zip(points, points[1:]):
            ax, ay = a
            bx, by = b
            length = abs(bx - ax) + abs(by - ay)
            if length == 0:
                continue
            n = max(1, length // step)
            for i in range(1, n + 1):
                t = i / n
                samples.append((ax + (bx - ax) * t, ay + (by - ay) * t))
        return samples
