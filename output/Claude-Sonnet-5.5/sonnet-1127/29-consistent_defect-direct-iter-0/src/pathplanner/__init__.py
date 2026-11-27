"""Path planning."""


class PathPlanner:
    """Grid path planner: horizontal first, then vertical."""

    def plan(self, start, points):
        """Return corner waypoints from start through points."""
        path = [tuple(start)]
        cur = tuple(start)
        for p in points:
            p = tuple(p)
            if cur[0] != p[0] and cur[1] != p[1]:
                path.append((p[0], cur[1]))
            if path[-1] != p:
                path.append(p)
            cur = p
        return path
