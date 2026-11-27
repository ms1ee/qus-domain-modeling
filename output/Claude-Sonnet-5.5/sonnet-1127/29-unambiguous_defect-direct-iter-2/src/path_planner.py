"""Grid path planning."""


class PathPlanner:
    """Manhattan pathfinding on the grid."""

    @staticmethod
    def step(pos, target, speed):
        """Move up to `speed` units: horizontal first, then vertical."""
        x, y = pos
        tx, ty = target
        budget = speed
        dx = max(-budget, min(budget, tx - x))
        x += dx
        budget -= abs(dx)
        dy = max(-budget, min(budget, ty - y))
        y += dy
        return (x, y)

    @staticmethod
    def route(start, via, end):
        """Corner-point route start -> via -> end."""
        pts = [tuple(start)]
        for p in (via, end):
            c = pts[-1]
            if c[0] != p[0] and c[1] != p[1]:
                pts.append((p[0], c[1]))
            if pts[-1] != tuple(p):
                pts.append(tuple(p))
        return pts
