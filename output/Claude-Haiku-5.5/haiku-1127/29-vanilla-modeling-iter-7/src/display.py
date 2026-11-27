"""Status display and ASCII map rendering."""

from order_model import Order

STATE_NAMES = {0: "Idle", 1: "Picking up", 2: "Delivering"}
GRID_CELLS = 8
CELL_SIZE = 100


def _cell_index(value):
    """Return the grid cell index (0-7) containing a coordinate."""
    return min(max(int(value), 0) // CELL_SIZE, GRID_CELLS - 1)


class DisplayManager:
    """Renders status text, order tables, rider logs and the ASCII map.

    Attributes:
        system: The ``SystemManager`` being displayed.
        symbol_map: Mapping of map features to their ASCII symbols.
    """

    def __init__(self, system):
        """Create a display bound to a system manager.

        Args:
            system: The ``SystemManager`` instance.
        """
        self.system = system
        self.symbol_map = {
            "rider": "R",
            "restaurant": "S",
            "customer": "C",
            "empty": ".",
            "street": "#",
        }

    def render_status(self):
        """Return the system snapshot: funds, rider count and each rider's state."""
        riders = self.system.riders
        lines = [
            "=== System Status ===",
            f"Tick: {self.system.current_tick}",
            f"System funds: {self.system.funds}",
            f"Riders: {len(riders)}",
        ]
        if not riders:
            lines.append("  (no riders recruited yet)")
        for rider in riders:
            ids = ", ".join(f"#{o.id}" for o in rider.orders) or "-"
            lines.append(
                f"  Rider #{rider.rider_id}: position=({rider.x}, {rider.y}) "
                f"status={STATE_NAMES.get(rider.state, 'Unknown')} "
                f"orders={len(rider.orders)} [{ids}]"
            )
        return "\n".join(lines)

    def render_orders(self):
        """Return a table with the details of every order."""
        orders = self.system.order_manager.orders
        if not orders:
            return "No orders yet."
        lines = ["=== Orders ==="]
        for order in orders:
            rider = f"#{order.rider_id}" if order.rider_id is not None else "-"
            taken = order.time_taken if order.time_taken is not None else "-"
            lines.append(
                f"Order #{order.id}: start_tick={order.start_time} "
                f"restaurant={order.restaurant} customer={order.customer} "
                f"distance={order.distance:.1f} time_taken={taken} "
                f"rider={rider} status={order.status}"
            )
        return "\n".join(lines)

    def render_rider_log(self):
        """Return every recorded status change for all riders, ordered by tick."""
        entries = []
        for rider in self.system.riders:
            for entry in rider.log:
                entries.append((entry["tick"], rider.rider_id, entry))
        if not entries:
            return "No rider events recorded."
        entries.sort(key=lambda item: (item[0], item[1]))
        lines = ["=== Rider Event Log ==="]
        for tick, rider_id, entry in entries:
            order_text = f"order #{entry['order_id']}" if entry["order_id"] is not None else "-"
            lines.append(
                f"tick {tick:>4} | Rider #{rider_id} | {entry['event']:<20} | "
                f"{order_text:<10} | pos=({entry['x']}, {entry['y']}) "
                f"state={STATE_NAMES.get(entry['state'], 'Unknown')}"
            )
        return "\n".join(lines)

    def render_map(self, route_points=None):
        """Render the 8x8 ASCII map.

        Symbols: ``R`` rider, ``S`` restaurant, ``C`` customer, ``#`` street
        or route segment, ``.`` empty. Riders are drawn on top of other
        symbols. Only orders that are not completed are shown.

        Args:
            route_points: Optional list of ``(x, y)`` points to draw as a route.

        Returns:
            Multi-line string of the map.
        """
        grid = [[self.symbol_map["empty"]] * GRID_CELLS for _ in range(GRID_CELLS)]

        def place(x, y, symbol):
            col = _cell_index(x)
            row = GRID_CELLS - 1 - _cell_index(y)
            grid[row][col] = symbol

        for x, y in route_points or []:
            place(x, y, self.symbol_map["street"])
        for order in self.system.order_manager.orders:
            if order.status == Order.COMPLETED:
                continue
            place(order.restaurant[0], order.restaurant[1], self.symbol_map["restaurant"])
            place(order.customer[0], order.customer[1], self.symbol_map["customer"])
        for rider in self.system.riders:
            place(rider.x, rider.y, self.symbol_map["rider"])

        lines = ["=== Map (x cells 0-7 left to right, y cells bottom to top) ==="]
        lines.append(" " * 7 + " ".join(str(c) for c in range(GRID_CELLS)))
        for row in range(GRID_CELLS):
            gy = GRID_CELLS - 1 - row
            lines.append(f"y={gy * CELL_SIZE:>3}  " + " ".join(grid[row]))
        lines.append("Legend: R=Rider S=Restaurant C=Customer #=Street/Route .=Empty")
        return "\n".join(lines)
