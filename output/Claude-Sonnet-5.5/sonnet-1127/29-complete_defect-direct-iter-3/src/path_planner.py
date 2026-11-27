"""Grid based path planning."""


class PathPlanner:
    """Plans street-preferring right-angle paths."""

    @staticmethod
    def nearest_street(v):
        """Nearest street line coordinate (multiple of 100)."""
        return min(800, max(0, int(round(v / 100.0)) * 100))

    @classmethod
    def plan(cls, start, end):
        """Return waypoint list from start to end (start excluded)."""
        sx, sy = start
        ex, ey = end
        pts = []
        cur = (sx, sy)
        on_street = sx % 100 == 0 or sy % 100 == 0
        if not on_street and (sx, sy) != (ex, ey):
            # rider is inside a cell: step to nearest horizontal street
            # (special case: directly above/below target handled the same way)
            sy2 = cls.nearest_street(sy)
            pts.append((sx, sy2))
            cur = (sx, sy2)
        if cur[0] != ex and cur[1] % 100 == 0:
            pts.append((ex, cur[1]))
            cur = (ex, cur[1])
        elif cur[0] != ex:
            pts.append((ex, cur[1]))
            cur = (ex, cur[1])
        if cur[1] != ey:
            pts.append((ex, ey))
        return pts

    @classmethod
    def full_route(cls, points):
        """Route through several consecutive destinations."""
        route = [points[0]]
        for a, b in zip(points, points[1:]):
            route.extend(cls.plan(a, b))
        return route

    @staticmethod
    def distance(a, b):
        """Manhattan distance."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
