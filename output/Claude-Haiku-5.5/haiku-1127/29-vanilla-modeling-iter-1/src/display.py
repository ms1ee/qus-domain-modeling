"""Text display: ASCII map, status, order and rider reports.

Map legend:
    '#' street (grid line), '.' empty space, 'S' restaurant, 'C' customer,
    'R' rider, '*' route. Each canvas character spans 50 units, so grid cell
    centres (x = 150, 250, ...) fall on odd indices and streets on even ones.
"""

from typing import Any, Iterable, List, Sequence, Tuple

from path_planner import CELL_SIZE, MAP_SIZE

Point = Tuple[int, int]
CANVAS_UNIT = CELL_SIZE // 2


class DisplayManager:
    """Builds human-readable text for the command line interface.

    Attributes:
        map_symbols: Mapping from element name to its ASCII symbol.
    """

    def __init__(self) -> None:
        """Create the display manager with the standard symbol set."""
        self.map_symbols = {
            "rider": "R",
            "restaurant": "S",
            "customer": "C",
            "empty": ".",
            "street": "#",
            "route": "*",
        }

    def _index(self, value: int) -> int:
        """Convert a coordinate to a canvas index."""
        return min(max(int(value) // CANVAS_UNIT, 0), MAP_SIZE // CANVAS_UNIT)

    def render_map(self, riders: Iterable[Any] = (), orders: Iterable[Any] = (),
                   route: Sequence[Point] = ()) -> str:
        """Render the 8x8 grid as ASCII art.

        Args:
            riders: Riders to draw.
            orders: Orders whose restaurant and customer points are drawn
                (completed orders are hidden).
            route: Route points drawn as connected '*' marks.

        Returns:
            The multi-line map string.
        """
        size = MAP_SIZE // CANVAS_UNIT + 1
        canvas: List[List[str]] = []
        for row in range(size):
            y = row * CANVAS_UNIT
            line = []
            for col in range(size):
                x = col * CANVAS_UNIT
                on_street = x % CELL_SIZE == 0 or y % CELL_SIZE == 0
                line.append(self.map_symbols["street" if on_street else "empty"])
            canvas.append(line)

        def put(x: int, y: int, key: str) -> None:
            canvas[self._index(y)][self._index(x)] = self.map_symbols[key]

        for x, y in route:
            put(x, y, "route")
        for order in orders:
            if order.status == "completed":
                continue
            put(order.restaurant_x, order.restaurant_y, "restaurant")
            put(order.customer_x, order.customer_y, "customer")
        for rider in riders:
            put(rider.x, rider.y, "rider")

        lines = [
            "Map (1 char = 50 units): # street  . empty  S restaurant  "
            "C customer  R rider  * route",
        ]
        for row, cells in enumerate(canvas):
            lines.append(f"{row * CANVAS_UNIT:>4} " + "".join(cells))
        lines.append(f"     x: 0 -> {MAP_SIZE} (left to right), "
                     f"y: 0 -> {MAP_SIZE} (top to bottom)")
        return "\n".join(lines)

    def format_status(self, funds: int, riders: Sequence[Any], pending: int = 0) -> str:
        """Format the system snapshot shown by the 'status' command.

        Args:
            funds: Current system funds.
            riders: All riders.
            pending: Number of orders waiting for a rider.

        Returns:
            Multi-line status text.
        """
        lines = [
            f"System funds: {funds}",
            f"Riders: {len(riders)}",
            f"Pending orders: {pending}",
        ]
        if not riders:
            lines.append("  (no riders yet)")
        for rider in riders:
            order_ids = [order.id for order in rider.orders]
            lines.append(
                f"  Rider {rider.rider_id}: position ({rider.x}, {rider.y}), "
                f"status {rider.state_name}, speed {rider.speed}, "
                f"orders {len(rider.orders)} {order_ids}"
            )
        return "\n".join(lines)

    def format_orders(self, orders: Sequence[Any]) -> str:
        """Format a table of all orders.

        Args:
            orders: Order history.

        Returns:
            Multi-line table text.
        """
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':<14} {'Customer':<14} "
                  f"{'Distance':>9} {'Time':>6} {'Rider':>6} {'Status':<10}")
        lines = [header, "-" * len(header)]
        for order in orders:
            restaurant = f"({order.restaurant_x},{order.restaurant_y})"
            customer = f"({order.customer_x},{order.customer_y})"
            time_text = "-" if order.time_taken is None else str(order.time_taken)
            rider_text = "-" if order.rider_id is None else str(order.rider_id)
            lines.append(
                f"{order.id:>4} {order.start_time:>6} {restaurant:<14} {customer:<14} "
                f"{order.distance:>9.1f} {time_text:>6} {rider_text:>6} {order.status:<10}"
            )
        return "\n".join(lines)

    def format_rider_logs(self, riders: Sequence[Any]) -> str:
        """Format the status change history of every rider.

        Args:
            riders: All riders.

        Returns:
            Multi-line log text.
        """
        if not riders:
            return "No riders yet."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider {rider.rider_id} (current: {rider.state_name}, "
                         f"travelled {rider.distance_travelled} units):")
            for entry in rider.log:
                order_text = "-" if entry["order_id"] is None else str(entry["order_id"])
                lines.append(
                    f"  t={entry['tick']:>4}  {entry['event']:<22} order={order_text:<5} "
                    f"pos=({entry['x']},{entry['y']})"
                )
        return "\n".join(lines)
