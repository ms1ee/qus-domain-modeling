"""Grid-based path planning."""

from config import CELL_SIZE


class PathPlanner:
    """Plans Manhattan (right-angle) paths on the grid map.

    Riders move only horizontally or vertically. Paths prefer streets: if a
    rider stands on a vertical street (x is a multiple of 100) it moves
    vertically first, otherwise it moves horizontally first. When the rider
    is directly above/below (or level with) the target a straight path is
    used (the special case). Riders never block each other, so there are no
    path conflicts or deadlocks.
    """

    @staticmethod
    def is_street(x, y):
        """Return True if (x, y) lies on a street grid line."""
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    @staticmethod
    def is_special_case(start, target):
        """Rider directly above or below the target (same x, different y)."""
        return start[0] == target[0] and start[1] != target[1]

    @staticmethod
    def plan(start, target):
        """Return a list of waypoints from ``start`` to ``target``.

        The start point is not included; the last waypoint is the target.
        """
        sx, sy = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        if (sx, sy) == (tx, ty):
            return []
        if sx == tx or sy == ty:
            return [(tx, ty)]
        if sx % CELL_SIZE == 0 and sy % CELL_SIZE != 0:
            corner = (sx, ty)
        else:
            corner = (tx, sy)
        return [corner, (tx, ty)]

    @staticmethod
    def route(start, stops):
        """Plan a continuous route through several stops.

        Returns the list of points including ``start``.
        """
        points = [(int(start[0]), int(start[1]))]
        cur = points[0]
        for stop in stops:
            for wp in PathPlanner.plan(cur, stop):
                points.append(wp)
            cur = (int(stop[0]), int(stop[1]))
        return points

    @staticmethod
    def path_length(points):
        """Total Manhattan length of a polyline."""
        total = 0
        for a, b in zip(points, points[1:]):
            total += abs(a[0] - b[0]) + abs(a[1] - b[1])
        return total

    @staticmethod
    def step(pos, waypoints, budget):
        """Advance along ``waypoints`` using at most ``budget`` units.

        Returns ``(new_pos, remaining_waypoints, used)``.
        """
        x, y = int(pos[0]), int(pos[1])
        wps = list(waypoints)
        used = 0
        budget = int(budget)
        while wps and used < budget:
            tx, ty = wps[0]
            if (x, y) == (tx, ty):
                wps.pop(0)
                continue
            rem = budget - used
            if x != tx:
                d = min(rem, abs(tx - x))
                x += d if tx > x else -d
                used += d
            else:
                d = min(rem, abs(ty - y))
                y += d if ty > y else -d
                used += d
        while wps and (x, y) == tuple(wps[0]):
            wps.pop(0)
        return (x, y), wps, used
