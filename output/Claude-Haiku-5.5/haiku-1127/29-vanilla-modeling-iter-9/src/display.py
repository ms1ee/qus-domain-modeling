"""Status display and ASCII map visualisation."""

from order_model import STATUS_COMPLETED
from rider import STATE_NAMES
import grid


class DisplayManager:
    """Renders the map, status, order table and rider history as text.

    Attributes:
        symbol_map (dict[str, str]): symbols used on the ASCII map.
    """

    def __init__(self):
        """Create a display manager with the standard symbol set."""
        self.symbol_map = {
            "rider": "R",
            "restaurant": "S",
            "customer": "C",
            "empty": ".",
            "street": "#",
            "route": "*",
        }

    def render_map(self, riders=(), orders=(), route_points=None):
        """Render the 8x8 grid map.

        Symbol priority: rider > restaurant > customer > route > street > empty.
        Route points are drawn as connected ``*`` cells.

        Args:
            riders (iterable[Rider]): riders to display.
            orders (iterable[Order]): active orders to display.
            route_points (list[tuple] | None): ``(x, y)`` points of a route.

        Returns:
            str: multi-line map text.
        """
        size = grid.GRID_DIM
        sym = self.symbol_map
        canvas = [[sym["empty"]] * size for _ in range(size)]
        for gy in range(size):
            for gx in range(size):
                if grid.is_street_cell(gx, gy):
                    canvas[gy][gx] = sym["street"]
        for x, y in route_points or []:
            canvas[grid.to_cell(y)][grid.to_cell(x)] = sym["route"]
        for order in orders:
            if order.status == STATUS_COMPLETED:
                continue
            rx, ry = order.res_pos
            cx, cy = order.cus_pos
            canvas[grid.to_cell(ry)][grid.to_cell(rx)] = sym["restaurant"]
            canvas[grid.to_cell(cy)][grid.to_cell(cx)] = sym["customer"]
        for rider in riders:
            canvas[grid.to_cell(rider.y)][grid.to_cell(rider.x)] = sym["rider"]

        lines = ["    " + " ".join(str(gx) for gx in range(size))]
        for gy in reversed(range(size)):
            lines.append(f"{gy:>2}  " + " ".join(canvas[gy]))
        lines.append("  (columns = x cell, rows = y cell, each cell is 100x100 units)")
        lines.append(
            "  Legend: R rider  S restaurant  C customer  # street  * route  . empty"
        )
        return "\n".join(lines)

    def render_status(self, system):
        """Render funds, time and every rider's position, state and orders.

        Args:
            system (SystemManager): the system to describe.

        Returns:
            str: status text.
        """
        riders = system.riders
        lines = [
            "=== System Status ===",
            f"Funds: {system.funds}",
            f"Simulated time: {system.simulated_time} ticks",
            f"Riders: {len(riders)}",
        ]
        for rider in riders:
            order_ids = ", ".join(f"#{o.id}" for o in rider.orders) or "none"
            lines.append(
                f"  Rider #{rider.rider_id}: position=({rider.x}, {rider.y}) "
                f"status={STATE_NAMES.get(rider.state, 'unknown')} "
                f"orders={len(rider.orders)} [{order_ids}]"
            )
        return "\n".join(lines)

    def render_orders(self, orders):
        """Render a table of all orders.

        Args:
            orders (iterable[Order]): orders to display.

        Returns:
            str: table text.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        header = (
            f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
            f"{'Distance':>9} {'Time':>6} {'Rider':>6} {'Status':>11}"
        )
        lines = [header, "-" * len(header)]
        for order in orders:
            rest = f"({order.res_pos[0]},{order.res_pos[1]})"
            cust = f"({order.cus_pos[0]},{order.cus_pos[1]})"
            time_taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else f"#{order.rider_id}"
            lines.append(
                f"{order.id:>4} {order.start_time:>6} {rest:>12} {cust:>12} "
                f"{order.distance:>9.1f} {time_taken:>6} {rider:>6} {order.status:>11}"
            )
        return "\n".join(lines)

    def render_rider_history(self, riders):
        """Render every recorded status change for all riders.

        Args:
            riders (iterable[Rider]): riders whose logs are shown.

        Returns:
            str: history text.
        """
        riders = list(riders)
        if not riders:
            return "No riders yet."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} ({len(rider.log)} events):")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                lines.append(
                    f"  t={entry['time']:>5}  {entry['event']:<20} order={order:<6} "
                    f"pos=({entry['x']}, {entry['y']}) "
                    f"state={STATE_NAMES.get(entry['state'], 'unknown')}"
                )
        return "\n".join(lines)
