"""Grid-based path planning on the street network.

The map is an 800x800 unit area divided into 8x8 cells of 100x100 units.
Streets lie on the lines x % 100 == 0 or y % 100 == 0. Restaurants and
customers are located on street intersections (both coordinates multiples
of 100), which form a 9x9 lattice of nodes. Movement between adjacent lattice
nodes is always axis-aligned and therefore always stays on a street.
"""

import heapq
import itertools
import math

from config import CELL_SIZE, GRID_SIZE

HALF_CELL = CELL_SIZE // 2

LATTICE_NODES = [
    (x, y)
    for y in range(0, GRID_SIZE + 1, CELL_SIZE)
    for x in range(0, GRID_SIZE + 1, CELL_SIZE)
]

DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1))

STEP_COST = 10
TURN_COST = 5


def to_lattice_value(value):
    """Convert a raw coordinate to the nearest street intersection value.

    The value is clamped to the map range 0-800 and rounded to the nearest
    multiple of 100.

    Args:
        value: Integer-like coordinate.

    Returns:
        int: Snapped coordinate value.
    """
    number = int(value)
    number = max(0, min(GRID_SIZE, number))
    return ((number + HALF_CELL) // CELL_SIZE) * CELL_SIZE


def to_lattice_point(point):
    """Snap an ``(x, y)`` point to the nearest street intersection.

    Args:
        point: Sequence of two coordinates.

    Returns:
        tuple: ``(x, y)`` with both values on the intersection lattice.
    """
    x, y = point
    return (to_lattice_value(x), to_lattice_value(y))


def manhattan(a, b):
    """Return the Manhattan distance between two points.

    Args:
        a: ``(x, y)`` point.
        b: ``(x, y)`` point.

    Returns:
        int: ``|ax - bx| + |ay - by|``.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def is_on_street(x, y):
    """Return True if the point lies on a street grid line.

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        bool: True when x or y is aligned with a grid line.
    """
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


class PathPlanner:
    """Plan right-angle routes along streets between lattice nodes.

    The planner uses Dijkstra's algorithm over (node, direction) states. Each
    move costs ``step_cost`` and every change of direction adds ``turn_cost``,
    so the resulting routes prefer straight runs along a street. A target
    located directly above, below, or beside the rider is therefore reached by
    a single straight segment (the special case of direct alignment).

    Riders do not block one another; shared streets are allowed, which avoids
    deadlocks because no rider ever waits on another rider.
    """

    def __init__(self, step_cost=STEP_COST, turn_cost=TURN_COST):
        """Create a planner.

        Args:
            step_cost: Cost of moving one block along a street.
            turn_cost: Extra cost incurred when changing direction.
        """
        self.step_cost = step_cost
        self.turn_cost = turn_cost

    def plan(self, start, goal):
        """Compute a street route from ``start`` to ``goal``.

        Args:
            start: ``(x, y)`` lattice node where the route begins. The start
                node itself is not included in the result.
            goal: ``(x, y)`` lattice node where the route ends.

        Returns:
            list[tuple]: Ordered list of nodes after ``start`` up to and
            including ``goal``. Empty if ``start`` equals ``goal``.
        """
        start = to_lattice_point(start)
        goal = to_lattice_point(goal)
        if start == goal:
            return []

        best = {(start, None): 0}
        parent = {}
        tie = itertools.count()
        heap = [(0, next(tie), start, None)]

        while heap:
            cost, _, node, direction = heapq.heappop(heap)
            if cost > best.get((node, direction), math.inf):
                continue
            if node == goal:
                return self._reconstruct(parent, (node, direction))
            for nd in DIRECTIONS:
                nxt = (node[0] + nd[0] * CELL_SIZE, node[1] + nd[1] * CELL_SIZE)
                if not (0 <= nxt[0] <= GRID_SIZE and 0 <= nxt[1] <= GRID_SIZE):
                    continue
                step = self.step_cost
                if direction is not None and nd != direction:
                    step += self.turn_cost
                new_cost = cost + step
                key = (nxt, nd)
                if new_cost < best.get(key, math.inf):
                    best[key] = new_cost
                    parent[key] = (node, direction)
                    heapq.heappush(heap, (new_cost, next(tie), nxt, nd))
        return []

    @staticmethod
    def _reconstruct(parent, key):
        """Rebuild the node sequence from the parent map.

        Args:
            parent: Mapping from state to predecessor state.
            key: Final state ``(node, direction)``.

        Returns:
            list[tuple]: Nodes in travel order, excluding the start node.
        """
        path = []
        while key in parent:
            path.append(key[0])
            key = parent[key]
        path.reverse()
        return path

    @staticmethod
    def route_length(nodes, start=None):
        """Return the total Manhattan length of a node sequence.

        Args:
            nodes: Ordered list of ``(x, y)`` nodes.
            start: Optional starting point preceding ``nodes``.

        Returns:
            int: Sum of segment lengths.
        """
        total = 0
        previous = start
        for node in nodes:
            if previous is not None:
                total += manhattan(previous, node)
            previous = node
        return total
