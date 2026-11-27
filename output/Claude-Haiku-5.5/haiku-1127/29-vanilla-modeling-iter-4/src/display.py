"""Status displays and ASCII map visualisation.

The ASCII map is drawn on a 17x17 canvas. Even-indexed rows and columns are
street lines (``#``) and odd-indexed positions are cell centres, which hold
the restaurant (S), customer (C) and rider (R) symbols. Route lines are
drawn with ``*``.
"""

import math

from order_model import Order
from path_planner import (CELL_SIZE, GRID_CELLS, MAP_SIZE, cell_index_of)
from rider import STATE_NAMES

STEP = CELL_SIZE // 2
CANVAS = 2 * GRID_CELLS + 1


def _to_canvas(x, y):
    """Convert a map coordinate to canvas ``(column, row)``.

    Args:
        x: X coordinate.
        y: Y coordinate (row 0 is the top, y = 800).

    Returns:
        Tuple ``(col, row)`` clamped to the canvas.
    """
    col = min(max(int(round(x / STEP)), 0), CANVAS - 1)
    row = min(max(int(round((MAP_SIZE - y) / STEP)), 0), CANVAS - 1)
    return col, row


def _sample(start, end):
    """Return points sampled every ``STEP`` units along a segment.

    Args:
        start: Segment start ``(x, y)``.
        end: Segment end ``(x, y)``.

    Returns:
        List of ``(x, y)`` float points including both endpoints.
    """
    (x1, y1), (x2, y2) = start, end
    steps = max(1, int(math.ceil(max(abs(x2 - x1), abs(y2 - y1)) / STEP)))
    return [(x1 + (x2 - x1) * i / steps, y1 + (y2 - y1) * i / steps)
            for i in range(steps + 1)]


def _cell_canvas(x, y):
    """Return the canvas ``(col, row)`` of the cell centre containing a point.

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        Tuple ``(col, row)`` on the canvas.
    """
    gx, gy = cell_index_of(x, y)
    col = 2 * gx + 1
    row = 2 * (GRID_CELLS - 1 - gy) + 1
    return col, row


class DisplayManager:
    """Renders status, order tables, rider logs and the ASCII map.

    Attributes:
        system: The :class:`SystemManager` being displayed.
    """

    def __init__(self, system):
        """Create a display bound to a system manager.

        Args:
            system: The :class:`SystemManager` to render.
        """
        self.system = system

    def render_status(self):
        """Render funds, rider counts and per-rider details.

        Returns:
            Multi-line string.
        """
        snap = self.system.status_snapshot()
        lines = [
            f"Simulation tick: {snap['time']}",
            f"System funds: {snap['funds']}",
            f"Riders: {snap['rider_count']} (idle: {snap['idle']})",
            f"Pending orders: {snap['pending']}",
        ]
        riders = self.system.riders
        if not riders:
            lines.append("  No riders on duty.")
        for rider in riders:
            order_ids = ", ".join(f"#{o.id}" for o in rider.orders) or "none"
            lines.append(
                f"  Rider {rider.rider_id}: position ({rider.x}, {rider.y}), "
                f"status {rider.state_name}, orders {len(rider.orders)} "
                f"[{order_ids}]"
            )
        return "\n".join(lines)

    def render_orders(self):
        """Render a table of all orders.

        Returns:
            Multi-line string.
        """
        orders = self.system.order_manager.orders
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} "
                  f"{'Customer':>12} {'Distance':>9} {'Taken':>6} "
                  f"{'Rider':>6} {'Status':>11}")
        lines = [header, "-" * len(header)]
        for order in orders:
            restaurant = f"({order.restaurant_x},{order.restaurant_y})"
            customer = f"({order.customer_x},{order.customer_y})"
            taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else str(order.rider_id)
            lines.append(
                f"{order.id:>4} {order.start_time:>6} {restaurant:>12} "
                f"{customer:>12} {order.distance:>9.1f} {taken:>6} "
                f"{rider:>6} {order.status:>11}"
            )
        return "\n".join(lines)

    def render_rider_log(self):
        """Render the status-change history of every rider.

        Returns:
            Multi-line string.
        """
        riders = self.system.riders
        if not riders:
            return "No riders on duty."
        lines = []
        for rider in riders:
            lines.append(f"Rider {rider.rider_id}:")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order_text = ("-" if entry["order_id"] is None
                              else f"#{entry['order_id']}")
                state = STATE_NAMES.get(entry["state"], "unknown")
                lines.append(
                    f"  t={entry['time']:>4}  {entry['event']:<22} "
                    f"order={order_text:<5} pos=({entry['x']},{entry['y']}) "
                    f"state={state}"
                )
        return "\n".join(lines)

    def render_map(self, segments=None):
        """Render the ASCII map with riders, orders and an optional route.

        Args:
            segments: Optional list of ``((x1, y1), (x2, y2))`` route
                segments drawn with ``*``.

        Returns:
            Multi-line string.
        """
        canvas = [[("#" if (r % 2 == 0 or c % 2 == 0) else ".")
                   for c in range(CANVAS)] for r in range(CANVAS)]

        for start, end in segments or []:
            for px, py in _sample(start, end):
                col, row = _to_canvas(px, py)
                canvas[row][col] = "*"

        def place(x, y, symbol):
            col, row = _cell_canvas(x, y)
            canvas[row][col] = symbol

        for order in self.system.order_manager.active_orders():
            place(order.restaurant_x, order.restaurant_y, "S")
            place(order.customer_x, order.customer_y, "C")
        for rider in self.system.riders:
            place(rider.x, rider.y, "R")

        lines = ["Legend: R rider  S restaurant  C customer  "
                 "# street  . block  * route"]
        header = " " * 5
        labels = [" "] * (2 * CANVAS)
        for gx in range(GRID_CELLS):
            text = str(gx * CELL_SIZE + CELL_SIZE // 2)
            pos = 2 * (2 * gx + 1)
            for i, ch in enumerate(text):
                labels[pos + i] = ch
        lines.append(header + "".join(labels).rstrip())
        for r in range(CANVAS):
            if r % 2 == 1:
                gy = GRID_CELLS - 1 - (r - 1) // 2
                prefix = f"{gy * CELL_SIZE + CELL_SIZE // 2:>4} "
            else:
                prefix = " " * 5
            lines.append(prefix + " ".join(canvas[r]))
        return "\n".join(lines)
