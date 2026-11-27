"""Status display and ASCII map visualisation.

The ASCII map is 16x16 characters. Each character covers a 50x50 unit area,
so the displayed area spans 0-750 on both axes. Symbols:
    R = rider, S = restaurant, C = customer, # = street, . = empty,
    * = planned route line.
"""

from typing import Any, Iterable, List, Optional, Sequence, Tuple

MAP_CELLS = 16
MAP_UNIT = 50
CELL_SIZE = 100

SYMBOL_RIDER = "R"
SYMBOL_RESTAURANT = "S"
SYMBOL_CUSTOMER = "C"
SYMBOL_EMPTY = "."
SYMBOL_STREET = "#"
SYMBOL_ROUTE = "*"


class DisplayManager:
    """Builds textual status tables and the command-line map."""

    @staticmethod
    def _index(value: float) -> int:
        """Map a coordinate to a map character index (clamped)."""
        return min(max(int(value), 0) // MAP_UNIT, MAP_CELLS - 1)

    def render_status(self, funds: int, riders: Sequence[Any],
                      tick: int, pending: int) -> str:
        """Render a snapshot of system funds, riders and their orders.

        Args:
            funds: Current system funds.
            riders: Riders to display.
            tick: Current simulated tick.
            pending: Number of unassigned orders.

        Returns:
            Multi-line status text.
        """
        lines = [
            f"=== System Status (tick {tick}) ===",
            f"System funds: {funds}",
            f"Pending (unassigned) orders: {pending}",
            f"Riders: {len(riders)}",
        ]
        if riders:
            lines.append(
                f"{'ID':<5}{'Position':<14}{'Status':<14}"
                f"{'Active':<8}Order IDs")
            for rider in riders:
                active = rider.active_orders()
                order_ids = [o.id for o in rider.orders]
                lines.append(
                    f"#{rider.rider_id:<4}"
                    f"{str((rider.x, rider.y)):<14}"
                    f"{rider.state_name:<14}"
                    f"{len(active):<8}{order_ids}")
        return "\n".join(lines)

    def render_orders(self, orders: Iterable[Any]) -> str:
        """Render a table of all orders.

        Args:
            orders: Orders to display.

        Returns:
            Multi-line table text.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        lines = [
            f"{'ID':<5}{'Start':<7}{'Restaurant':<13}{'Customer':<13}"
            f"{'Dist':<6}{'Taken':<7}{'Rider':<7}Status",
        ]
        for o in orders:
            taken = "-" if o.time_taken is None else str(o.time_taken)
            rider = "-" if o.rider_id is None else f"#{o.rider_id}"
            lines.append(
                f"{o.id:<5}{o.start_time:<7}{str(o.res_pos):<13}"
                f"{str(o.cus_pos):<13}{o.distance:<6}{taken:<7}"
                f"{rider:<7}{o.status}")
            if o.completion_time is not None:
                lines.append(
                    f"      completed at tick {o.completion_time}, "
                    f"efficiency {o.efficiency:.2f} units/tick")
        return "\n".join(lines)

    def render_rider_logs(self, riders: Sequence[Any]) -> str:
        """Render every status-change record for all riders.

        Args:
            riders: Riders whose logs should be displayed.

        Returns:
            Multi-line log text.
        """
        if not riders:
            return "No riders."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"--- Rider #{rider.rider_id} ---")
            for entry in rider.log:
                order = ("-" if entry["order_id"] is None
                         else f"order #{entry['order_id']}")
                lines.append(
                    f"  t={entry['time']:<5}{entry['event']:<22}{order:<12}"
                    f"at ({entry['x']}, {entry['y']}) "
                    f"state={entry['state']}")
        return "\n".join(lines)

    def render_map(self, riders: Sequence[Any] = (),
                   orders: Sequence[Any] = (),
                   route: Optional[Sequence[Tuple[int, int]]] = None) -> str:
        """Render the 16x16 ASCII map with riders, orders and an optional route.

        Args:
            riders: Riders to mark with 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') to mark.
            route: Optional list of waypoints drawn as a connected line.

        Returns:
            Multi-line map text including a legend.
        """
        size = MAP_CELLS
        grid = [[SYMBOL_EMPTY] * size for _ in range(size)]
        for row in range(size):
            for col in range(size):
                x, y = col * MAP_UNIT, row * MAP_UNIT
                if x % CELL_SIZE == 0 or y % CELL_SIZE == 0:
                    grid[row][col] = SYMBOL_STREET

        def mark(x: float, y: float, symbol: str) -> None:
            grid[self._index(y)][self._index(x)] = symbol

        if route:
            for (x1, y1), (x2, y2) in zip(route, route[1:]):
                dist = abs(x2 - x1) + abs(y2 - y1)
                steps = max(1, dist // 10)
                for i in range(steps + 1):
                    t = i / steps
                    mark(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, SYMBOL_ROUTE)

        for order in orders:
            mark(order.res_pos[0], order.res_pos[1], SYMBOL_RESTAURANT)
            mark(order.cus_pos[0], order.cus_pos[1], SYMBOL_CUSTOMER)

        for rider in riders:
            mark(rider.x, rider.y, SYMBOL_RIDER)

        lines = []
        for row in range(size):
            label = f"{row * MAP_UNIT:>4} "
            lines.append(label + " ".join(grid[row]))
        lines.append("")
        lines.append("Legend: R=rider S=restaurant C=customer "
                     "#=street .=empty *=route")
        lines.append("Each character = 50 units; top-left is (0, 0).")
        return "\n".join(lines)
