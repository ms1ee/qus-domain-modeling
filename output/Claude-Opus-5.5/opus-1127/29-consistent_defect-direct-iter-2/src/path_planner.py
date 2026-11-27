"""Grid based path planning along streets (grid lines every 100 units)."""

GRID = 100


class PathPlanner:
    """Street-preferring Manhattan path planner."""

    @staticmethod
    def next_axis(x, y, tx, ty):
        """Choose which axis to move along next, or None if arrived."""
        if x == tx and y == ty:
            return None
        # Special case: directly above/below target -> vertical only.
        if x == tx:
            return "y"
        if y == ty:
            return "x"
        # On a horizontal street -> move horizontally first.
        if y % GRID == 0:
            return "x"
        return "y"

    @classmethod
    def step(cls, x, y, tx, ty, budget):
        """Move from (x, y) toward (tx, ty) using up to ``budget`` units.

        Returns (new_x, new_y, remaining_budget).
        """
        while budget > 0:
            axis = cls.next_axis(x, y, tx, ty)
            if axis is None:
                break
            if axis == "x":
                d = tx - x
                mv = min(abs(d), budget)
                x += mv if d > 0 else -mv
            else:
                d = ty - y
                mv = min(abs(d), budget)
                y += mv if d > 0 else -mv
            budget -= mv
        return x, y, budget

    @classmethod
    def plan(cls, start, target):
        """Return list of waypoints (corners) from start to target."""
        x, y = start
        tx, ty = target
        points = [(x, y)]
        guard = 0
        while (x, y) != (tx, ty) and guard < 10:
            axis = cls.next_axis(x, y, tx, ty)
            if axis == "x":
                x = tx
            else:
                y = ty
            points.append((x, y))
            guard += 1
        return points

    @classmethod
    def plan_multi(cls, start, targets):
        """Plan a continuous route through multiple destinations."""
        route = [tuple(start)]
        cur = tuple(start)
        for t in targets:
            seg = cls.plan(cur, tuple(t))
            route.extend(seg[1:])
            cur = tuple(t)
        return route

    @staticmethod
    def route_length(points):
        """Manhattan length of a waypoint route."""
        total = 0
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            total += abs(x2 - x1) + abs(y2 - y1)
        return total
