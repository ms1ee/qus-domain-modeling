"""Path planning."""


class PathPlanner:
    """Grid-based planner: horizontal first, then vertical."""

    @staticmethod
    def next_step(pos, target, speed):
        """Return new position moving up to speed units toward target."""
        x, y = pos
        tx, ty = target
        budget = speed
        if x != tx:
            d = min(budget, abs(tx - x))
            x += d if tx > x else -d
            budget -= d
        if budget > 0 and y != ty:
            d = min(budget, abs(ty - y))
            y += d if ty > y else -d
        return x, y

    @staticmethod
    def route(start, *points):
        """Return list of corner points through destinations."""
        path = [tuple(start)]
        cur = tuple(start)
        for p in points:
            if cur[0] != p[0] and cur[1] != p[1]:
                path.append((p[0], cur[1]))
            if cur != tuple(p):
                path.append(tuple(p))
            cur = tuple(p)
        return path
