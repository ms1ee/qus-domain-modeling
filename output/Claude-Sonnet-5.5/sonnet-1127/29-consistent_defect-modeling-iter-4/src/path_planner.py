"""Grid path planning."""


class PathPlanner:
    """Street-following planner with right-angle turns."""

    def plan(self, start, end):
        """Waypoints from start to end: horizontal then vertical."""
        pts = [tuple(start)]
        corner = (end[0], start[1])
        if corner != pts[-1] and corner != tuple(end):
            pts.append(corner)
        if tuple(end) != pts[-1]:
            pts.append(tuple(end))
        return pts

    def plan_multi(self, start, destinations):
        """Continuous path through several destinations."""
        path = [tuple(start)]
        cur = tuple(start)
        for d in destinations:
            path.extend(self.plan(cur, d)[1:])
            cur = tuple(d)
        return path
