"""Grid based path planning.

Coordinate system: an 800x800 map split in 8x8 cells of 100x100 units.
Streets run along every line where ``x`` or ``y`` is a multiple of 100.
Restaurants and customers sit at cell centers (``x % 100 == 50`` and
``y % 100 == 50``).  Riders travel along streets and only leave them for the
final hop into a cell center (and the first hop back out of it).
"""

from config import CELL_SIZE, MAP_SIZE


def to_grid_center(value):
    """Convert a raw coordinate (0-800) to the center of its grid cell.

    ``center = (v // 100) * 100 + 50``; out of range values are clamped so
    that 800 maps to 750 and negative values map to 50.
    """
    v = int(value)
    v = max(0, min(MAP_SIZE - 1, v))
    return (v // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2


def to_grid_point(pos):
    """Convert an ``(x, y)`` pair to the corresponding cell center."""
    return (to_grid_center(pos[0]), to_grid_center(pos[1]))


def on_street(x, y):
    """Return True if the point lies on a street."""
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def manhattan(a, b):
    """Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class PathPlanner:
    """Computes street-following, right-angled paths on the grid."""

    def __init__(self):
        self.last_special = False

    @staticmethod
    def _choose_line(a, b):
        """Choose a street line (multiple of 100) near ``a`` towards ``b``."""
        low = (int(a) // CELL_SIZE) * CELL_SIZE
        high = low + CELL_SIZE
        candidates = [c for c in (low, high) if 0 <= c <= MAP_SIZE]
        return min(candidates, key=lambda c: (abs(a - c) + abs(c - b), c))

    def street_route(self, a, b):
        """Route between two street points; returns waypoints (excl. ``a``)."""
        ax, ay = a
        bx, by = b
        if (ax, ay) == (bx, by):
            return []
        a_h = ay % CELL_SIZE == 0
        a_v = ax % CELL_SIZE == 0
        b_h = by % CELL_SIZE == 0
        b_v = bx % CELL_SIZE == 0
        if a_h and b_h and ay == by:
            return [(bx, by)]
        if a_v and b_v and ax == bx:
            return [(bx, by)]
        if a_v and b_h:
            return [(ax, by), (bx, by)]
        if a_h and b_v:
            return [(bx, ay), (bx, by)]
        if a_h and b_h:
            vx = self._choose_line(ax, bx)
            return [(vx, ay), (vx, by), (bx, by)]
        # both on vertical streets with different x
        hy = self._choose_line(ay, by)
        return [(ax, hy), (bx, hy), (bx, by)]

    def plan(self, start, target):
        """Plan a path from ``start`` to ``target``.

        Returns the list of waypoints (excluding ``start``) ending at
        ``target``.  Sets ``self.last_special`` when the special case
        "rider directly above/below the target" was handled.
        """
        x, y = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        self.last_special = False
        if (x, y) == (tx, ty):
            return []
        raw = []
        # Special case: start off-street inside the target's own cell.
        if (not on_street(x, y) and x // CELL_SIZE == tx // CELL_SIZE
                and y // CELL_SIZE == ty // CELL_SIZE):
            raw = [(tx, y), (tx, ty)]
            return self._dedupe((x, y), raw)
        # Step 1: leave an off-street position onto a horizontal street.
        if not on_street(x, y):
            if ty > y:
                ny = (y // CELL_SIZE + 1) * CELL_SIZE
            else:
                ny = (y // CELL_SIZE) * CELL_SIZE
            raw.append((x, ny))
            y = ny
        # Step 2: compute the entrance point of the target cell.
        if on_street(tx, ty):
            entrance = (tx, ty)
        else:
            below = (ty // CELL_SIZE) * CELL_SIZE
            above = below + CELL_SIZE
            ey = below if abs(y - below) <= abs(y - above) else above
            entrance = (tx, ey)
        # Special case: directly above / below the target on a non-street
        # column; the rider must side-step to a vertical street.
        if x == tx and x % CELL_SIZE != 0 and y != entrance[1]:
            self.last_special = True
        raw.extend(self.street_route((x, y), entrance))
        if entrance != (tx, ty):
            raw.append((tx, ty))
        return self._dedupe((int(start[0]), int(start[1])), raw)

    def plan_multi(self, start, destinations):
        """Plan a continuous path through several destinations in order."""
        path = []
        current = (int(start[0]), int(start[1]))
        special = False
        for dest in destinations:
            seg = self.plan(current, dest)
            special = special or self.last_special
            path.extend(seg)
            current = (int(dest[0]), int(dest[1]))
        self.last_special = special
        return path

    @staticmethod
    def _dedupe(start, points):
        """Remove consecutive duplicate points (and points equal to start)."""
        result = []
        prev = start
        for p in points:
            if p != prev:
                result.append(p)
                prev = p
        return result

    @staticmethod
    def path_length(start, path):
        """Total length of a path starting at ``start``."""
        total = 0
        prev = start
        for p in path:
            total += manhattan(prev, p)
            prev = p
        return total
