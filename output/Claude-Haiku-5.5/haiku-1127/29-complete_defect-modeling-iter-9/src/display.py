"""Status formatting and ASCII map rendering."""

from config import CELL_SIZE, MAP_SIZE

_HALF = CELL_SIZE // 2  # canvas resolution: one char per 50 units


class DisplayManager:
    """Renders the ASCII map and formatted status tables.

    The map is a 17x17 character canvas. Even canvas indices are street
    lines (multiples of 100 units) and odd indices are cell centers, so the
    8x8 grid is drawn with '#' streets and '.' cell interiors. Row index is
    the y coordinate and column index is the x coordinate.

    Attributes:
        restaurant_symbol: Symbol for restaurants ('S').
        customer_symbol: Symbol for customers ('C').
        rider_symbol: Symbol for riders ('R').
        empty_symbol: Symbol for empty cell interiors ('.').
        street_symbol: Symbol for streets ('#').
        route_symbol: Symbol for planned route segments ('*').
        canvas_size: Width and height of the canvas in characters.
    """

    def __init__(self):
        """Create a display manager with the standard symbol set."""
        self.restaurant_symbol = "S"
        self.customer_symbol = "C"
        self.rider_symbol = "R"
        self.empty_symbol = "."
        self.street_symbol = "#"
        self.route_symbol = "*"
        self.canvas_size = MAP_SIZE // _HALF + 1

    def legend(self) -> str:
        """Return a one-line legend for the map symbols.

        Returns:
            str: Legend text.
        """
        return (f"Legend: {self.rider_symbol}=rider {self.restaurant_symbol}=restaurant "
                f"{self.customer_symbol}=customer {self.street_symbol}=street "
                f"{self.empty_symbol}=empty {self.route_symbol}=route")

    def _to_canvas(self, point) -> tuple:
        """Convert an ``(x, y)`` coordinate to a ``(row, col)`` canvas index.

        Args:
            point: ``(x, y)`` coordinates.

        Returns:
            tuple: ``(row, col)``.
        """
        return int(point[1]) // _HALF, int(point[0]) // _HALF

    def _put(self, canvas, point, symbol) -> None:
        """Place a symbol at the canvas position of a coordinate.

        Args:
            canvas: 2D list of characters.
            point: ``(x, y)`` coordinates.
            symbol: Character to place.
        """
        row, col = self._to_canvas(point)
        canvas[row][col] = symbol

    def _draw_segment(self, canvas, start, end) -> None:
        """Draw an axis-aligned route segment with the route symbol.

        Args:
            canvas: 2D list of characters.
            start: Segment start ``(x, y)``.
            end: Segment end ``(x, y)``.
        """
        r1, c1 = self._to_canvas(start)
        r2, c2 = self._to_canvas(end)
        for row in range(min(r1, r2), max(r1, r2) + 1):
            for col in range(min(c1, c2), max(c1, c2) + 1):
                canvas[row][col] = self.route_symbol

    def render_map(self, riders=(), orders=(), route=None) -> str:
        """Render the ASCII map with riders, orders and an optional route.

        Args:
            riders: Iterable of Rider objects to display.
            orders: Iterable of Order objects; restaurants and customers of
                non-completed orders are displayed.
            route: Optional tuple ``(start, waypoints)`` drawn as a connected
                line graph.

        Returns:
            str: Multi-line map text.
        """
        size = self.canvas_size
        canvas = [
            [self.street_symbol if (row % 2 == 0 or col % 2 == 0) else self.empty_symbol
             for col in range(size)]
            for row in range(size)
        ]
        if route is not None:
            start, waypoints = route
            points = [tuple(start)] + [tuple(p) for p in waypoints]
            for a, b in zip(points, points[1:]):
                self._draw_segment(canvas, a, b)
        for order in orders:
            if order.status == "completed":
                continue
            self._put(canvas, order.restaurant, self.restaurant_symbol)
            self._put(canvas, order.customer, self.customer_symbol)
        for rider in riders:
            self._put(canvas, (rider.x, rider.y), self.rider_symbol)
        return "\n".join("".join(row) for row in canvas)

    def format_status(self, funds: int, riders, orders) -> str:
        """Format a snapshot of funds, riders and their active orders.

        Args:
            funds: Current fund balance.
            riders: Iterable of Rider objects.
            orders: Iterable of active Order objects (unused for listing,
                kept for API symmetry).

        Returns:
            str: Status report text.
        """
        riders = list(riders)
        lines = [f"System funds: {funds}", f"Riders: {len(riders)}"]
        if not riders:
            lines.append("  (no riders)")
        for rider in riders:
            order_ids = [o.id for o in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id}: state={rider.state_name} "
                f"position=({rider.x}, {rider.y}) speed={rider.speed} "
                f"orders={order_ids if order_ids else '[]'} "
                f"special_case={'yes' if rider.special_case else 'no'}"
            )
        return "\n".join(lines)

    def format_orders(self, orders) -> str:
        """Format a table of all orders.

        Args:
            orders: Iterable of Order objects.

        Returns:
            str: Table text.
        """
        orders = list(orders)
        if not orders:
            return "No orders."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Distance':>8} {'Taken':>6} {'Rider':>6} {'Status':<11}")
        lines = [header, "-" * len(header)]
        for order in orders:
            taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else f"#{order.rider_id}"
            lines.append(
                f"{order.id:>4} {order.start_time:>6} "
                f"{str(tuple(order.res_pos)):>12} {str(tuple(order.cus_pos)):>12} "
                f"{order.distance:>8} {taken:>6} {rider:>6} {order.status:<11}"
            )
        return "\n".join(lines)

    def format_rider_log(self, riders) -> str:
        """Format the full status-change history of every rider.

        Args:
            riders: Iterable of Rider objects.

        Returns:
            str: Event log text grouped by rider.
        """
        riders = list(riders)
        if not riders:
            return "No riders."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} (current: {rider.state_name})")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                lines.append(
                    f"  tick {entry['tick']:>5} | {entry['event']:<22} | "
                    f"order {order:>4} | at ({entry['x']}, {entry['y']})"
                )
        return "\n".join(lines)

    def format_route_summary(self, route, rider) -> str:
        """Summarise a planned route for a rider.

        Args:
            route: Route object from PathPlanner.
            rider: The assigned Rider.

        Returns:
            str: Summary text including speed and estimated ticks.
        """
        return "\n".join([
            f"Assigned rider: #{rider.rider_id}",
            f"Rider speed: {rider.speed} units/tick",
            f"Route distance: {route.total_distance} units",
            f"Estimated time: {route.estimated_ticks(rider.speed)} ticks",
        ])
