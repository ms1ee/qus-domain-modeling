"""Grid-based path planning for the 800x800 street map.

The map is divided into 100x100 unit cells. Streets run along the grid
lines (x or y is a multiple of 100). Restaurants, customers and street
intersections are the points where both coordinates are multiples of 100.
Paths are computed over the intersection graph with Dijkstra's algorithm,
penalising right-angle turns so that straight runs are preferred.
"""

import heapq
import itertools
import logging
import math

MAP_SIZE = 800
CELL_SIZE = 100
GRID_NODES = MAP_SIZE // CELL_SIZE + 1  # 9 intersections per axis
STEP_COST = CELL_SIZE                    # cost of moving one block
TURN_PENALTY = 10                        # extra cost for a right-angle turn
DIRECTIONS = ((CELL_SIZE, 0), (-CELL_SIZE, 0), (0, CELL_SIZE), (0, -CELL_SIZE))

logger = logging.getLogger("dispatch.path")


def snap_to_cell(x, y):
    """Snap a point to the top-left corner of the grid cell containing it.

    Args:
        x: X coordinate (0-800).
        y: Y coordinate (0-800).

    Returns:
        Tuple ``(cell_x, cell_y)`` with both values multiples of 100.
    """
    return (int(x) // CELL_SIZE * CELL_SIZE, int(y) // CELL_SIZE * CELL_SIZE)


def is_intersection(x, y):
    """Return True if the point lies on a street intersection."""
    return x % CELL_SIZE == 0 and y % CELL_SIZE == 0


def is_on_street(x, y):
    """Return True if the point lies on any street (grid line)."""
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def in_bounds(x, y):
    """Return True if the point lies inside the 800x800 map."""
    return 0 <= x <= MAP_SIZE and 0 <= y <= MAP_SIZE


def manhattan(a, b):
    """Return the Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def euclidean(a, b):
    """Return the Euclidean distance between two points."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def route_length(points):
    """Return the total travelled distance along a list of points."""
    return sum(manhattan(points[i], points[i + 1]) for i in range(len(points) - 1))


class PathPlanner:
    """Plans axis-aligned routes along streets between two points."""

    def entry_nodes(self, x, y):
        """Return the intersections a point can leave from, with costs.

        A point on an intersection returns itself with cost 0. A point in
        the middle of a block returns the two surrounding intersections,
        with the distance needed to reach each one.

        Args:
            x: X coordinate of the start point.
            y: Y coordinate of the start point.

        Returns:
            List of ``((node_x, node_y), cost)`` tuples.

        Raises:
            ValueError: If the point is not on a street.
        """
        if is_intersection(x, y):
            return [((x, y), 0)]
        if not is_on_street(x, y):
            raise ValueError(f"Point ({x}, {y}) is not on a street")
        base_x = x - x % CELL_SIZE
        base_y = y - y % CELL_SIZE
        if y % CELL_SIZE == 0:
            candidates = [
                ((base_x, y), x - base_x),
                ((base_x + CELL_SIZE, y), base_x + CELL_SIZE - x),
            ]
        else:
            candidates = [
                ((x, base_y), y - base_y),
                ((x, base_y + CELL_SIZE), base_y + CELL_SIZE - y),
            ]
        return [(node, cost) for node, cost in candidates if in_bounds(*node)]

    def plan(self, start, goal):
        """Compute the waypoints from ``start`` to ``goal`` along streets.

        Args:
            start: ``(x, y)`` current position of the rider.
            goal: ``(x, y)`` destination intersection.

        Returns:
            List of waypoints (intersections) ending at ``goal``. The start
            point itself is not included. An empty list means no movement.

        Raises:
            ValueError: If the goal is not an intersection or no route exists.
        """
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return []
        if not is_intersection(*goal):
            raise ValueError(f"Goal {goal} is not a street intersection")

        entries = self.entry_nodes(*start)
        if not entries:
            raise ValueError(f"No street access from {start}")
        for node, _ in entries:
            if node == goal:
                return [goal]

        best = {}
        parent = {}
        heap = []
        counter = itertools.count()
        for node, cost in entries:
            state = (node, None)
            best[state] = cost
            parent[state] = None
            heapq.heappush(heap, (cost, next(counter), state))

        found = None
        while heap:
            cost, _, state = heapq.heappop(heap)
            if cost > best.get(state, math.inf):
                continue
            node, direction = state
            if node == goal:
                found = state
                break
            for step in DIRECTIONS:
                nxt = (node[0] + step[0], node[1] + step[1])
                if not in_bounds(*nxt):
                    continue
                new_cost = cost + STEP_COST
                if direction is not None and step != direction:
                    new_cost += TURN_PENALTY
                next_state = (nxt, step)
                if new_cost < best.get(next_state, math.inf):
                    best[next_state] = new_cost
                    parent[next_state] = state
                    heapq.heappush(heap, (new_cost, next(counter), next_state))

        if found is None:
            raise ValueError(f"No route from {start} to {goal}")

        nodes = []
        state = found
        while state is not None:
            nodes.append(state[0])
            state = parent[state]
        nodes.reverse()
        if nodes and nodes[0] == start:
            nodes = nodes[1:]
        logger.debug("Planned route %s -> %s with %d waypoints", start, goal, len(nodes))
        return nodes
