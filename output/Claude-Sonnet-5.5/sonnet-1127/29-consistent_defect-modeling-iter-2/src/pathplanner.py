"""Grid based path planning."""

CELL = 100
MAX_COORD = 800


class PathPlanner:
    """Plans right-angle paths along streets."""

    @staticmethod
    def next_position(x, y, tx, ty, speed):
        """Move up to `speed` units from (x, y) toward (tx, ty).

        Moves horizontally first, then vertically (right-angle turns).
        """
        budget = speed
        if x != tx:
            step = min(budget, abs(tx - x))
            x += step if tx > x else -step
            budget -= step
        if budget > 0 and y != ty:
            step = min(budget, abs(ty - y))
            y += step if ty > y else -step
        return x, y

    @staticmethod
    def plan_route(points):
        """Return waypoints connecting a list of points with right angles."""
        route = []
        for i, p in enumerate(points):
            if i == 0:
                route.append(p)
                continue
            prev = route[-1]
            if prev[0] != p[0] and prev[1] != p[1]:
                route.append((p[0], prev[1]))
            route.append(p)
        return route

    @staticmethod
    def route_length(points):
        """Manhattan length of a route through points."""
        return sum(abs(a[0] - b[0]) + abs(a[1] - b[1])
                   for a, b in zip(points, points[1:]))
