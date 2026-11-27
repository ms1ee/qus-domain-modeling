"""Status text and ASCII map rendering."""

import math
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

from grid_map import DISPLAY_STEP, GridMap
from order_model import STATUS_COMPLETED
from rider import STATE_NAMES

SYMBOL_RIDER = "R"
SYMBOL_RESTAURANT = "S"
SYMBOL_CUSTOMER = "C"
SYMBOL_EMPTY = "."
SYMBOL_STREET = "#"
SYMBOL_ROUTE = "*"
DISPLAY_GRID_SIZE = 16


class DisplayManager:
    """Renders the simulation state for the command line."""

    def __init__(self, grid: Optional[GridMap] = None,
                 display_grid_size: int = DISPLAY_GRID_SIZE) -> None:
        """Create a display manager.

        Args:
            grid: Map used to decide which points are streets.
            display_grid_size: Number of character cells per side (16).
        """
        self.grid = grid or GridMap()
        self.display_grid_size = int(display_grid_size)
        self.step = DISPLAY_STEP

    def _node(self, x: float, y: float) -> Tuple[int, int]:
        """Map a world coordinate to a (row, col) character node."""
        limit = self.display_grid_size
        col = min(limit, max(0, round(x / self.step)))
        row = min(limit, max(0, round(y / self.step)))
        return row, col

    def _segment_nodes(self, start: Tuple[int, int], end: Tuple[int, int]) -> Iterator[Tuple[int, int]]:
        """Yield character nodes sampled along a straight segment."""
        ax, ay = start
        bx, by = end
        length = abs(bx - ax) + abs(by - ay)
        steps = max(1, math.ceil(length / self.step))
        for i in range(steps + 1):
            t = i / steps
            yield self._node(ax + (bx - ax) * t, ay + (by - ay) * t)

    def render_map(self, riders: Iterable = (), orders: Iterable = (),
                   route: Optional[Sequence[Tuple[int, int]]] = None) -> str:
        """Render the ASCII city map.

        Args:
            riders: Riders to mark with 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') are marked.
            route: Optional list of points drawn as a connected route ('*').

        Returns:
            Multi-line string containing the map and a legend.
        """
        size = self.display_grid_size + 1
        canvas: List[List[str]] = [[SYMBOL_EMPTY] * size for _ in range(size)]
        for row in range(size):
            for col in range(size):
                if self.grid.is_street(col * self.step, row * self.step):
                    canvas[row][col] = SYMBOL_STREET

        if route:
            points = list(route)
            pairs = list(zip(points, points[1:])) or [(points[0], points[0])]
            for a, b in pairs:
                for row, col in self._segment_nodes(a, b):
                    canvas[row][col] = SYMBOL_ROUTE

        for order in orders:
            r, c = self._node(order.restaurant_x, order.restaurant_y)
            canvas[r][c] = SYMBOL_RESTAURANT
            r, c = self._node(order.customer_x, order.customer_y)
            canvas[r][c] = SYMBOL_CUSTOMER

        for rider in riders:
            r, c = self._node(rider.x, rider.y)
            canvas[r][c] = SYMBOL_RIDER

        lines = []
        for row in range(size):
            y_value = row * self.step
            label = f"{y_value:>4} " if y_value % 100 == 0 else "     "
            lines.append(label + " ".join(canvas[row]))
        lines.append("Legend: R=rider S=restaurant C=customer #=street .=empty *=route")
        return "\n".join(lines)

    def format_status(self, funds: int, tick: int, riders: Sequence) -> str:
        """Format the status snapshot of the system.

        Args:
            funds: Current system funds.
            tick: Current simulated time.
            riders: All riders.

        Returns:
            Multi-line status text.
        """
        lines = [f"System funds: {funds}", f"Current tick: {tick}", f"Riders: {len(riders)}"]
        if not riders:
            lines.append("  (no riders recruited yet)")
        for rider in riders:
            active = [o.id for o in rider.active_orders()]
            lines.append(
                f"  Rider #{rider.rider_id}: location ({rider.x}, {rider.y}) | "
                f"status {STATE_NAMES.get(rider.state, 'unknown')} | "
                f"active orders {len(active)} {active} | total orders {len(rider.orders)}"
            )
        return "\n".join(lines)

    def format_orders(self, orders: Sequence) -> str:
        """Format a table of all orders.

        Args:
            orders: Orders to display.

        Returns:
            Multi-line table text.
        """
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Distance':>9} {'Time':>6} {'Rider':>6} {'Status':>10}")
        lines = [header, "-" * len(header)]
        for o in orders:
            time_text = str(o.time_taken) if o.status == STATUS_COMPLETED else "-"
            rider_text = str(o.assigned_rider_id) if o.assigned_rider_id is not None else "-"
            lines.append(
                f"{o.id:>4} {o.start_time:>6} {str((o.restaurant_x, o.restaurant_y)):>12} "
                f"{str((o.customer_x, o.customer_y)):>12} {o.distance:>9.1f} {time_text:>6} "
                f"{rider_text:>6} {o.status:>10}"
            )
        return "\n".join(lines)

    def format_rider_log(self, riders: Sequence) -> str:
        """Format every recorded status change of all riders.

        Args:
            riders: Riders whose logs should be shown.

        Returns:
            Multi-line log text.
        """
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id}:")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order_text = f"order {entry['order_id']}" if entry["order_id"] is not None else "-"
                lines.append(
                    f"  tick {entry['tick']:>4} | {entry['event']:<20} | {order_text:<10} | "
                    f"pos ({entry['x']}, {entry['y']}) | state {STATE_NAMES.get(entry['state'], '?')}"
                )
        return "\n".join(lines) if lines else "No riders yet."

    def format_route_report(self, order, rider, ticks: int) -> str:
        """Format the summary shown after a delivery simulation.

        Args:
            order: The simulated order.
            rider: The assigned rider.
            ticks: Ticks simulated while watching the order.

        Returns:
            Multi-line report text.
        """
        time_value = order.time_taken if order.status == STATUS_COMPLETED else ticks
        return "\n".join([
            f"Order #{order.id} assigned to rider #{rider.rider_id}",
            f"Rider speed: {rider.speed} units/tick",
            f"Time: {time_value} ticks",
            f"Distance: {order.distance:.1f} units",
            f"Route points: {len(order.route)}",
        ])
