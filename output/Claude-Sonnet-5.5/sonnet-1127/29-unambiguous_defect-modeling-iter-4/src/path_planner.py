"""Path planning on the grid."""


class PathPlanner:
    """Manhattan (street-following) path planner."""

    @staticmethod
    def plan(start, targets):
        """Return waypoint list from start through targets (x first, then y)."""
        pts = [tuple(start)]
        cur = tuple(start)
        for t in targets:
            t = tuple(t)
            if cur[0] != t[0]:
                pts.append((t[0], cur[1]))
            if cur[1] != t[1]:
                pts.append(t)
            cur = t
        return pts
