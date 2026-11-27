"""Grid based path planning (prefers moving along streets)."""

from gridmap import GRID


class PathPlanner:
    """Plans axis-aligned waypoint paths on the grid."""

    def __init__(self, grid=GRID):
        self.grid = grid

    def plan(self, start, end):
        """Return list of axis-aligned waypoints from start to end."""
        x, y = start
        ex, ey = end
        cs = self.grid.cell_size
        pts = []
        if x % cs != 0 and x != ex:
            # Off-street: first reach the nearest vertical street.
            nx = int(round(x / float(cs))) * cs
            nx = min(max(nx, 0), self.grid.width)
            pts.append((nx, y))
            x = nx
        pts.append((x, ey))
        pts.append((ex, ey))
        out = []
        cur = start
        for p in pts:
            if p != cur:
                out.append(p)
                cur = p
        return out

    def plan_multi(self, start, stops):
        """Plan a continuous path through several destinations."""
        path = []
        cur = start
        for s in stops:
            path.extend(self.plan(cur, s))
            cur = s
        return path
