"""Grid-based path planning for riders.

Routes follow the streets of the 8x8 grid: a rider always moves along one
axis at a time, preferring horizontal movement first at a right-angle turn.
A simple priority rule prevents deadlocks between riders that want to occupy
the same position.
"""

import grid

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2


class PathPlanner:
    """Compute street-following routes and resolve movement conflicts."""

    def plan(self, start, goal):
        """Plan a route from ``start`` to ``goal``.

        If the two points share an x or y coordinate (the target is directly
        above, below, left or right), a straight single-segment route is
        returned. Otherwise the route makes exactly one right-angle turn.

        Args:
            start: Current point ``(x, y)``.
            goal: Destination point ``(x, y)``.

        Returns:
            list[tuple[int, int]]: Waypoints after ``start`` ending at
            ``goal``. Empty if already at the goal.
        """
        sx, sy = start
        gx, gy = goal
        if (sx, sy) == (gx, gy):
            return []
        if sx == gx or sy == gy:
            return [(gx, gy)]
        corner = (gx, sy)
        return [corner, (gx, gy)]

    def plan_route(self, start, stops):
        """Plan a continuous multi-destination route.

        Args:
            start: Starting point ``(x, y)``.
            stops: Ordered destinations, e.g. ``[restaurant, customer]``.

        Returns:
            list[tuple[int, int]]: Concatenated waypoints after ``start``.
        """
        points = []
        current = start
        for stop in stops:
            leg = self.plan(current, stop)
            points.extend(leg)
            current = stop
        return points

    def route_length(self, start, points):
        """Return the total length of a route in units."""
        return grid.path_length(start, points)

    @staticmethod
    def step(x, y, target, budget):
        """Move one axis-aligned step toward ``target``.

        Movement is performed along the first axis that still differs from
        the target, limited by ``budget``.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            target: Target waypoint ``(x, y)``.
            budget: Maximum units that may be moved this tick.

        Returns:
            tuple[int, int, int]: New ``(x, y)`` and the distance moved.
        """
        tx, ty = target
        if x != tx:
            delta = tx - x
            moved = min(budget, abs(delta))
            return (x + moved if delta > 0 else x - moved), y, moved
        if y != ty:
            delta = ty - y
            moved = min(budget, abs(delta))
            return x, (y + moved if delta > 0 else y - moved), moved
        return x, y, 0

    @staticmethod
    def is_blocked(mover, next_pos, riders):
        """Decide whether ``mover`` must yield before entering ``next_pos``.

        A rider yields only to a lower-id rider that is currently in motion
        and occupies the target position. Because waiting is only ever done
        toward strictly lower ids, no cycle of waiting riders can form, which
        rules out deadlock.

        Args:
            mover: The rider that wants to move.
            next_pos: Position ``(x, y)`` the mover would enter.
            riders: Iterable of all riders.

        Returns:
            bool: True if the mover must wait this tick.
        """
        target = (next_pos[0], next_pos[1])
        for other in riders:
            if other is mover:
                continue
            if other.rider_id >= mover.rider_id:
                continue
            if other.state == STATE_IDLE:
                continue
            if (other.x, other.y) == target:
                return True
        return False
