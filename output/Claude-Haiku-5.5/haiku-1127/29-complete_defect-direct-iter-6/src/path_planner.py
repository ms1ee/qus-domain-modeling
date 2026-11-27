"""Grid-based path planning for riders.

Routes run along streets: every step moves one grid cell horizontally or
vertically, so the rider always stays on a street line through cell centers.
"""

import logging

from geometry import cell_to_point, sign, to_cell

logger = logging.getLogger("dispatch.path")


class PathPlanner:
    """Plans right-angle, street-following routes on the 8x8 grid."""

    def plan(self, start, goal, occupied=None):
        """Plan a route between two cell-center points.

        Straight-line moves (target directly above/below or beside the start)
        are handled naturally: the route collapses onto a single street.
        For diagonal targets an L-shaped route is chosen, preferring the
        corner that is not occupied by a stationary rider (conflict
        avoidance).

        Args:
            start: ``(x, y)`` cell center where the route begins.
            goal: ``(x, y)`` cell center where the route ends.
            occupied: Optional set of ``(col, row)`` cells held by riders.

        Returns:
            List of cell-center points after ``start`` up to and including
            ``goal``. Empty when start equals goal.
        """
        if start == goal:
            return []
        occupied = occupied or set()
        sc, sr = to_cell(start)
        gc, gr = to_cell(goal)
        horizontal_first = True
        if sc != gc and sr != gr:
            horizontal_corner = (gc, sr)
            vertical_corner = (sc, gr)
            if horizontal_corner in occupied and vertical_corner not in occupied:
                horizontal_first = False
        cells = self._walk(sc, sr, gc, gr, horizontal_first)
        return [cell_to_point(c, r) for c, r in cells]

    def plan_route(self, start, stops, occupied=None):
        """Plan a continuous multi-destination route.

        Args:
            start: ``(x, y)`` starting cell center.
            stops: Ordered list of ``(x, y)`` cell centers to visit.
            occupied: Optional set of occupied ``(col, row)`` cells.

        Returns:
            Concatenated list of waypoints covering every stop in order.
        """
        route = []
        current = start
        for stop in stops:
            route.extend(self.plan(current, stop, occupied))
            current = stop
        return route

    @staticmethod
    def occupied_cells(riders, exclude=None):
        """Return cells currently held by stationary riders.

        Args:
            riders: Iterable of Rider objects.
            exclude: Rider to ignore (usually the one planning).

        Returns:
            Set of ``(col, row)`` tuples.
        """
        cells = set()
        for rider in riders:
            if rider is exclude or rider.route:
                continue
            cells.add(to_cell(rider.position))
        return cells

    @staticmethod
    def is_blocked(target, rider, riders):
        """Return True if a stationary rider other than ``rider`` sits on ``target``."""
        for other in riders:
            if other is rider:
                continue
            if other.position == target and not other.route:
                return True
        return False

    @staticmethod
    def _walk(c0, r0, c1, r1, horizontal_first):
        """Return the cells visited walking from (c0, r0) to (c1, r1)."""
        cells = []
        c, r = c0, r0
        while (c, r) != (c1, r1):
            if horizontal_first:
                if c != c1:
                    c += sign(c1 - c)
                else:
                    r += sign(r1 - r)
            else:
                if r != r1:
                    r += sign(r1 - r)
                else:
                    c += sign(c1 - c)
            cells.append((c, r))
        return cells
