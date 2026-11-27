"""Status displays and ASCII map rendering.

Map legend:
    R rider, S restaurant, C customer, # street, . empty space, * route.

The map is drawn at 50-unit resolution so that cell centers (e.g. 150) and
street lines (e.g. 200) both land on distinct characters. The y axis points
upwards.
"""

from typing import List, Optional, Sequence, Tuple

from grid import MAP_SIZE
from order_model import Order, STATUS_COMPLETED
from rider import STATE_NAMES, Rider

CANVAS_STEP = 50
CANVAS_MAX = MAP_SIZE // CANVAS_STEP  # 16
CANVAS_SIZE = CANVAS_MAX + 1
LEGEND = "Legend: R rider, S restaurant, C customer, # street, . empty, * route"


def _axis_samples(a: int, b: int, step: int = 10) -> List[int]:
    """Return sample coordinates between ``a`` and ``b`` inclusive.

    Args:
        a: First coordinate.
        b: Second coordinate.
        step: Sampling distance.

    Returns:
        Sorted list of sample values.
    """
    lo, hi = sorted((a, b))
    values = list(range(lo, hi + 1, step))
    if not values or values[-1] != hi:
        values.append(hi)
    return values


def _segment_points(a: Tuple[int, int], b: Tuple[int, int]) -> List[Tuple[int, int]]:
    """Sample a Manhattan path from ``a`` to ``b`` (horizontal then vertical).

    Args:
        a: Start point.
        b: End point.

    Returns:
        Sampled points along the path.
    """
    (x0, y0), (x1, y1) = a, b
    points = [(x, y0) for x in _axis_samples(x0, x1)]
    points.extend((x1, y) for y in _axis_samples(y0, y1))
    return points


