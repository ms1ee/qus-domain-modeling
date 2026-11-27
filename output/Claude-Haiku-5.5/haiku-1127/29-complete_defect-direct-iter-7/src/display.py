"""Status displays, route maps and the ASCII city map.

Map layout: the 8x8 grid of cells is drawn on a 15x15 character canvas.
Cell centres sit at even rows/columns (shown as '.'), and the street
segments between neighbouring cells sit at odd positions (shown as '#').
"""

from __future__ import annotations

from typing import Iterable, Sequence

import config
from order_model import STATUS_COMPLETED, grid_index
from rider import STATE_NAMES

Point = tuple[int, int]


class DisplayManager:
    """Renders status text, order and rider tables, and ASCII maps."""

    SYMBOL_RIDER = "R"
    SYMBOL_RESTAURANT = "S"
    SYMBOL_CUSTOMER = "C"
    SYMBOL_EMPTY = "."
    SYMBOL_STREET = "#"
    SYMBOL_ROUTE = "*"

    def __init__(self) -> None:
        """Compute the canvas size for the configured grid."""
        self.size = 2 * config.GRID_SIZE - 1

    # ------------------------------------------------------------------
    # Map helpers
    # ------------------------------------------------------------------
    def _blank_canvas(self) -> list[list[str]]:
        """Return a canvas with cell centres and street segments filled."""
        return [
            [self.SYMBOL_EMPTY if r % 2 == 0 and c % 2 == 0
             else self.SYMBOL_STREET for c in range(self.size)]
            for r in range(self.size)
        ]

    @staticmethod
    def _to_canvas(point: Sequence[int]) -> tuple[int, int]:
        """Map a map coordinate to its (row, column) canvas position."""
        gx, gy = grid_index(point[0], point[1])
        return 2 * gy, 2 * gx

    def _place(self, canvas: list[list[str]], point: Sequence[int],
               symbol: str) -> None:
        """Write a symbol at the cell containing ``point``."""
        row, col = self._to_canvas(point)
        canvas[row][col] = symbol

    def _draw_route(self, canvas: list[list[str]],
                    points: Iterable[Sequence[int]]) -> None:
        """Draw a connected line through consecutive points."""
        points = list(points)
        for a, b in zip(points, points[1:]):
            r1, c1 = self._to_canvas(a)
            r2, c2 = self._to_canvas(b)
            for col in range(min(c1, c2), max(c1, c2) + 1):
                canvas[r1][col] = self.SYMBOL_ROUTE
            for row in range(min(r1, r2), max(r1, r2) + 1):
                canvas[row][c2] = self.SYMBOL_ROUTE

    def _frame(self, canvas: list[list[str]], title: str) -> str:
        """Wrap a canvas with a title, axis labels and a legend."""
        prefix = "   "
        width = len(prefix) + 2 * (self.size - 1) + 1
        header = [" "] * width
        for gx in range(config.GRID_SIZE):
            header[len(prefix) + 4 * gx] = str(gx)
        lines = [title, "".join(header).rstrip()]
        for r, row in enumerate(canvas):
            label = f"{r // 2:>2} " if r % 2 == 0 else "   "
            lines.append(label + " ".join(row))
        lines.append("Columns = x cell index, rows = y cell index "
                     "(y grows downwards).")
        lines.append("Legend: R rider  S restaurant  C customer  "
                     ". cell centre  # street  * route")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Public rendering API
    # ------------------------------------------------------------------
    def render_map(self, riders: Iterable, orders: Iterable) -> str:
        """Render the current city map with riders and active orders.

        Args:
            riders: Riders to plot.
            orders: Orders; only non-completed orders are plotted.

        Returns:
            str: Multi-line ASCII map.
        """
        canvas = self._blank_canvas()
        for order in orders:
            if order.status == STATUS_COMPLETED:
                continue
            self._place(canvas, order.res_pos, self.SYMBOL_RESTAURANT)
            self._place(canvas, order.cus_pos, self.SYMBOL_CUSTOMER)
        for rider in riders:
            self._place(canvas, rider.position, self.SYMBOL_RIDER)
        return self._frame(canvas, "City map (current state)")

    def render_route(self, start: Sequence[int], waypoints: Iterable,
                     restaurant: Sequence[int],
                     customer: Sequence[int]) -> str:
        """Render a rider's planned route as a connected line graph.

        Args:
            start: Rider's current position.
            waypoints: Planned route waypoints.
            restaurant: Restaurant cell centre.
            customer: Customer cell centre.

        Returns:
            str: Multi-line ASCII map of the route.
        """
        canvas = self._blank_canvas()
        self._draw_route(canvas, [tuple(start), *waypoints])
        self._place(canvas, restaurant, self.SYMBOL_RESTAURANT)
        self._place(canvas, customer, self.SYMBOL_CUSTOMER)
        self._place(canvas, start, self.SYMBOL_RIDER)
        return self._frame(canvas, "Assigned route")

    def render_status(self, system) -> str:
        """Render funds, rider count and every rider's state and orders.

        Args:
            system: The SystemManager instance.

        Returns:
            str: Status report.
        """
        riders = system.riders
        pending = system.order_manager.pending_orders()
        lines = [
            f"Tick: {system.tick}",
            f"System funds: {system.funds}",
            f"Riders: {len(riders)}",
            f"Pending orders: {len(pending)}",
        ]
        if not riders:
            lines.append(
                f"  No riders yet. Recruitment occurs at funds >= "
                f"{config.RECRUIT_THRESHOLD}.")
        for rider in riders:
            gx, gy = grid_index(rider.x, rider.y)
            orders = ", ".join(f"#{o.id}({o.status})"
                               for o in rider.orders) or "none"
            flag = " [yielding]" if rider.special_case else ""
            lines.append(
                f"  Rider #{rider.rider_id}: "
                f"{STATE_NAMES.get(rider.state, 'unknown')}{flag} | "
                f"cell ({gx},{gy}) at ({rider.x},{rider.y}) | "
                f"speed {rider.speed} | orders: {orders}")
        return "\n".join(lines)

    def render_orders(self, orders: Sequence) -> str:
        """Render a table of all orders.

        Args:
            orders: Orders to display.

        Returns:
            str: Table text.
        """
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} "
                  f"{'Customer':>12} {'Dist':>6} {'Time':>6} "
                  f"{'Rider':>6} {'Status':<12}")
        rows = [header, "-" * len(header)]
        for order in orders:
            res = f"({order.res_pos[0]},{order.res_pos[1]})"
            cus = f"({order.cus_pos[0]},{order.cus_pos[1]})"
            taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else f"#{order.rider_id}"
            rows.append(
                f"{order.id:>4} {order.start_tick:>6} {res:>12} {cus:>12} "
                f"{order.distance:>6} {taken:>6} {rider:>6} "
                f"{order.status:<12}")
        return "\n".join(rows)

    def render_rider_log(self, riders: Sequence) -> str:
        """Render the status-change log of every rider.

        Args:
            riders: Riders whose logs are shown.

        Returns:
            str: Log text.
        """
        if not riders:
            return "No riders."
        lines: list[str] = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} (speed {rider.speed}):")
            if not rider.log:
                lines.append("  (no records)")
            for entry in rider.log:
                oid = "-" if entry["order_id"] is None \
                    else f"#{entry['order_id']}"
                state = STATE_NAMES.get(entry["state"], "unknown")
                lines.append(
                    f"  t={entry['tick']:<5} {entry['event']:<22} "
                    f"order {oid:<6} at ({entry['x']},{entry['y']}) "
                    f"state={state}")
        return "\n".join(lines)

    @staticmethod
    def format_event(event: dict) -> str:
        """Format a simulation event as a single console line.

        Args:
            event: Event dictionary produced by rider or system logic.

        Returns:
            str: Human-readable line prefixed with the tick number.
        """
        tick = event.get("tick", "?")
        name = event.get("event")
        rid = event.get("rider_id")
        oid = event.get("order_id")
        if name == "accepted_order":
            text = (f"Rider #{rid} accepted order #{oid} "
                    f"and is heading to the restaurant.")
        elif name == "arrived_at_merchant":
            text = (f"Rider #{rid} picked up order #{oid} "
                    f"and is delivering it.")
        elif name == "delivered_to_customer":
            text = f"Rider #{rid} delivered order #{oid} to the customer."
        elif name == "assigned":
            text = f"Queued order #{oid} assigned to rider #{rid}."
        elif name == "recovered":
            text = f"Rider #{rid} recovered from an internal error."
        elif name == "spawn":
            text = f"Rider #{rid} joined the fleet."
        else:
            text = f"Rider #{rid}: {name}"
        return f"[t={tick}] {text}"
