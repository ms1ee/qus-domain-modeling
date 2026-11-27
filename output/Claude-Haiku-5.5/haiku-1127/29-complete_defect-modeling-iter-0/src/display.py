"""Status, order, rider and ASCII map rendering.

Map symbols: ``R`` rider, ``S`` restaurant, ``C`` customer, ``.`` empty cell,
``#`` street (cells and connecting segments of the displayed route).
The 8x8 cells are drawn on a 15x15 canvas so that connecting segments can be
placed between neighbouring cells.
"""

from path_planner import CELL_HALF, CELL_SIZE, GRID_CELLS, cell_of

SYMBOL_RIDER = "R"
SYMBOL_RESTAURANT = "S"
SYMBOL_CUSTOMER = "C"
SYMBOL_EMPTY = "."
SYMBOL_STREET = "#"

LEGEND = "Legend: R=Rider  S=Restaurant  C=Customer  .=Empty  #=Street"


class DisplayManager:
    """Formats system information for the command line.

    Attributes:
        display_width: Number of grid cells across the map.
    """

    def __init__(self, display_width=GRID_CELLS):
        """Create a display manager.

        Args:
            display_width: Number of grid columns to draw.
        """
        self.display_width = display_width

    def render_map(self, riders, orders, route=None):
        """Render the 8x8 ASCII map.

        Args:
            riders: Iterable of Rider objects to draw.
            orders: Iterable of Order objects; active restaurants and
                customers are drawn.
            route: Optional Route whose cells and segments are drawn as streets.

        Returns:
            Multi-line string with the map.
        """
        size = 2 * GRID_CELLS - 1
        canvas = [[" "] * size for _ in range(size)]
        for gy in range(GRID_CELLS):
            for gx in range(GRID_CELLS):
                canvas[2 * gy][2 * gx] = SYMBOL_EMPTY

        if route is not None and route.waypoints:
            waypoints = route.waypoints
            for gx, gy in waypoints:
                canvas[2 * gy][2 * gx] = SYMBOL_STREET
            for (ax, ay), (bx, by) in zip(waypoints, waypoints[1:]):
                canvas[ay + by][ax + bx] = SYMBOL_STREET

        for order in orders:
            if order.status == "completed":
                continue
            rx, ry = cell_of(order.restaurant_x, order.restaurant_y)
            canvas[2 * ry][2 * rx] = SYMBOL_RESTAURANT
            cx, cy = cell_of(order.customer_x, order.customer_y)
            canvas[2 * cy][2 * cx] = SYMBOL_CUSTOMER

        for rider in riders:
            gx, gy = cell_of(rider.x, rider.y)
            canvas[2 * gy][2 * gx] = SYMBOL_RIDER

        lines = []
        prefix_width = len(f"y={CELL_HALF:>3} | ")
        header = [" "] * size
        for gx in range(GRID_CELLS):
            header[2 * gx] = str(gx)
        lines.append(" " * prefix_width + "".join(header))
        for gy in range(GRID_CELLS):
            center_y = gy * CELL_SIZE + CELL_HALF
            prefix = f"y={center_y:>3} | "
            lines.append(prefix + "".join(canvas[2 * gy]))
        lines.append("Columns: x cell index (0-7); rows: y cell center (0-800)")
        lines.append(LEGEND)
        return "\n".join(lines)

    def render_route_summary(self, route, speed):
        """Describe a route's length and estimated travel time.

        Args:
            route: Route object.
            speed: Rider speed in units per tick.

        Returns:
            Single-line summary string.
        """
        ticks = route.travel_ticks(speed) if speed > 0 else 0
        return (
            f"Route length: {route.total_distance} units | speed: {speed} units/tick "
            f"| estimated time: {ticks} tick(s)"
        )

    def render_rider_line(self, rider):
        """Return a one-line description of a rider."""
        order_ids = ", ".join(str(o.id) for o in rider.orders) or "none"
        return (
            f"Rider #{rider.rider_id}: position ({rider.x}, {rider.y}) | "
            f"state: {rider.state_name} | speed: {rider.speed} | "
            f"orders: {order_ids} | special case: {'yes' if rider.special_case else 'no'}"
        )

    def render_status(self, tick, funds, riders, pending_count):
        """Render the system status snapshot.

        Args:
            tick: Current simulated tick.
            funds: Current fund balance.
            riders: List of Rider objects.
            pending_count: Number of orders waiting for a rider.

        Returns:
            Multi-line string.
        """
        lines = [
            f"System status (tick {tick})",
            f"  Funds: {funds}",
            f"  Riders: {len(riders)} | Pending orders: {pending_count}",
        ]
        if not riders:
            lines.append("  No riders on duty.")
        for rider in riders:
            lines.append("  " + self.render_rider_line(rider))
        return "\n".join(lines)

    def render_orders(self, orders):
        """Render a table of orders.

        Args:
            orders: Iterable of Order objects.

        Returns:
            Multi-line string.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        header = (
            f"{'ID':>4} {'Start':>6} {'Restaurant':>14} {'Customer':>14} "
            f"{'Distance':>9} {'Time':>6} {'Rider':>6} {'Status':<12}"
        )
        lines = [header, "-" * len(header)]
        for order in orders:
            restaurant = f"({order.restaurant_raw[0]},{order.restaurant_raw[1]})"
            customer = f"({order.customer_raw[0]},{order.customer_raw[1]})"
            distance = str(order.distance) if order.completion_time is not None else "-"
            time_taken = str(order.time_taken) if order.time_taken is not None else "-"
            rider = str(order.rider_id) if order.rider_id is not None else "-"
            lines.append(
                f"{order.id:>4} {order.start_time:>6} {restaurant:>14} {customer:>14} "
                f"{distance:>9} {time_taken:>6} {rider:>6} {order.status:<12}"
            )
        return "\n".join(lines)

    def render_rider_log(self, riders):
        """Render every recorded status change of all riders.

        Args:
            riders: Iterable of Rider objects.

        Returns:
            Multi-line string.
        """
        riders = list(riders)
        if not riders:
            return "No riders on duty."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} history:")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order_text = entry["order_id"] if entry["order_id"] is not None else "-"
                lines.append(
                    f"  t={entry['time']:>5}  {entry['event']:<22} "
                    f"pos=({entry['x']},{entry['y']})  order={order_text}"
                )
        return "\n".join(lines)
