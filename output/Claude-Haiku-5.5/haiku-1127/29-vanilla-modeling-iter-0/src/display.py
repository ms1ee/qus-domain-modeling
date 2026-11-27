"""Status display and ASCII map visualisation."""

from typing import Iterable, List, Optional, Sequence, Tuple

from path_planner import GridMap
from rider import STATE_LABELS

Point = Tuple[int, int]


class DisplayManager:
    """Formats system status, order tables, rider logs and the ASCII map.

    The ASCII map uses a 17x17 character canvas for the 8x8 grid: street
    lines are drawn with '#' at even indices, grid-cell centers (where
    restaurants, customers and riders stand) lie at odd indices.
    Symbols: 'R' rider, 'S' restaurant, 'C' customer, '.' empty,
    '#' street, '*' route.
    """

    def __init__(self, grid_map: Optional[GridMap] = None) -> None:
        """Create a display bound to a grid map.

        Args:
            grid_map: Map description; an 800x800 map is used if None.
        """
        self.grid_map = grid_map or GridMap()

    def to_canvas(self, x: int, y: int) -> Tuple[int, int]:
        """Convert world coordinates to (column, row) on the ASCII canvas.

        Row 0 is the top of the map (largest y).
        """
        half = self.grid_map.cell_size // 2
        max_index = self.grid_map.cells_per_side * 2
        col = min(max(x // half, 0), max_index)
        row = min(max((self.grid_map.height - y) // half, 0), max_index)
        return col, row

    def render_status(self, funds: int, sim_time: int, riders: Sequence) -> str:
        """Return a snapshot of funds, time and every rider's state.

        Args:
            funds: Current system funds.
            sim_time: Current simulated tick.
            riders: Sequence of Rider objects.

        Returns:
            Multi-line status text.
        """
        lines = [
            f"System funds: {funds}",
            f"Simulated time: {sim_time}",
            f"Riders: {len(riders)}",
        ]
        if not riders:
            lines.append("  (no riders recruited yet)")
        for rider in riders:
            order_ids = ", ".join(str(o.id) for o in rider.orders) or "-"
            lines.append(
                f"  Rider #{rider.rider_id}: location=({rider.x}, {rider.y}) "
                f"status={rider.state_label} orders={len(rider.orders)} "
                f"[{order_ids}]")
        return "\n".join(lines)

    def render_orders(self, orders: Iterable) -> str:
        """Return a table with details of every order.

        Columns: ID, start time, restaurant, customer, distance, time taken,
        assigned rider and status.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} | {'Start':>5} | {'Restaurant':>12} | "
                  f"{'Customer':>12} | {'Distance':>8} | {'Taken':>5} | "
                  f"{'Rider':>5} | Status")
        lines = [header, "-" * len(header)]
        for order in orders:
            restaurant = f"({order.restaurant_x},{order.restaurant_y})"
            customer = f"({order.customer_x},{order.customer_y})"
            taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else f"#{order.rider_id}"
            lines.append(
                f"{order.id:>4} | {order.start_time:>5} | {restaurant:>12} | "
                f"{customer:>12} | {order.distance:>8.0f} | {taken:>5} | "
                f"{rider:>5} | {order.status}")
        return "\n".join(lines)

    def render_rider_logs(self, riders: Sequence) -> str:
        """Return every recorded status change for all riders."""
        lines: List[str] = []
        for rider in riders:
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else entry["order_id"]
                state = STATE_LABELS.get(entry["state"], "unknown")
                lines.append(
                    f"t={entry['time']:>4} rider#{rider.rider_id:<3} "
                    f"{entry['event']:<22} order={order:<4} "
                    f"at ({entry['x']},{entry['y']}) state={state}")
        return "\n".join(lines) if lines else "No rider events recorded."

    def _draw_segment(self, canvas: List[List[str]], start: Point,
                      end: Point) -> None:
        """Draw a route segment between two canvas cells with '*'."""
        dc = (end[0] > start[0]) - (end[0] < start[0])
        dr = (end[1] > start[1]) - (end[1] < start[1])
        col, row = start
        self._mark(canvas, col, row)
        while (col, row) != end:
            if col != end[0]:
                col += dc
            else:
                row += dr
            self._mark(canvas, col, row)

    @staticmethod
    def _mark(canvas: List[List[str]], col: int, row: int) -> None:
        """Set a route symbol unless a marker already occupies the cell."""
        if canvas[row][col] not in "SCR":
            canvas[row][col] = "*"

    def render_map(self, riders: Sequence = (), orders: Sequence = (),
                   route: Optional[Sequence[Point]] = None) -> str:
        """Return the ASCII map with riders, orders and an optional route.

        Args:
            riders: Riders to mark with 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') are
                shown while they are not completed.
            route: Optional sequence of (x, y) points drawn as connected
                line segments with '*'.

        Returns:
            Multi-line string including a legend and active order list.
        """
        size = self.grid_map.cells_per_side * 2 + 1
        canvas = [["#" if (c % 2 == 0 or r % 2 == 0) else "."
                   for c in range(size)] for r in range(size)]

        if route:
            previous = None
            for x, y in route:
                current = self.to_canvas(x, y)
                if previous is not None and previous != current:
                    self._draw_segment(canvas, previous, current)
                previous = current

        active = [o for o in orders if o.status != "completed"]
        for order in active:
            col, row = self.to_canvas(order.restaurant_x, order.restaurant_y)
            canvas[row][col] = "S"
            col, row = self.to_canvas(order.customer_x, order.customer_y)
            canvas[row][col] = "C"
        for rider in riders:
            col, row = self.to_canvas(rider.x, rider.y)
            canvas[row][col] = "R"

        lines = ["".join(row) for row in canvas]
        lines.append("")
        lines.append("Legend: R=rider S=restaurant C=customer "
                     ". =empty #=street *=route")
        if active:
            lines.append("Active orders:")
            for order in active:
                lines.append(
                    f"  Order #{order.id}: status={order.status} "
                    f"restaurant=({order.restaurant_x},{order.restaurant_y}) "
                    f"customer=({order.customer_x},{order.customer_y}) "
                    f"rider={'-' if order.rider_id is None else order.rider_id}")
        else:
            lines.append("No active orders.")
        return "\n".join(lines)
