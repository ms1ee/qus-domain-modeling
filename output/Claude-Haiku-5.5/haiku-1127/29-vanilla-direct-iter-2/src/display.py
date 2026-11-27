"""Status display and ASCII map visualization."""

import logging
from typing import Any, Iterable, List, Sequence, Tuple

from rider import STATE_NAMES

logger = logging.getLogger(__name__)


class DisplayManager:
    """Renders simulator status, order tables, rider logs and the ASCII map.

    The ASCII map is a 17x17 character canvas. Each character represents 50
    map units, so street lines (multiples of 100) fall on even indices and the
    8x8 grid cells fall on odd indices. Symbols:
        '#' street, '.' empty cell, 'R' rider, 'S' restaurant,
        'C' customer, '*' route line segment.
    """

    CANVAS = 17
    STEP = 50

    @classmethod
    def point_to_cell(cls, x: int, y: int) -> Tuple[int, int]:
        """Convert a map coordinate to a ``(row, col)`` canvas index.

        Args:
            x: X coordinate (0-800).
            y: Y coordinate (0-800).

        Returns:
            Tuple ``(row, col)`` inside the canvas.
        """
        col = min(max(int(x) // cls.STEP, 0), cls.CANVAS - 1)
        row = min(max(int(y) // cls.STEP, 0), cls.CANVAS - 1)
        return row, col

    def render_map(
        self,
        riders: Iterable[Any] = (),
        orders: Iterable[Any] = (),
        route: Sequence[Tuple[int, int]] = (),
    ) -> str:
        """Render the ASCII map with riders, orders and an optional route.

        Args:
            riders: Riders to mark with 'R'.
            orders: Orders to mark with 'S' and 'C' (completed orders skipped).
            route: Sequence of positions drawn as connected '*' segments.

        Returns:
            The multi-line map string.
        """
        n = self.CANVAS
        canvas = [
            ["#" if (r % 2 == 0 or c % 2 == 0) else "." for c in range(n)]
            for r in range(n)
        ]

        cells = [self.point_to_cell(x, y) for x, y in route]
        for (r1, c1), (r2, c2) in zip(cells, cells[1:]):
            for r in range(min(r1, r2), max(r1, r2) + 1):
                for c in range(min(c1, c2), max(c1, c2) + 1):
                    canvas[r][c] = "*"

        for order in orders:
            if getattr(order, "status", "") == "completed":
                continue
            r, c = self.point_to_cell(*order.res_pos)
            canvas[r][c] = "S"
            r, c = self.point_to_cell(*order.cus_pos)
            canvas[r][c] = "C"

        for rider in riders:
            r, c = self.point_to_cell(rider.x, rider.y)
            canvas[r][c] = "R"

        lines = ["     x: 0 .. 800 (1 char = 50 units, streets every 100)"]
        for r in range(n):
            label = f"{r * self.STEP:>4} " if r % 2 == 0 else "     "
            lines.append(label + " ".join(canvas[r]))
        lines.append("Legend: R rider, S restaurant, C customer, "
                     "# street, . empty, * route")
        return "\n".join(lines)

    def render_status(self, funds: int, riders: Sequence[Any], pending_count: int) -> str:
        """Render the system status snapshot.

        Args:
            funds: Current system funds.
            riders: All riders.
            pending_count: Number of orders waiting for assignment.

        Returns:
            The multi-line status string.
        """
        lines = [
            "=== System Status ===",
            f"Funds: {funds}",
            f"Riders: {len(riders)}",
            f"Pending orders: {pending_count}",
        ]
        for rider in riders:
            order_ids = [o.id for o in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id} | position ({rider.x}, {rider.y}) | "
                f"{STATE_NAMES.get(rider.state, 'unknown')} | "
                f"orders: {len(rider.orders)} {order_ids}"
            )
        return "\n".join(lines)

    def render_orders(self, orders: Sequence[Any]) -> str:
        """Render a table of all orders.

        Args:
            orders: All orders in creation order.

        Returns:
            The multi-line table string.
        """
        if not orders:
            return "No orders yet."
        lines = ["=== Orders ==="]
        for o in orders:
            time_taken = "-" if o.time_taken is None else f"{o.time_taken} ticks"
            rider = "-" if o.rider_id is None else f"#{o.rider_id}"
            lines.append(
                f"Order #{o.id} | start tick {o.start_tick} | "
                f"restaurant {o.res_pos} | customer {o.cus_pos} | "
                f"distance {o.distance} | time {time_taken} | "
                f"rider {rider} | status {o.status}"
            )
        return "\n".join(lines)

    def render_rider_logs(self, riders: Sequence[Any]) -> str:
        """Render the status-change history of every rider.

        Args:
            riders: All riders.

        Returns:
            The multi-line log string.
        """
        if not riders:
            return "No riders."
        lines = ["=== Rider Records ==="]
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id}:")
            if not rider.log:
                lines.append("  (no records)")
            for entry in rider.log:
                order = "-" if entry.get("order_id") is None else f"#{entry['order_id']}"
                state = STATE_NAMES.get(entry.get("state", 0), "unknown")
                lines.append(
                    f"  tick {entry.get('tick', 0):>5} | {entry['event']:<22} | "
                    f"order {order:<6} | position ({entry.get('x')}, {entry.get('y')}) | "
                    f"state {state}"
                )
        return "\n".join(lines)
