"""Status display and ASCII map rendering."""

from __future__ import annotations

from typing import Any, Iterable, List, Optional, Sequence, Tuple

from path_planner import CELL_SIZE, MAP_SIZE

Point = Tuple[int, int]


class DisplayManager:
    """Builds text output for the status, order, rider and map views.

    The ASCII map uses one character per 50 units, so the 8x8 cell grid is
    drawn on a 17x17 canvas: even indices are streets (grid lines), odd
    indices are cell centres.  Restaurants are cell centres (``S``) and
    customers are cell centres (``C``).
    """

    STREET = "#"
    EMPTY = "."
    RIDER = "R"
    RESTAURANT = "S"
    CUSTOMER = "C"
    ROUTE = "*"
    UNITS_PER_CHAR = CELL_SIZE // 2
    CANVAS_SIZE = 2 * (MAP_SIZE // CELL_SIZE) + 1

    @classmethod
    def to_canvas(cls, value: float) -> int:
        """Convert a map coordinate to a canvas index."""
        index = int(round(value / cls.UNITS_PER_CHAR))
        return max(0, min(cls.CANVAS_SIZE - 1, index))

    @classmethod
    def canvas_pos(cls, point: Sequence[float]) -> Tuple[int, int]:
        """Return the ``(row, column)`` canvas index for an ``(x, y)`` point."""
        x, y = point[0], point[1]
        return cls.to_canvas(y), cls.to_canvas(x)

    def render_map(self, riders: Iterable[Any] = (), orders: Iterable[Any] = (),
                   route: Optional[List[Point]] = None) -> str:
        """Render the ASCII map with riders, orders and an optional route.

        Args:
            riders: Riders to mark with ``R``.
            orders: Orders whose restaurant (``S``) and customer (``C``)
                locations are shown while not completed.
            route: Optional list of points drawn as a connected line of ``*``.

        Returns:
            Multi-line string.
        """
        size = self.CANVAS_SIZE
        canvas = [
            [self.STREET if (row % 2 == 0 or col % 2 == 0) else self.EMPTY
             for col in range(size)]
            for row in range(size)
        ]
        if route:
            self._draw_route(canvas, route)
        for order in orders:
            if order.status == "completed":
                continue
            row, col = self.canvas_pos(order.res_pos)
            canvas[row][col] = self.RESTAURANT
            row, col = self.canvas_pos(order.cus_pos)
            canvas[row][col] = self.CUSTOMER
        for rider in riders:
            row, col = self.canvas_pos(rider.position)
            canvas[row][col] = self.RIDER

        lines = [" ".join(row) for row in canvas]
        header = "Map (1 char = 50 units; top-left = (0,0); x ->, y down)"
        legend = "Legend: R rider  S restaurant  C customer  # street  . cell  * route"
        return "\n".join([header, *lines, legend])

    def _draw_route(self, canvas: List[List[str]], route: List[Point]) -> None:
        """Draw connected line segments through ``route`` on the canvas."""
        first_row, first_col = self.canvas_pos(route[0])
        if canvas[first_row][first_col] in (self.STREET, self.EMPTY):
            canvas[first_row][first_col] = self.ROUTE
        for (x1, y1), (x2, y2) in zip(route, route[1:]):
            dx = x2 - x1
            dy = y2 - y1
            steps = max(1, max(abs(dx), abs(dy)) // 5)
            for step in range(steps + 1):
                x = round(x1 + dx * step / steps)
                y = round(y1 + dy * step / steps)
                row, col = self.canvas_pos((x, y))
                if canvas[row][col] in (self.STREET, self.EMPTY):
                    canvas[row][col] = self.ROUTE

    def render_status(self, funds: int, riders: Sequence[Any]) -> str:
        """Render the system snapshot: funds and every rider's details."""
        lines = [f"System funds: {funds}", f"Riders: {len(riders)}"]
        if not riders:
            lines.append("  (no riders recruited yet)")
        for rider in riders:
            order_ids = [o.id for o in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id}: position=({rider.x},{rider.y}) "
                f"state={rider.state_name} speed={rider.speed} "
                f"orders={len(order_ids)} order_ids={order_ids}"
                f"{' [special case]' if rider.special_case else ''}")
        return "\n".join(lines)

    def render_orders(self, orders: Sequence[Any]) -> str:
        """Render a table with details for every order."""
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4}  {'Start':>6}  {'Restaurant':<12}  {'Customer':<12}  "
                  f"{'Distance':>8}  {'Taken':>6}  {'Rider':>6}  Status")
        lines = [header, "-" * len(header)]
        for order in orders:
            restaurant = f"({order.res_pos[0]},{order.res_pos[1]})"
            customer = f"({order.cus_pos[0]},{order.cus_pos[1]})"
            taken = str(order.duration) if order.duration is not None else "-"
            rider = f"#{order.rider_id}" if order.rider_id is not None else "-"
            lines.append(
                f"{order.id:>4}  {order.start_tick:>6}  {restaurant:<12}  {customer:<12}  "
                f"{order.distance:>8.1f}  {taken:>6}  {rider:>6}  {order.status}")
        return "\n".join(lines)

    def render_rider_logs(self, riders: Sequence[Any]) -> str:
        """Render every recorded status change for all riders."""
        if not riders:
            return "No riders recruited yet."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} ({len(rider.log)} events):")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = f"order #{entry['order_id']}" if entry["order_id"] is not None else "-"
                lines.append(
                    f"  tick {entry['tick']:>6} | {entry['event']:<20} | {order:<12} | "
                    f"pos ({entry['x']},{entry['y']}) | state {entry['state']}")
        return "\n".join(lines)
