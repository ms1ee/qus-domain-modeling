"""Path planning on the grid."""


class PathPlanner:
    """Right-angle, street-preferring path planner."""

    def plan(self, start, end):
        """Return waypoint list (excluding start) from start to end."""
        sx, sy = start
        ex, ey = end
        if (sx, sy) == (ex, ey):
            return []
        if sx == ex or sy == ey:
            return [(ex, ey)]
        # Prefer to stay on a street: if on a horizontal street move
        # horizontally first; otherwise vertical first (vertical street
        # or directly above/below special case).
        if sy % 100 == 0:
            return [(ex, sy), (ex, ey)]
        return [(sx, ey), (ex, ey)]

    def plan_multi(self, start, points):
        """Continuous path through several destinations."""
        path = []
        cur = start
        for p in points:
            path.extend(self.plan(cur, p))
            cur = p
        return path

    @staticmethod
    def length(start, path):
        total = 0
        cur = start
        for p in path:
            total += abs(p[0] - cur[0]) + abs(p[1] - cur[1])
            cur = p
        return total

    def step(self, pos, target, dist):
        """Move up to dist units from pos toward target along the path."""
        path = self.plan(pos, target)
        x, y = pos
        remaining = dist
        for wx, wy in path:
            d = abs(wx - x) + abs(wy - y)
            if d <= remaining:
                remaining -= d
                x, y = wx, wy
            else:
                if wx != x:
                    x += remaining if wx > x else -remaining
                else:
                    y += remaining if wy > y else -remaining
                remaining = 0
            if remaining == 0:
                break
        return x, y
