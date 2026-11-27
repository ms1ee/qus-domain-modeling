"""Status displays and ASCII map visualization."""

from rider import STATE_NAMES

GRID_STEP = 50
MAP_CELLS = 17  # 0..800 in steps of 50


class DisplayManager:
    """Renders the simulator state as text for the command line.

    Attributes:
        symbol_map (dict[str, str]): Symbols used on the ASCII map.
    """

    def __init__(self):
        """Initialize the symbol mapping."""
        self.symbol_map = {
            "rider": "@",
            "restaurant": "S",
            "customer": "C",
            "route": "*",
            "empty": " ",
            "street_h": "-",
            "street_v": "|",
            "intersection": "+",
        }

    def _base_symbol(self, x, y):
        """Return the background symbol for a map point."""
        on_x = x % 100 == 0
        on_y = y % 100 == 0
        if on_x and on_y:
            return self.symbol_map["intersection"]
        if on_y:
            return self.symbol_map["street_h"]
        if on_x:
            return self.symbol_map["street_v"]
        return self.symbol_map["empty"]

    def render_map(self, riders, orders, route=None):
        """Render the 8x8 cell map with riders, orders, and an optional route.

        Each character represents 50 units. Intersections are shown with
        ``+``; restaurants (``S``) and customers (``C``) are shown for active
        orders; riders are shown as ``@``; and a route is drawn with ``*``.

        Args:
            riders: Iterable of ``Rider`` objects.
            orders: Iterable of ``Order`` objects (completed ones are skipped).
            route: Optional list of waypoints ``(x, y)``.

        Returns:
            Multi-line string with the map and a legend.
        """
        cells = []
        for row in range(MAP_CELLS):
            y = row * GRID_STEP
            cells.append([self._base_symbol(col * GRID_STEP, y) for col in range(MAP_CELLS)])

        if route:
            for x, y in route[1:-1]:
                cells[y // GRID_STEP][x // GRID_STEP] = self.symbol_map["route"]

        for order in orders:
            if order.status == "completed":
                continue
            rx, ry = order.restaurant_pos
            cx, cy = order.customer_pos
            cells[ry // GRID_STEP][rx // GRID_STEP] = self.symbol_map["restaurant"]
            cells[cy // GRID_STEP][cx // GRID_STEP] = self.symbol_map["customer"]

        for rider in riders:
            cells[rider.y // GRID_STEP][rider.x // GRID_STEP] = self.symbol_map["rider"]

        lines = ["   x: 0 .. 800 (1 char = 50 units)"]
        for row in range(MAP_CELLS):
            lines.append(f"{row * GRID_STEP:>4} " + "".join(cells[row]))
        lines.append(
            "Legend: @ rider  S restaurant  C customer  * route  "
            "+ intersection  - / | street"
        )
        return "\n".join(lines)

    def render_status(self, funds, tick, riders, orders):
        """Render the system snapshot shown by the ``status`` command."""
        active = [o for o in orders if o.status != "completed"]
        lines = [
            f"Funds: {funds}",
            f"Tick: {tick}",
            f"Riders: {len(riders)}",
            f"Active orders: {len(active)}",
        ]
        for rider in riders:
            order_ids = ", ".join(str(o.id) for o in rider.orders) or "-"
            lines.append(
                f"  Rider {rider.rider_id}: status={STATE_NAMES.get(rider.state, 'unknown')} "
                f"position=({rider.x}, {rider.y}) orders={len(rider.orders)} [{order_ids}]"
            )
        return "\n".join(lines)

    def render_orders(self, orders):
        """Render order details for the ``orders`` command."""
        if not orders:
            return "No orders yet."
        lines = []
        for o in orders:
            taken = "-" if o.time_taken is None else str(o.time_taken)
            rider = "-" if o.rider_id is None else str(o.rider_id)
            lines.append(
                f"Order {o.id}: start_tick={o.start_time} restaurant={o.restaurant_pos} "
                f"customer={o.customer_pos} distance={o.distance} time_taken={taken} "
                f"rider={rider} status={o.status}"
            )
        return "\n".join(lines)

    def render_rider_logs(self, riders):
        """Render every recorded status change for all riders."""
        if not riders:
            return "No riders recruited yet."
        lines = []
        for rider in riders:
            lines.append(f"Rider {rider.rider_id}:")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else str(entry["order_id"])
                lines.append(
                    f"  t={entry['time']} event={entry['event']} order={order} "
                    f"position=({entry['x']}, {entry['y']}) "
                    f"state={STATE_NAMES.get(entry['state'], 'unknown')}"
                )
        return "\n".join(lines)
