"""Grid-based path planning for the street network.

Each grid cell center is a street intersection (node). Riders travel along the
streets between adjacent nodes. The planner uses Dijkstra's algorithm with a
small penalty for each right-angle turn, so it prefers straight streets and
produces the shortest route with the fewest turns.
"""

import heapq
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from location import Location, to_grid_index
from settings import CONFIG

Node = Tuple[int, int]
Point = Tuple[int, int]
DIRECTIONS: Tuple[Node, ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))
NO_DIRECTION = -1


@dataclass
class Cell:
    """A single grid cell.

    Attributes:
        row: Row index of the cell.
        col: Column index of the cell.
        is_street: Whether the cell lies on the street network.
    """

    row: int
    col: int
    is_street: bool = True


class Grid:
    """The 8x8 grid of cells that makes up the city map."""

    def __init__(self) -> None:
        self.map_size = CONFIG["map_size"]
        self.cell_size = CONFIG["cell_size"]
        self.dimensions = self.map_size // self.cell_size
        self.cells: List[List[Cell]] = [
            [Cell(row, col) for col in range(self.dimensions)]
            for row in range(self.dimensions)
        ]

    def in_bounds(self, node: Node) -> bool:
        """Return True if the ``(col, row)`` node is inside the grid."""
        col, row = node
        return 0 <= col < self.dimensions and 0 <= row < self.dimensions

    def cell_at(self, node: Node) -> Cell:
        """Return the cell at the given ``(col, row)`` node."""
        col, row = node
        return self.cells[row][col]


class Route:
    """A planned route through the grid.

    Attributes:
        waypoints: Ordered list of Location objects, starting at the origin.
        total_distance: Total travelled distance in map units.
        estimated_ticks: Ticks needed at the planned speed.
    """

    def __init__(self, waypoints: List[Location], total_distance: int,
                 estimated_ticks: int) -> None:
        self.waypoints = waypoints
        self.total_distance = total_distance
        self.estimated_ticks = estimated_ticks

    def coordinates(self) -> List[Point]:
        """Return the waypoints as a list of ``(x, y)`` tuples."""
        return [(wp.x, wp.y) for wp in self.waypoints]


class PathPlanner:
    """Plans street-following routes on the grid."""

    def __init__(self, turn_penalty: Optional[int] = None) -> None:
        self.grid = Grid()
        self.cell_size = self.grid.cell_size
        self.turn_penalty = (
            CONFIG["turn_penalty"] if turn_penalty is None else turn_penalty
        )

    @staticmethod
    def snap(point: Point) -> Node:
        """Return the grid node nearest to a map point (its containing cell)."""
        return (to_grid_index(point[0]), to_grid_index(point[1]))

    @staticmethod
    def is_aligned(start: Point, goal: Point) -> bool:
        """Return True if two points share an x or y line (straight run).

        This covers the special case where a rider is directly above or below
        (or beside) its target.
        """
        return start[0] == goal[0] or start[1] == goal[1]

    def plan(self, start: Point, goal: Point, speed: Optional[int] = None) -> Route:
        """Plan a route from ``start`` to ``goal`` along the streets.

        Args:
            start: Origin point in map units.
            goal: Destination point in map units.
            speed: Movement speed in units per tick (defaults to config).

        Returns:
            A Route whose waypoints are grid node centers.
        """
        speed = speed or CONFIG["rider_speed"]
        nodes = self.shortest_path(self.snap(start), self.snap(goal))
        waypoints = [Location.from_node(col, row) for col, row in nodes]
        total = (len(nodes) - 1) * self.cell_size
        ticks = math.ceil(total / speed) if total else 0
        return Route(waypoints, total, ticks)

    def plan_route(self, start: Point, stops: Sequence[Point],
                   speed: Optional[int] = None) -> Route:
        """Plan one continuous route through several stops in order.

        This is the multi-destination path used for restaurant-then-customer
        trips. Shared junctions between consecutive legs are not duplicated.

        Args:
            start: Origin point in map units.
            stops: Ordered destination points in map units.
            speed: Movement speed in units per tick (defaults to config).

        Returns:
            A Route covering all legs.
        """
        speed = speed or CONFIG["rider_speed"]
        combined: List[Location] = []
        total = 0
        current = start
        for stop in stops:
            leg = self.plan(current, stop, speed)
            points = leg.waypoints[1:] if combined else leg.waypoints
            combined.extend(points)
            total += leg.total_distance
            current = stop
        if not combined:
            combined = [Location.from_node(*self.snap(start))]
        ticks = math.ceil(total / speed) if total else 0
        return Route(combined, total, ticks)

    def shortest_path(self, start: Node, goal: Node) -> List[Node]:
        """Find the cheapest node sequence from ``start`` to ``goal``.

        The search state includes the direction of the last move, so that
        turns carry a penalty and straight streets are preferred.

        Returns:
            List of ``(col, row)`` nodes, including both endpoints.

        Raises:
            RuntimeError: If no path exists (cannot happen on this grid).
        """
        if start == goal:
            return [start]
        start_state = (start, NO_DIRECTION)
        best_cost: Dict[Tuple[Node, int], float] = {start_state: 0}
        previous: Dict[Tuple[Node, int], Tuple[Node, int]] = {}
        heap = [(0, start, NO_DIRECTION)]
        while heap:
            cost, node, came_dir = heapq.heappop(heap)
            state = (node, came_dir)
            if cost > best_cost.get(state, math.inf):
                continue
            if node == goal:
                return self._rebuild(state, previous)
            for direction, (dc, dr) in enumerate(DIRECTIONS):
                nxt = (node[0] + dc, node[1] + dr)
                if not self.grid.in_bounds(nxt):
                    continue
                step = self.cell_size
                if came_dir != NO_DIRECTION and direction != came_dir:
                    step += self.turn_penalty
                new_cost = cost + step
                next_state = (nxt, direction)
                if new_cost < best_cost.get(next_state, math.inf):
                    best_cost[next_state] = new_cost
                    previous[next_state] = state
                    heapq.heappush(heap, (new_cost, nxt, direction))
        raise RuntimeError(f"no route found from {start} to {goal}")

    @staticmethod
    def _rebuild(state: Tuple[Node, int],
                 previous: Dict[Tuple[Node, int], Tuple[Node, int]]) -> List[Node]:
        """Walk predecessor links back to the start and return the nodes."""
        nodes = [state[0]]
        while state in previous:
            state = previous[state]
            nodes.append(state[0])
        nodes.reverse()
        return nodes


_DEFAULT_PLANNER: Optional[PathPlanner] = None


def default_planner() -> PathPlanner:
    """Return the shared PathPlanner, creating it on first use.

    The planner is created lazily so that configuration loaded at startup is
    applied to it.
    """
    global _DEFAULT_PLANNER
    if _DEFAULT_PLANNER is None:
        _DEFAULT_PLANNER = PathPlanner()
    return _DEFAULT_PLANNER
