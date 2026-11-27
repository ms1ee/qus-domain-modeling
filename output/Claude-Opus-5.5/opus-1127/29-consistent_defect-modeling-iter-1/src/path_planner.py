"""Grid based path planning."""

from grid_map import CELL_SIZE


class Path:
    """A planned path consisting of axis-aligned waypoints."""

    def __init__(self, waypoints):
        self.waypoints = list(waypoints)
        self.length = sum(
            abs(b[0] - a[0]) + abs(b[1] - a[1])
            for a, b in zip(self.waypoints, self.waypoints[1:]))

    def __repr__(self):
        return "Path(%r, length=%d)" % (self.waypoints, self.length)


class PathPlanner:
    """Plans street-following routes (right angle turns only)."""

    def __init__(self, cell_size=CELL_SIZE):
        self.cell_size = cell_size

    def plan(self, start, end):
        """Return a :class:`Path` from ``start`` to ``end``.

        Strategy:
        * same point -> single waypoint;
        * straight line (incl. rider directly above/below target) -> direct;
        * otherwise move along a street: horizontal first if the current
          row is a street, vertical first if only the column is a street,
          and if on neither, snap vertically to the nearest street first.
        """
        sx, sy = int(start[0]), int(start[1])
        ex, ey = int(end[0]), int(end[1])
        if (sx, sy) == (ex, ey):
            return Path([(sx, sy)])
        if sx == ex or sy == ey:
            return Path([(sx, sy), (ex, ey)])
        c = self.cell_size
        on_h_street = sy % c == 0
        on_v_street = sx % c == 0
        if on_h_street:
            points = [(sx, sy), (ex, sy), (ex, ey)]
        elif on_v_street:
            points = [(sx, sy), (sx, ey), (ex, ey)]
        else:
            low = (sy // c) * c
            high = low + c
            snap = low if abs(low - ey) <= abs(high - ey) else high
            points = [(sx, sy), (sx, snap), (ex, snap), (ex, ey)]
        cleaned = []
        for p in points:
            if not cleaned or cleaned[-1] != p:
                cleaned.append(p)
        return Path(cleaned)

    def plan_multi(self, start, stops):
        """Plan a continuous path visiting ``stops`` in order."""
        waypoints = [tuple(start)]
        current = tuple(start)
        for stop in stops:
            segment = self.plan(current, stop).waypoints
            for p in segment[1:]:
                if waypoints[-1] != p:
                    waypoints.append(p)
            current = tuple(stop)
        return Path(waypoints)