def _to_cell(x: int, y: int) -> Tuple[int, int]:
    """Convert a map coordinate to canvas (row, column).

    Args:
        x: Map X coordinate.
        y: Map Y coordinate.

    Returns:
        Tuple ``(row, col)`` where row 0 is the top of the map.
    """
    col = min(max(x, 0) // CANVAS_STEP, CANVAS_MAX)
    row = CANVAS_MAX - min(max(y, 0) // CANVAS_STEP, CANVAS_MAX)
    return row, col


class DisplayManager:
    """Renders status text, order tables, rider logs and the ASCII map.

    Attributes:
        system: The SystemManager whose state is displayed.
    """

    def __init__(self, system) -> None:
        """Create a display bound to a system manager.

        Args:
            system: SystemManager instance.
        """
        self.system = system

    def render_status(self) -> str:
        """Build the status snapshot text.

        Returns:
            Multi-line status report.
        """
        riders = self.system.riders
        lines = [
            f"System funds: {self.system.funds}",
            f"Current tick: {self.system.current_tick}",
            f"Riders: {len(riders)} (idle: {self.system.idle_rider_count()})",
            f"Pending orders: {self.system.order_manager.pending_count}",
        ]
        for rider in riders:
            order_ids = ", ".join(str(o.id) for o in rider.orders) or "none"
            lines.append(
                f"  Rider #{rider.rider_id}: position ({rider.x}, {rider.y}) | "
                f"status: {STATE_NAMES[rider.state]} | speed: {rider.speed} | "
                f"orders: {len(rider.orders)} [{order_ids}]"
            )
        return "\n".join(lines)

    def render_orders(self) -> str:
        """Build the order table.

        Returns:
            Formatted table of all orders.
        """
        orders = self.system.order_manager.all_orders
        if not orders:
            return "No orders yet."
        header = (
            f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
            f"{'Distance':>9} {'Time':>6} {'Rider':>6} {'Status':>10}"
        )
        lines = [header, "-" * len(header)]
        for order in orders:
            rider = "-" if order.rider_id is None else str(order.rider_id)
            time_taken = "-" if order.time_taken is None else str(order.time_taken)
            lines.append(
                f"{order.id:>4} {order.start_time:>6} "
                f"{str((order.restaurant_x, order.restaurant_y)):>12} "
                f"{str((order.customer_x, order.customer_y)):>12} "
                f"{order.distance:>9.2f} {time_taken:>6} {rider:>6} {order.status:>10}"
            )
        return "\n".join(lines)

    def render_rider_log(self) -> str:
        """Build the status-change history for every rider.

        Returns:
            Multi-line history text.
        """
        lines: List[str] = []
        for rider in self.system.riders:
            lines.append(f"Rider #{rider.rider_id}:")
            if not rider.log:
                lines.append("  (no records)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else str(entry["order_id"])
                lines.append(
                    f"  tick {entry['tick']:>5} | {entry['event']:<22} | order {order:>4} | "
                    f"pos ({entry['x']}, {entry['y']}) | state {STATE_NAMES[entry['state']]}"
                )
        return "\n".join(lines) if lines else "No riders yet."

    def render_map(self, trail: Optional[Sequence[Tuple[int, int]]] = None) -> str:
        """Render the ASCII map.

        Args:
            trail: Optional route points drawn as '*'.

        Returns:
            Multi-line map text including legend.
        """
        canvas = self._blank_canvas()
        if trail:
            self._draw_route(canvas, trail)
        for order in self.system.order_manager.active_orders():
            self._place(canvas, order.restaurant_x, order.restaurant_y, "S")
            self._place(canvas, order.customer_x, order.customer_y, "C")
        for rider in self.system.riders:
            self._place(canvas, rider.x, rider.y, "R")
        return self._frame(canvas) + "\n" + LEGEND

    def render_route_map(
        self,
        order: Order,
        trail: Sequence[Tuple[int, int]],
        rider: Optional[Rider],
        new_rider_added: int,
    ) -> str:
        """Render the summary shown after an order is accepted and completed.

        Args:
            order: The order that was processed.
            trail: Route points visited by the assigned rider.
            rider: The assigned rider, if any.
            new_rider_added: Number of riders recruited for this order.

        Returns:
            Multi-line summary including the route map.
        """
        lines = [
            f"Order #{order.id} processed.",
            f"Restaurant grid point: ({order.restaurant_x}, {order.restaurant_y})",
            f"Customer grid point: ({order.customer_x}, {order.customer_y})",
            f"New rider added: {'yes (' + str(new_rider_added) + ')' if new_rider_added else 'no'}",
        ]
        if rider is not None:
            lines.append(
                f"Assigned rider: #{rider.rider_id} | speed: {rider.speed} units/tick"
            )
        lines.append(
            f"Distance: {order.distance:.2f} | time taken: "
            f"{order.time_taken if order.time_taken is not None else '-'} ticks"
        )
        lines.append(self.render_map(trail))
        return "\n".join(lines)

    def _blank_canvas(self) -> List[List[str]]:
        """Create the base canvas with streets and empty cells.

        Returns:
            2-D list of characters.
        """
        canvas: List[List[str]] = []
        for row in range(CANVAS_SIZE):
            y = (CANVAS_MAX - row) * CANVAS_STEP
            line = []
            for col in range(CANVAS_SIZE):
                x = col * CANVAS_STEP
                line.append("#" if x % 100 == 0 or y % 100 == 0 else ".")
            canvas.append(line)
        return canvas

    def _draw_route(self, canvas: List[List[str]], trail: Sequence[Tuple[int, int]]) -> None:
        """Draw connected route segments onto the canvas.

        Args:
            canvas: Canvas to modify in place.
            trail: Ordered route points.
        """
        points: List[Tuple[int, int]] = [trail[0]]
        for prev, cur in zip(trail, trail[1:]):
            points.extend(_segment_points(prev, cur))
        for x, y in points:
            row, col = _to_cell(x, y)
            if canvas[row][col] in ".#":
                canvas[row][col] = "*"

    def _place(self, canvas: List[List[str]], x: int, y: int, symbol: str) -> None:
        """Place a marker symbol at a map coordinate.

        Args:
            canvas: Canvas to modify.
            x: Map X coordinate.
            y: Map Y coordinate.
            symbol: Single-character marker.
        """
        row, col = _to_cell(x, y)
        canvas[row][col] = symbol

    def _frame(self, canvas: List[List[str]]) -> str:
        """Add row labels and axis notes to the canvas.

        Args:
            canvas: Completed canvas.

        Returns:
            Printable map text.
        """
        lines = []
        for row, chars in enumerate(canvas):
            y = (CANVAS_MAX - row) * CANVAS_STEP
            label = f"{y:>4}" if y % 100 == 0 else "    "
            lines.append(f"{label} |{''.join(chars)}|")
        lines.append("     x: 0 (left) .. 800 (right), y: 0 (bottom) .. 800 (top)")
        return "\n".join(lines)
