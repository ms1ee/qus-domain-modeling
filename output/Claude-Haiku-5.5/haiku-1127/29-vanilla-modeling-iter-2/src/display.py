"""Status text, order and rider reports, and ASCII map rendering."""

from typing import Any, List, Optional, Sequence, Tuple

from path_planner import MAP_SIZE
from rider import STATE_NAMES

Point = Tuple[int, int]

# One map character per 50 units. Grid lines (multiples of 100) fall on even
# indexes; cell centres (50, 150, ...) fall on odd indexes.
STEP = 50

LEGEND = "S=Restaurant  C=Customer  R=Rider  #=Street  .=Empty  *=Route"


class DisplayManager:
    """Builds textual reports and the ASCII map for the command line.

    Attributes:
        system: The ``SystemManager`` being displayed.
        order_manager: The ``OrderManager`` providing order data (optional).
        map_size: Size of the map in units.
    """

    def __init__(self, system: Any, order_manager: Any = None,
                 map_size: int = MAP_SIZE) -> None:
        """Create a display manager.

        Args:
            system: System manager instance.
            order_manager: Order manager instance, or None.
            map_size: Size of the square map in units.
        """
        self.system = system
        self.order_manager = order_manager
        self.map_size = map_size
        self.dim = map_size // STEP + 1

    # ------------------------------------------------------------------
    # Map rendering
    # ------------------------------------------------------------------
    def _index(self, value: int) -> int:
        """Convert a coordinate to a map character index."""
        return min(max(int(value), 0) // STEP, self.dim - 1)

    def _blank_grid(self) -> List[List[str]]:
        """Return an empty canvas with street lines drawn."""
        return [["#" if (row % 2 == 0 or col % 2 == 0) else "."
                 for col in range(self.dim)]
                for row in range(self.dim)]

    def _plot(self, grid: List[List[str]], point: Point, symbol: str) -> None:
        """Place a symbol at the map position of ``point``."""
        x, y = point
        grid[self._index(y)][self._index(x)] = symbol

    def _draw_route(self, grid: List[List[str]], points: Sequence[Point],
                    start: Point) -> None:
        """Draw connected route segments with '*' characters.

        Args:
            grid: Canvas to draw on.
            points: Route waypoints in order.
            start: Route starting point.
        """
        prev = start
        for point in points:
            px, py = point
            qx, qy = prev
            if px == qx:
                col = self._index(px)
                lo, hi = sorted((self._index(qy), self._index(py)))
                for row in range(lo, hi + 1):
                    grid[row][col] = "*"
            elif py == qy:
                row = self._index(py)
                lo, hi = sorted((self._index(qx), self._index(px)))
                for col in range(lo, hi + 1):
                    grid[row][col] = "*"
            prev = point

    def render(self, route: Optional[Sequence[Point]] = None,
               route_start: Optional[Point] = None) -> str:
        """Render the ASCII map.

        Args:
            route: Optional waypoints to draw as a connected line.
            route_start: Starting point of the route (defaults to the first
                riders' position when omitted).

        Returns:
            Multi-line string containing the map and the legend.
        """
        grid = self._blank_grid()
        if route:
            start = route_start if route_start is not None else route[0]
            self._draw_route(grid, route, start)
        if self.order_manager is not None:
            for order in self.order_manager.active_orders():
                self._plot(grid, order.res_pos, "S")
                self._plot(grid, order.cus_pos, "C")
        for rider in self.system.riders:
            self._plot(grid, (rider.x, rider.y), "R")

        lines = ["y\\x"]
        for row_index, row in enumerate(grid):
            lines.append(f"{row_index * STEP:>4} " + " ".join(row))
        lines.append(f"x: 0..{self.map_size} left to right, rows every {STEP} units")
        lines.append(LEGEND)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Text reports
    # ------------------------------------------------------------------
    def status_text(self) -> str:
        """Return the system snapshot: funds, riders and their orders."""
        riders = self.system.riders
        idle = sum(1 for rider in riders if rider.state == 0)
        lines = [
            f"Simulation tick: {self.system.current_tick}",
            f"System funds: {self.system.funds}",
            f"Riders: {len(riders)} (idle {idle}, busy {len(riders) - idle})",
        ]
        for rider in riders:
            order_ids = ", ".join(f"#{o.id}" for o in rider.orders) or "-"
            lines.append(
                f"  Rider #{rider.rider_id}: position ({rider.x}, {rider.y}) | "
                f"status: {STATE_NAMES.get(rider.state, 'unknown')} | "
                f"orders: {len(rider.orders)} [{order_ids}]")
        pending = self.order_manager.pending_count() if self.order_manager else 0
        lines.append(f"Pending orders: {pending}")
        return "\n".join(lines)

    def orders_text(self) -> str:
        """Return a table of all orders with timing and assignment details."""
        orders = self.order_manager.orders if self.order_manager else []
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Distance':>9} {'Time':>6} {'Eff':>7} {'Rider':>6} {'Status':>10}")
        lines = [header, "-" * len(header)]
        for order in orders:
            restaurant = f"({order.res_pos[0]},{order.res_pos[1]})"
            customer = f"({order.cus_pos[0]},{order.cus_pos[1]})"
            time_taken = str(order.time_taken) if order.time_taken is not None else "-"
            efficiency = (f"{order.efficiency:.2f}"
                          if order.efficiency is not None else "-")
            rider = f"#{order.rider_id}" if order.rider_id is not None else "-"
            lines.append(
                f"{order.id:>4} {order.start_time:>6} {restaurant:>12} {customer:>12} "
                f"{order.distance:>9.1f} {time_taken:>6} {efficiency:>7} "
                f"{rider:>6} {order.status:>10}")
        return "\n".join(lines)

    def riders_text(self) -> str:
        """Return every recorded status change for every rider."""
        lines: List[str] = []
        for rider in self.system.riders:
            lines.append(f"Rider #{rider.rider_id} (speed {rider.speed}/tick):")
            if not rider.log:
                lines.append("  no records")
            for entry in rider.log:
                order = f"#{entry['order_id']}" if entry["order_id"] is not None else "-"
                lines.append(
                    f"  tick {entry['tick']:>4} | {entry['event']:<20} | "
                    f"order {order:>5} | pos ({entry['x']},{entry['y']}) | "
                    f"{STATE_NAMES.get(entry['state'], 'unknown')}")
        return "\n".join(lines) if lines else "No riders yet."
