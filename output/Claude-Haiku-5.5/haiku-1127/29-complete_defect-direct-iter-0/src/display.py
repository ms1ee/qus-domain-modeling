"""Display helpers: ASCII map rendering and text reports.

The ASCII map uses a 17x17 canvas: street lines are at even canvas indices,
cell centers at odd indices. Each canvas character represents 50 units, so
``canvas_index = coordinate // 50``.

Symbols: 'R' rider, 'S' restaurant, 'C' customer, '.' empty cell,
'#' street, '*' planned route.
"""

from typing import Iterable, List, Optional, Sequence, Tuple

from grid import CELL_SIZE, GRID_DIM
from order_model import STATUS_COMPLETED, Order
from rider import Rider

CANVAS_SIZE = 2 * GRID_DIM + 1
UNIT = CELL_SIZE // 2
Cell = Tuple[int, int]


class DisplayManager:
    """Renders the map, status snapshots and order/rider reports."""

    # ------------------------------------------------------------------
    # Map rendering
    # ------------------------------------------------------------------
    @staticmethod
    def _blank_canvas() -> List[List[str]]:
        """Create the empty street-grid canvas."""
        return [
            [
                "#" if (row % 2 == 0 or col % 2 == 0) else "."
                for col in range(CANVAS_SIZE)
            ]
            for row in range(CANVAS_SIZE)
        ]

    @staticmethod
    def _to_cell(point: Tuple[int, int]) -> Cell:
        """Convert a map point to canvas ``(row, col)``."""
        x, y = point
        col = min(x // UNIT, CANVAS_SIZE - 1)
        row = min(y // UNIT, CANVAS_SIZE - 1)
        return (row, col)

    @staticmethod
    def _span(start: int, end: int) -> List[int]:
        """Inclusive integer range from ``start`` to ``end`` in either order."""
        step = 1 if end >= start else -1
        return list(range(start, end + step, step))

    def _draw_route(self, canvas: List[List[str]], route: Sequence) -> None:
        """Draw the route as a connected line with '*' characters."""
        for first, second in zip(route, route[1:]):
            row1, col1 = self._to_cell(first)
            row2, col2 = self._to_cell(second)
            for col in self._span(col1, col2):
                self._mark_route(canvas, row1, col)
            for row in self._span(row1, row2):
                self._mark_route(canvas, row, col2)

    @staticmethod
    def _mark_route(canvas: List[List[str]], row: int, col: int) -> None:
        """Mark a route cell unless a symbol already occupies it."""
        if canvas[row][col] in ("#", "."):
            canvas[row][col] = "*"

    def render_map(
        self,
        riders: Iterable[Rider],
        orders: Iterable[Order] = (),
        route: Optional[Sequence] = None,
    ) -> str:
        """Render the 8x8 ASCII map.

        Args:
            riders: Riders to display as 'R'.
            orders: Orders whose restaurant ('S') and customer ('C')
                locations should be shown.
            route: Optional list of points drawn as a connected line.

        Returns:
            Multi-line string containing the map and a legend.
        """
        canvas = self._blank_canvas()
        if route:
            self._draw_route(canvas, route)
        for order in orders:
            row, col = self._to_cell(order.restaurant_center)
            canvas[row][col] = "S"
            row, col = self._to_cell(order.customer_center)
            canvas[row][col] = "C"
        for rider in riders:
            row, col = self._to_cell(rider.position)
            canvas[row][col] = "R"
        lines = ["".join(row) for row in canvas]
        lines.append(
            "Legend: R=Rider S=Restaurant C=Customer #=Street "
            "*=Route .=Empty (origin top-left, x->right, y->down)"
        )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Text reports
    # ------------------------------------------------------------------
    @staticmethod
    def rider_line(rider: Rider) -> str:
        """Return a one-line summary of a rider."""
        order_ids = [str(o.id) for o in rider.orders] or ["-"]
        return (
            f"Rider #{rider.rider_id:<3} | state: {rider.state_name:<10} | "
            f"pos ({rider.x:>3},{rider.y:>3}) | speed {rider.speed:>3} | "
            f"orders: {', '.join(order_ids)}"
            f"{' | waiting' if rider.special_case else ''}"
        )

    def render_status(
        self,
        funds: int,
        tick: int,
        riders: Sequence[Rider],
        pending_count: int,
    ) -> str:
        """Render the system status snapshot."""
        lines = [
            "=== System Status ===",
            f"Tick: {tick}",
            f"Funds: {funds}",
            f"Riders: {len(riders)}",
            f"Pending orders (no rider): {pending_count}",
        ]
        for rider in riders:
            lines.append("  " + self.rider_line(rider))
        if not riders:
            lines.append("  (no riders yet)")
        return "\n".join(lines)

    def render_orders(self, orders: Sequence[Order]) -> str:
        """Render the table of all orders."""
        if not orders:
            return "No orders yet."
        header = (
            f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
            f"{'Dist':>5} {'Taken':>6} {'Rider':>6} {'Status':<10}"
        )
        lines = ["=== Orders ===", header, "-" * len(header)]
        for order in orders:
            taken = (
                str(order.time_taken)
                if order.status == STATUS_COMPLETED
                else "-"
            )
            rider = str(order.rider_id) if order.rider_id is not None else "-"
            lines.append(
                f"{order.id:>4} {order.start_time:>6} "
                f"{str(order.res_pos):>12} {str(order.cus_pos):>12} "
                f"{order.distance:>5} {taken:>6} {rider:>6} "
                f"{order.status:<10}"
            )
        return "\n".join(lines)

    def render_rider_log(self, riders: Sequence[Rider]) -> str:
        """Render every recorded status change for all riders."""
        if not riders:
            return "No riders yet."
        lines = ["=== Rider Event Log ==="]
        entries = []
        for rider in riders:
            entries.extend(rider.log)
        entries.sort(key=lambda e: (e["time"], e["rider_id"]))
        if not entries:
            return "No events recorded."
        for entry in entries:
            order_text = (
                f"order {entry['order_id']}"
                if entry["order_id"] is not None
                else "-"
            )
            lines.append(
                f"tick {entry['time']:>4} | rider {entry['rider_id']:>3} | "
                f"{entry['event']:<22} | {order_text:<10} | "
                f"pos ({entry['x']},{entry['y']})"
            )
        return "\n".join(lines)

    def render_order_result(
        self, result: dict, riders: Sequence[Rider]
    ) -> str:
        """Render the response to a ``start`` command."""
        order: Order = result["order"]
        rider: Optional[Rider] = result["rider"]
        new_rider = result["new_rider"]
        lines = [
            f"Order #{order.id} accepted at tick {order.start_time}.",
            f"  Restaurant: input {order.res_pos} -> grid cell "
            f"{order.restaurant_cell} center {order.restaurant_center}",
            f"  Customer:   input {order.cus_pos} -> grid cell "
            f"{order.customer_cell} center {order.customer_center}",
            f"  Distance: {order.distance} units",
        ]
        if new_rider is not None:
            lines.append(f"  New rider added: yes (Rider #{new_rider.rider_id})")
        else:
            lines.append("  New rider added: no")
        if rider is None:
            lines.append(
                "  No rider available: the order is queued and will be "
                "assigned when capacity frees up."
            )
            lines.append(self.render_map(riders, [order]))
            return "\n".join(lines)

        lines.append(
            f"  Assigned rider: #{rider.rider_id} at {rider.position} "
            f"({rider.state_name})"
        )
        lines.append(f"  Speed: {result['speed']} units/tick")
        lines.append(
            f"  Route length: {result['route_length']} units, estimated "
            f"time: {result['eta_ticks']} tick(s)"
        )
        if result["queue_ahead"]:
            lines.append(
                f"  Note: rider has {result['queue_ahead']} order(s) ahead "
                "in the queue; the estimate excludes them."
            )
        route = result["route"]
        lines.append("  Route: " + " -> ".join(str(p) for p in route))
        lines.append(self.render_map(riders, [order], route))
        return "\n".join(lines)

    @staticmethod
    def render_help() -> str:
        """Return the command reference."""
        return "\n".join([
            "Commands (shortcut in brackets):",
            "  start [rx ry cx cy]  (s) place an order: restaurant then "
            "customer coordinates (0-800)",
            "  status               (st) funds, riders and their orders",
            "  orders               (o) all orders and their details",
            "  riders               (r) rider status-change log",
            "  map                  (m) ASCII map of riders and orders",
            "  tick [n]             (t) advance the simulation n ticks",
            "  help                 (h, ?) show this help",
            "  quit                 (q, exit) save state and exit",
            "  !!                   repeat the previous command",
            "Each command advances the simulated clock by one tick.",
        ])
