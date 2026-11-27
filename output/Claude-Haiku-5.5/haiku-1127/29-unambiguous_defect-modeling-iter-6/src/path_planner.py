"""Grid-based path planning for the food delivery simulator.

The map is an 800x800 unit plane split into an 8x8 grid of 100-unit cells.
Streets are the grid lines (points where x or y is a multiple of 100).
Restaurant and customer locations sit at cell centers (x and y equal to
``k * 100 + 50``). Planning uses a lattice with a 50-unit step, so every
node is either a street point or a cell center.

Movement rules:
    * Riders move only along streets (horizontal or vertical moves).
    * A cell center is only entered when it is the destination, so riders
      never cut through the middle of a block.
    * Breadth-first search yields a shortest route on the street network.
"""

import math
import random
from collections import deque
from typing import Deque, Dict, List, Optional, Sequence, Tuple

Point = Tuple[int, int]

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIMENSION = MAP_SIZE // CELL_SIZE
STEP = 50
NODES_PER_AXIS = MAP_SIZE // STEP + 1
_DIRECTIONS = ((STEP, 0), (-STEP, 0), (0, STEP), (0, -STEP))


class Grid:
    """Geometry helper describing the 8x8 cell grid.

    Attributes:
        size_units: Map size in coordinate units (800).
        cell_size: Size of one cell in units (100).
        dimension: Number of cells per axis (8).
    """

    def __init__(self, size_units: int = MAP_SIZE, cell_size: int = CELL_SIZE) -> None:
        self.size_units = size_units
        self.cell_size = cell_size
        self.dimension = size_units // cell_size

    def cell_index(self, value: int) -> int:
        """Return the cell index (0-7) that contains a coordinate value.

        Values outside the map are clamped to the nearest valid cell.
        """
        index = value // self.cell_size
        return min(max(index, 0), self.dimension - 1)

    def cell_center(self, value: int) -> int:
        """Convert a coordinate to the center of its cell.

        Implements ``center = (value // 100) * 100 + 50``, with clamping.
        """
        return self.cell_index(value) * self.cell_size + self.cell_size // 2

    def contains(self, x: int, y: int) -> bool:
        """Return True if the point lies inside the map bounds."""
        return 0 <= x <= self.size_units and 0 <= y <= self.size_units

    def is_street(self, x: int, y: int) -> bool:
        """Return True if the point lies on a street (a grid line)."""
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def is_location(self, x: int, y: int) -> bool:
        """Return True if the point is a cell center (restaurant/customer spot)."""
        half = self.cell_size // 2
        return x % self.cell_size == half and y % self.cell_size == half


class PathPlanner:
    """Plans routes on the street network.

    Attributes:
        grid: The Grid geometry used for planning.
        prefer_streets: When True, cell centers are not used as through points.
    """

    def __init__(self, grid: Optional[Grid] = None, prefer_streets: bool = True) -> None:
        self.grid = grid or Grid()
        self.prefer_streets = prefer_streets
        self._road_nodes: List[Point] = [
            (x, y)
            for x in range(0, MAP_SIZE + 1, STEP)
            for y in range(0, MAP_SIZE + 1, STEP)
            if self.grid.is_street(x, y)
        ]

    def road_nodes(self) -> List[Point]:
        """Return a copy of all street nodes on the lattice."""
        return list(self._road_nodes)

    def random_road_node(self, rng: Optional[random.Random] = None) -> Point:
        """Pick a random street node, used to place riders on a road."""
        source = rng or random
        return source.choice(self._road_nodes)

    def is_passable(self, node: Point, goal: Point) -> bool:
        """Return True if a route may pass through ``node``.

        Cell centers are dead ends: they are only passable when they are the
        goal. This keeps riders on streets, with the exception of the final
        step into a restaurant or customer location.
        """
        x, y = node
        if not self.grid.contains(x, y):
            return False
        if self.prefer_streets and self.grid.is_location(x, y):
            return node == goal
        return True

    def find_path(self, start: Point, goal: Point) -> Optional[List[Point]]:
        """Find the shortest street route from ``start`` to ``goal``.

        Args:
            start: Starting point (not included in the result).
            goal: Destination point (included as the last element).

        Returns:
            Ordered list of lattice points from the first step to ``goal``.
            An empty list if ``start == goal``. None if no route exists.
        """
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return []
        if not self.grid.contains(*start) or not self.grid.contains(*goal):
            return None

        came_from: Dict[Point, Optional[Point]] = {start: None}
        queue: Deque[Point] = deque([start])
        while queue:
            current = queue.popleft()
            if current == goal:
                break
            for dx, dy in _DIRECTIONS:
                nxt = (current[0] + dx, current[1] + dy)
                if nxt in came_from or not self.is_passable(nxt, goal):
                    continue
                came_from[nxt] = current
                queue.append(nxt)

        if goal not in came_from:
            return None

        path: List[Point] = []
        node: Optional[Point] = goal
        while node is not None and node != start:
            path.append(node)
            node = came_from[node]
        path.reverse()
        return path

    @staticmethod
    def is_straight_line(a: Point, b: Point) -> bool:
        """Return True if two points share an x or y coordinate.

        Used for the special case where a rider is directly above or below
        its target.
        """
        return a[0] == b[0] or a[1] == b[1]

    @staticmethod
    def path_length_units(path: Sequence[Point]) -> int:
        """Return the travel distance of a path in coordinate units."""
        return len(path) * STEP

    @staticmethod
    def estimate_ticks(steps: int, speed: int) -> int:
        """Estimate how many ticks a rider needs to cover ``steps`` lattice steps.

        A rider moves ``max(1, speed // STEP)`` lattice steps per tick.
        """
        if steps <= 0:
            return 0
        steps_per_tick = max(1, speed // STEP)
        return int(math.ceil(steps / steps_per_tick))
