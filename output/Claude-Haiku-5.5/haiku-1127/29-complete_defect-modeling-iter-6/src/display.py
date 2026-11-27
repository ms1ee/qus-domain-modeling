"""Status display and ASCII map rendering.

The map is drawn on a 17x17 character canvas. Each character represents
50 units, so cell centres (50 + 100k) fall on odd indices and street lines
(multiples of 100) fall on even indices. Symbols:
    R rider, S restaurant, C customer, . empty cell centre,
    # street, * planned route.
"""

from typing import Iterable, List, Optional, Sequence, Tuple

from grid import CELL_SIZE, GRID_DIMENSION
from order_model import Order
from rider import STATE_NAMES

SYMBOL_RIDER = "R"
SYMBOL_RESTAURANT = "S"
SYMBOL_CUSTOMER = "C"
SYMBOL_EMPTY = "."
SYMBOL_STREET = "#"
SYMBOL_ROUTE = "*"

STEP = CELL_SIZE // 2
LEGEND = ("Legend: R rider, S restaurant, C customer, . cell centre, "
          "# street, * route (1 char = 50 units)")


class DisplayManager:
    """Formats status information and renders the ASCII map.

    Attributes:
        map_width: Canvas width in characters.
        map_height: Canvas height in characters.
    """

    def __init__(self) -> None:
        """Create the display manager with the 17x17 canvas size."""
        self.map_width = GRID_DIMENSION * 2 + 1
        self.map_height = self.map_width

    def _index(self, value: int) -> int:
        """Convert a coordinate to a canvas index (clamped)."""
        index = (int(value) + STEP // 2) // STEP
        return min(max(index, 0), self.map_width - 1)

    def _point(self, point: Tuple[int, int]) -> Tuple[int, int]:
        """Convert an (x, y) point to a canvas (column, row) pair."""
        return self._index(point[0]), self._index(point[1])

    def render_map(self, riders: Iterable = (),
                   orders: Sequence[Order] = (),
                   route: Optional[Sequence[Tuple[int, int]]] = None) -> str:
        """Render the ASCII map.

        Args:
            riders: Riders to mark with 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') are
                marked.
            route: Route points drawn as connected line segments with '*'.

        Returns:
            The multi-line map string.
        """
        width, height = self.map_width, self.map_height
        canvas: List[List[str]] = []
        for row in range(height):
            line = []
            for col in range(width):
                if col % 2 == 1 and row % 2 == 1:
                    line.append(SYMBOL_EMPTY)
                else:
                    line.append(SYMBOL_STREET)
            canvas.append(line)

        if route:
            points = [self._point(p) for p in route]
            for (c0, r0), (c1, r1) in zip(points, points[1:]):
                for col in range(min(c0, c1), max(c0, c1) + 1):
                    self._mark(canvas, col, r0, SYMBOL_ROUTE)
                for row in range(min(r0, r1), max(r0, r1) + 1):
                    self._mark(canvas, c1, row, SYMBOL_ROUTE)

        for order in orders:
            if order.status == Order.COMPLETED:
                continue
            col, row = self._point(order.restaurant_pos)
            canvas[row][col] = SYMBOL_RESTAURANT
            col, row = self._point(order.customer_pos)
            canvas[row][col] = SYMBOL_CUSTOMER

        for rider in riders:
            col, row = self._point(rider.position)
            canvas[row][col] = SYMBOL_RIDER

        return "\n".join("".join(line) for line in canvas)

    @staticmethod
    def _mark(canvas: List[List[str]], col: int, row: int,
              symbol: str) -> None:
        """Draw a route symbol without overwriting entity symbols."""
        if canvas[row][col] in (SYMBOL_EMPTY, SYMBOL_STREET):
            canvas[row][col] = symbol

    @staticmethod
    def legend() -> str:
        """Return the map legend text."""
        return LEGEND

    def format_status(self, system, riders: Sequence) -> str:
        """Return the system snapshot: funds, riders and their orders.

        Args:
            system: The SystemManager.
            riders: Riders to list.

        Returns:
            Multi-line status text.
        """
        pending = len(system.order_manager.pending)
        lines = [
            f"Simulated tick : {system.current_tick}",
            f"System funds   : {system.funds}",
            f"Riders         : {len(riders)}",
            f"Pending orders : {pending}",
        ]
        for rider in riders:
            state = STATE_NAMES.get(rider.state, "unknown")
            order_text = ", ".join(
                f"#{o.id}({o.status})" for o in rider.orders) or "-"
            lines.append(
                f"  Rider #{rider.rider_id} [{state}] at "
                f"({rider.x}, {rider.y}) speed {rider.speed} "
                f"orders: {order_text}")
        return "\n".join(lines)

    def format_orders(self, orders: Sequence[Order]) -> str:
        """Return a table of order details.

        Args:
            orders: Orders to list.

        Returns:
            Multi-line table text.
        """
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} "
                  f"{'Customer':>12} {'Dist':>8} {'Ticks':>6} "
                  f"{'Eff':>6} {'Rider':>6} {'Status':<10}")
        lines = [header, "-" * len(header)]
        for o in orders:
            rest = f"({o.restaurant_x},{o.restaurant_y})"
            cust = f"({o.customer_x},{o.customer_y})"
            ticks = "-" if o.time_taken is None else str(o.time_taken)
            rider = "-" if o.rider_id is None else f"#{o.rider_id}"
            lines.append(
                f"{o.id:>4} {o.start_time:>6} {rest:>12} {cust:>12} "
                f"{o.distance:>8.1f} {ticks:>6} {o.efficiency:>6.2f} "
                f"{rider:>6} {o.status:<10}")
        return "\n".join(lines)

    def format_riders(self, riders: Sequence) -> str:
        """Return the status-change history of every rider.

        Args:
            riders: Riders whose logs are listed.

        Returns:
            Multi-line log text.
        """
        if not riders:
            return "No riders recruited yet."
        lines: List[str] = []
        for rider in riders:
            state = STATE_NAMES.get(rider.state, "unknown")
            lines.append(f"Rider #{rider.rider_id} (now {state}, "
                         f"position ({rider.x}, {rider.y}))")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None \
                    else f"#{entry['order_id']}"
                lines.append(
                    f"  [tick {entry['tick']:>5}] {entry['event']:<22} "
                    f"order {order:<6} pos ({entry['x']}, {entry['y']})")
        return "\n".join(lines)

    def format_start_result(self, order: Order, rider, new_rider) -> str:
        """Return the summary printed after the start command.

        Args:
            order: The created order.
            rider: The assigned rider, or None if still pending.
            new_rider: A rider recruited for this order, or None.

        Returns:
            Multi-line summary text.
        """
        rgx, rgy = order.restaurant_cell()
        cgx, cgy = order.customer_cell()
        rx, ry = order.restaurant_pos
        cx, cy = order.customer_pos
        recruited = (f"yes (#{new_rider.rider_id})" if new_rider
                     else "no")
        lines = [
            f"=== Order #{order.id} ===",
            f"Restaurant grid: ({rgx}, {rgy})  centre: ({rx}, {ry})",
            f"Customer grid:   ({cgx}, {cgy})  centre: ({cx}, {cy})",
            f"New rider added: {recruited}",
        ]
        if rider is not None:
            lines.append(f"Assigned rider: #{rider.rider_id} "
                         f"(speed {rider.speed} units/tick)")
        else:
            lines.append("Assigned rider: none available (order pending)")
        if order.status == Order.COMPLETED:
            lines.append(
                f"Completed at tick {order.completion_time}; "
                f"time taken {order.time_taken} ticks; "
                f"distance {order.distance:.1f} units")
        else:
            lines.append(f"Status: {order.status}")
        return "\n".join(lines)
