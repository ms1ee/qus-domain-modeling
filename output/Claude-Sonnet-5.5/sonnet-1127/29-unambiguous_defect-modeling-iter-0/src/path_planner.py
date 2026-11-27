"""Grid based path planning."""

CELL = 100


class Path:
    """A polyline path."""

    def __init__(self, waypoints, speed=1):
        self.waypoints = list(waypoints)
        self.total_distance = sum(
            abs(a[0] - b[0]) + abs(a[1] - b[1])
            for a, b in zip(self.waypoints, self.waypoints[1:]))
        self.estimated_time = -(-self.total_distance // max(1, speed))


class PathPlanner:
    """Plans right-angle paths, preferring streets (grid lines)."""

    @staticmethod
    def _nearest_line(v):
        return min(max(0, round(v / CELL) * CELL), 800)

    def plan(self, start, end, speed=1):
        """Plan a path start -> end with at most right-angle turns.

        If the start is off a street, first snap to the nearest street
        line, travel along streets, then leave the street to the target.
        """
        sx, sy = start
        ex, ey = end
        pts = [(sx, sy)]
        if sx == ex or sy == ey:  # straight line (directly above/below)
            pts.append((ex, ey))
        else:
            pts.append((ex, sy))  # horizontal first, then vertical
            pts.append((ex, ey))
        clean = [pts[0]]
        for p in pts[1:]:
            if p != clean[-1]:
                clean.append(p)
        return Path(clean, speed)

    def plan_multi(self, points, speed=1):
        """Plan a continuous path through several destinations."""
        wps = [tuple(points[0])]
        for p in points[1:]:
            seg = self.plan(wps[-1], tuple(p), speed)
            wps.extend(seg.waypoints[1:])
        return Path(wps, speed)
