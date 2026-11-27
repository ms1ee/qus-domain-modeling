"""Status text and ASCII map rendering."""

from typing import Any, Iterable, List, Optional, Sequence, Tuple

from rider import STATE_NAMES

Point = Tuple[int, int]


class DisplayManager:
    """Formats the simulator state for the command line.

    The ASCII map samples the 800x800 unit map every 50 units, producing a
    17x17 character canvas. Intersections of the 8x8 cell grid are drawn at
    even positions, so streets appear as continuous lines of '#'.

    Attributes:
        map_size: Size of the map in units.
        resolution: Units represented by one character.
        symbol_rider: Symbol for riders ('R').
        symbol_restaurant: Symbol for restaurants ('S').
        symbol_customer: Symbol for customers ('C').
        symbol_empty: Symbol for off-street empty space ('.').
        symbol_street: Symbol for streets ('#').
        symbol_route: Symbol for a planned route ('*').
    """

    def __init__(self, map_size: int = 800, cell_size: int = 100,
                 resolution: int = 50) -> None:
        """Configure the renderer.

        Args:
            map_size: Map size in units.
            cell_size: Grid cell size in units.
            resolution: Units per character.
        """
        self.map_size = map_size
        self.cell_size = cell_size
        self.resolution = resolution
        self.symbol_rider = "R"
        self.symbol_restaurant = "S"
        self.symbol_customer = "C"
        self.symbol_empty = "."
        self.symbol_street = "#"
        self.symbol_route = "*"

    def render_status(self, funds: int, riders: Sequence[Any]) -> str:
        """Render the system snapshot: funds and each rider's details.

        Args:
            funds: Current system funds.
            riders: Riders to describe.

        Returns:
            Multi-line status text.
        """
        lines = [
            "=== System Status ===",
            f"System funds: {funds}",
            f"Rider count: {len(riders)}",
        ]
        for rider in riders:
            order_ids = [o.id for o in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id}: location ({rider.x}, {rider.y}) | "
                f"status: {STATE_NAMES.get(rider.state, 'unknown')} | "
                f"active orders: {rider.active_order_count()} | "
                f"order list: {order_ids if order_ids else 'none'}"
            )
        return "\n".join(lines)

    def render_orders(self, orders: Sequence[Any]) -> str:
        """Render a table of all orders.

        Args:
            orders: Orders to display.

        Returns:
            Multi-line table text.
        """
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Dist':>7} {'Taken':>6} {'Rider':>6} {'Status':>10}")
        lines = ["=== Orders ===", header, "-" * len(header)]
        for o in orders:
            rest = f"({o.restaurant_x},{o.restaurant_y})"
            cust = f"({o.customer_x},{o.customer_y})"
            taken = "-" if o.time_taken is None else str(o.time_taken)
            rider = "-" if o.rider_id is None else str(o.rider_id)
            lines.append(
                f"{o.id:>4} {o.start_time:>6} {rest:>12} {cust:>12} "
                f"{o.distance:>7.0f} {taken:>6} {rider:>6} {o.status:>10}"
            )
        return "\n".join(lines)

    def render_rider_log(self, riders: Sequence[Any]) -> str:
        """Render every recorded status change for all riders.

        Args:
            riders: Riders whose logs should be shown.

        Returns:
            Multi-line log text.
        """
        if not riders:
            return "No riders."
        lines = ["=== Rider Event Log ==="]
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id}:")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                lines.append(
                    f"  tick {entry['tick']:>4} | {entry['event']:<20} | "
                    f"order {order:>5} | pos ({entry['x']}, {entry['y']}) | "
                    f"state {STATE_NAMES.get(entry['state'], 'unknown')}"
                )
        return "\n".join(lines)

    def render_map(self, riders: Iterable[Any] = (), orders: Iterable[Any] = (),
                   route: Optional[List[Point]] = None) -> str:
        """Render the ASCII map with riders, orders and an optional route.

        Args:
            riders: Riders to mark with 'R'.
            orders: Orders whose restaurants ('S') and customers ('C') are marked.
            route: Optional polyline drawn with '*'.

        Returns:
            Multi-line map text.
        """
        steps = self.map_size // self.resolution
        size = steps + 1
        canvas = [[self.symbol_empty] * size for _ in range(size)]

        for row in range(size):
            y = (steps - row) * self.resolution
            for col in range(size):
                x = col * self.resolution
                if x % self.cell_size == 0 or y % self.cell_size == 0:
                    canvas[row][col] = self.symbol_street

        if route:
            for a, b in zip(route, route[1:]):
                for px, py in self._segment_points(a, b):
                    self._plot(canvas, px, py, self.symbol_route)
            if len(route) == 1:
                self._plot(canvas, route[0][0], route[0][1], self.symbol_route)

        for order in orders:
            self._plot(canvas, order.restaurant_x, order.restaurant_y,
                       self.symbol_restaurant)
            self._plot(canvas, order.customer_x, order.customer_y,
                       self.symbol_customer)

        for rider in riders:
            self._plot(canvas, rider.x, rider.y, self.symbol_rider)

        lines = ["=== Map (y=800 at top, x=0 at left) ==="]
        for row in range(size):
            y = (steps - row) * self.resolution
            label = f"{y:>4}" if y % 200 == 0 else "    "
            lines.append(label + " " + " ".join(canvas[row]))
        axis = "     " + " ".join(
            f"{x:<1}" if (i % 4 == 0) else " " for i, x in enumerate(range(size)))
        lines.append("     x: 0 ... 800 (ticks every 200 units)")
        lines.append(
            f"Legend: {self.symbol_rider}=rider {self.symbol_restaurant}=restaurant "
            f"{self.symbol_customer}=customer {self.symbol_street}=street "
            f"{self.symbol_empty}=empty {self.symbol_route}=route"
        )
        return "\n".join(lines)

    def _plot(self, canvas: List[List[str]], x: int, y: int, symbol: str) -> None:
        """Place ``symbol`` on the canvas at the sampled location of (x, y)."""
        steps = self.map_size // self.resolution
        col = int(round(x / self.resolution))
        row = steps - int(round(y / self.resolution))
        if 0 <= row <= steps and 0 <= col <= steps:
            canvas[row][col] = symbol

    def _segment_points(self, a: Point, b: Point) -> List[Point]:
        """Return sampled points along a straight segment from a to b."""
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        length = max(abs(dx), abs(dy))
        count = length // self.resolution
        sx = (dx > 0) - (dx < 0)
        sy = (dy > 0) - (dy < 0)
        return [(ax + sx * self.resolution * i, ay + sy * self.resolution * i)
                for i in range(count + 1)]
