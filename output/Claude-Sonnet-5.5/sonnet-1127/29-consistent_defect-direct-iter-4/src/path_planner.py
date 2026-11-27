"""Grid path planning."""


class PathPlanner:
    """Right-angle path planner (horizontal first, then vertical)."""

    @staticmethod
    def plan(start, end):
        """Return corner points from start to end."""
        pts = [tuple(start)]
        corner = (end[0], start[1])
        if corner != pts[-1] and corner != tuple(end):
            pts.append(corner)
        if tuple(end) != pts[-1]:
            pts.append(tuple(end))
        return pts

    @classmethod
    def plan_multi(cls, points):
        """Continuous path through several destinations."""
        path = [tuple(points[0])]
        for a, b in zip(points, points[1:]):
            path.extend(cls.plan(a, b)[1:])
        return path

    @staticmethod
    def length(path):
        return sum(abs(a[0] - b[0]) + abs(a[1] - b[1])
                   for a, b in zip(path, path[1:]))
