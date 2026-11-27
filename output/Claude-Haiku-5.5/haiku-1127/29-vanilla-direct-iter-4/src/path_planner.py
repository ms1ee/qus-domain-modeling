"""Grid-based path planning and route stepping.

Geometry
--------
The map is 800x800 units, split into an 8x8 grid of 100x100 cells.

* Streets are the grid lines: points with ``x % 100 == 0`` or ``y % 100 == 0``.
* Locations (restaurants, customers and cell centres) are points with
  ``x % 100 == 50`` and ``y % 100 == 50``.

Planning
--------
Routes are searched on a lattice with 50-unit spacing. An edge between two
adjacent lattice points is usable when it lies on a street, or when one of its
endpoints is a location (a short access spur into a block). Location points may
only be entered as the final destination, so routes never cut through blocks.
A start point that is not on the lattice (for example a rider standing inside a
block) is connected to the lattice by a short axis-aligned leg; this is the
special case for off-road positions.

Every route consists of axis-aligned segments, so movement is always horizontal
or vertical. Riders do not block one another, so no deadlock can occur; path
conflicts are resolved by allowing riders to share road cells.
"""

import logging
from collections import deque

logger = logging.getLogger(__name__)

MAP_SIZE = 800
CELL_SIZE = 100
LATTICE_STEP = 50
_NEIGHBOR_OFFSETS = (
    (LATTICE_STEP, 0),
    (-LATTICE_STEP, 0),
    (0, LATTICE_STEP),
    (0, -LATTICE_STEP),
)


def is_street_point(x, y):
    """Return True when the point lies on a street (grid line).

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        True if ``x`` or ``y`` is a multiple of the cell size.
    """
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def is_location_point(x, y):
    """Return True when the point is a cell centre (restaurant/customer site).

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        True if both coordinates are cell centres.
    """
    half = CELL_SIZE // 2
    return x % CELL_SIZE == half and y % CELL_SIZE == half


class PathPlanner:
    """Compute street-following routes and advance riders along them."""

    def __init__(self, map_size=MAP_SIZE):
        """Create a planner.

        Args:
            map_size: Side length of the square map in units.
        """
        self.map_size = map_size

    def snap(self, point):
        """Snap a point to the nearest lattice point inside the map.

        Args:
            point: ``(x, y)`` tuple.

        Returns:
            Tuple of lattice coordinates (multiples of 50).
        """
        return (self._snap_value(point[0]), self._snap_value(point[1]))

    def _snap_value(self, value):
        """Snap one coordinate to the 50-unit lattice and clamp to the map."""
        snapped = ((int(value) + LATTICE_STEP // 2) // LATTICE_STEP) * LATTICE_STEP
        return min(max(snapped, 0), self.map_size)

    @staticmethod
    def _edge_usable(a, b):
        """Return True when the lattice edge a-b may be travelled.

        An edge is usable when it lies on a street or touches a location
        (access spur into a block).
        """
        if a[0] == b[0]:
            on_street = a[0] % CELL_SIZE == 0
        else:
            on_street = a[1] % CELL_SIZE == 0
        if on_street:
            return True
        return is_location_point(*a) or is_location_point(*b)

    def _lattice_path(self, start, goal):
        """Breadth-first search for the shortest usable lattice path.

        Args:
            start: Lattice start point.
            goal: Lattice goal point.

        Returns:
            List of lattice points from start to goal inclusive, or None if
            no path exists.
        """
        if start == goal:
            return [start]
        previous = {start: None}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            if node == goal:
                break
            if node != start and is_location_point(*node):
                continue
            for dx, dy in _NEIGHBOR_OFFSETS:
                neighbor = (node[0] + dx, node[1] + dy)
                if not (0 <= neighbor[0] <= self.map_size
                        and 0 <= neighbor[1] <= self.map_size):
                    continue
                if neighbor in previous:
                    continue
                if not self._edge_usable(node, neighbor):
                    continue
                if is_location_point(*neighbor) and neighbor != goal:
                    continue
                previous[neighbor] = node
                queue.append(neighbor)
        if goal not in previous:
            return None
        path = []
        node = goal
        while node is not None:
            path.append(node)
            node = previous[node]
        path.reverse()
        return path

    def plan(self, start, goal):
        """Plan an axis-aligned route from start to goal.

        The route is the list of waypoints to visit in order, excluding the
        start point and including the goal. Consecutive waypoints are always
        connected by horizontal or vertical segments.

        Args:
            start: ``(x, y)`` current position.
            goal: ``(x, y)`` destination.

        Returns:
            List of ``(x, y)`` waypoints. Empty if start equals goal.
        """
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        snapped_start = self.snap(start)
        snapped_goal = self.snap(goal)
        lattice = self._lattice_path(snapped_start, snapped_goal)
        if lattice is None:
            logger.warning("No lattice path from %s to %s; using direct legs.",
                           snapped_start, snapped_goal)
            lattice = [snapped_start, snapped_goal]

        route = []
        current = start
        for target in lattice + [goal]:
            if target == current:
                continue
            if current[0] != target[0] and current[1] != target[1]:
                # Off-lattice leg: turn once so that each segment is axis-aligned.
                route.append((target[0], current[1]))
            route.append(target)
            current = target
        return route

    @staticmethod
    def route_length(start, route):
        """Total Manhattan length of a route.

        Args:
            start: ``(x, y)`` route origin.
            route: List of waypoints as returned by :meth:`plan`.

        Returns:
            Sum of segment lengths in units.
        """
        total = 0
        current = start
        for point in route:
            total += abs(point[0] - current[0]) + abs(point[1] - current[1])
            current = point
        return total

    @staticmethod
    def step_along(position, route, speed):
        """Advance a position along a route by up to ``speed`` units.

        Args:
            position: ``(x, y)`` current position.
            route: List of remaining waypoints.
            speed: Maximum distance to travel this tick.

        Returns:
            Tuple ``(new_position, remaining_route)``.
        """
        x, y = position
        remaining = list(route)
        budget = int(speed)
        while budget > 0 and remaining:
            tx, ty = remaining[0]
            dist = abs(tx - x) + abs(ty - y)
            if dist <= budget:
                x, y = tx, ty
                budget -= dist
                remaining.pop(0)
            else:
                if tx != x:
                    step = min(budget, abs(tx - x))
                    x += step if tx > x else -step
                else:
                    step = min(budget, abs(ty - y))
                    y += step if ty > y else -step
                budget = 0
        return (x, y), remaining
