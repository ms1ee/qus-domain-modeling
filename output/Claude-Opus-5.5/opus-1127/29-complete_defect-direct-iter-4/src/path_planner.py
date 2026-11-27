"""Grid based path planning.

The map is 800x800 units divided into 8x8 cells of 100x100 units.  Streets
are the grid lines (x or y is a multiple of 100).  Riders move along streets
using right-angle turns, and only leave a street for the final short hop
into the destination cell (cell centres are at 50-unit offsets).
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class PathPlanner:
    """Grid-based path planning helpers (all static)."""

    @staticmethod
    def to_grid_index(v):
        """Convert a raw coordinate (0-800) to a grid index (0-7)."""
        v = _clamp(int(v), 0, MAP_SIZE - 1)
        return v // CELL_SIZE

    @staticmethod
    def to_grid_center(v):
        """Convert a raw coordinate to the centre of its grid cell.

        ``center = (v // 100) * 100 + 50``; the boundary value 800 is mapped
        into the last cell (750).
        """
        return PathPlanner.to_grid_index(v) * CELL_SIZE + CELL_SIZE // 2

    @staticmethod
    def to_center_pos(pos):
        """Convert an (x, y) pair to its grid cell centre."""
        return (PathPlanner.to_grid_center(pos[0]),
                PathPlanner.to_grid_center(pos[1]))

    @staticmethod
    def is_on_street(x, y):
        """Return True if (x, y) lies on a street (grid line)."""
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    @staticmethod
    def is_special(start, target):
        """Return True when the rider is directly above/below the target
        while not standing on a vertical street (requires a detour)."""
        x, y = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        return x == tx and y != ty and x % CELL_SIZE != 0

    @staticmethod
    def _nearest_street(v, toward):
        """Return the street line nearest to ``v`` in the direction of
        ``toward`` (v itself if already on a street line)."""
        if v % CELL_SIZE == 0:
            return v
        lower = (v // CELL_SIZE) * CELL_SIZE
        upper = lower + CELL_SIZE
        s = upper if toward > v else lower
        return _clamp(s, 0, MAP_SIZE)

    @staticmethod
    def _clean(points):
        """Remove consecutive duplicates and collinear middle points."""
        out = []
        for p in points:
            if not out or out[-1] != p:
                out.append(p)
        changed = True
        while changed and len(out) > 2:
            changed = False
            for i in range(1, len(out) - 1):
                a, b, c = out[i - 1], out[i], out[i + 1]
                if (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1]):
                    # Only remove if b lies between a and c (no reversal)
                    if (min(a[0], c[0]) <= b[0] <= max(a[0], c[0]) and
                            min(a[1], c[1]) <= b[1] <= max(a[1], c[1])):
                        del out[i]
                        changed = True
                        break
        return out

    @staticmethod
    def plan(start, target):
        """Plan a street-following path.

        Returns a list of waypoints (tuples) starting with ``start`` and
        ending with ``target``; every segment is axis aligned.
        """
        x, y = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        pts = [(x, y)]
        if (x, y) == (tx, ty):
            return pts

        # Step onto the nearest street (vertical move) if inside a cell.
        if not PathPlanner.is_on_street(x, y):
            y = PathPlanner._nearest_street(y, ty)
            pts.append((x, y))

        # Horizontal street used to approach the target.
        if ty % CELL_SIZE == 0:
            ey = ty
        else:
            ey = PathPlanner._nearest_street(ty, y)

        if y == ey:
            pts.append((tx, ey))
        else:
            if x % CELL_SIZE == 0:
                vx = x
            elif tx % CELL_SIZE == 0:
                vx = tx
            else:
                lower = (tx // CELL_SIZE) * CELL_SIZE
                upper = min(lower + CELL_SIZE, MAP_SIZE)
                vx = min((lower, upper),
                         key=lambda c: (abs(x - c) + abs(c - tx), c))
            pts.append((vx, y))
            pts.append((vx, ey))
            pts.append((tx, ey))
        pts.append((tx, ty))
        return PathPlanner._clean(pts)

    @staticmethod
    def plan_multi(start, targets):
        """Plan a continuous path through several destinations."""
        path = [(int(start[0]), int(start[1]))]
        cur = path[0]
        for t in targets:
            seg = PathPlanner.plan(cur, t)
            path.extend(seg[1:])
            cur = (int(t[0]), int(t[1]))
        return PathPlanner._clean(path)

    @staticmethod
    def path_length(points):
        """Return the Manhattan length of a waypoint path."""
        total = 0
        for a, b in zip(points, points[1:]):
            total += abs(a[0] - b[0]) + abs(a[1] - b[1])
        return total

    @staticmethod
    def distance(a, b):
        """Street distance between two points (length of planned path)."""
        return PathPlanner.path_length(PathPlanner.plan(a, b))
