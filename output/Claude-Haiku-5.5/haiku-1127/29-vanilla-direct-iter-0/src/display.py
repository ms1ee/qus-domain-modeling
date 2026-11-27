"""Status displays and ASCII map visualisation."""

from globalvar import get_value
from grid import CELL_SIZE, MAP_SIZE, cell_label
from rider import STATE_NAMES

# Map resolution: one character per 50 units. Streets (multiples of 100)
# fall on even indices and cell centres (x % 100 == 50) on odd indices, so
# the 8x8 cell grid is drawn with '#' street lines between the blocks.
STEP = CELL_SIZE // 2
CANVAS = MAP_SIZE // STEP + 1


def _idx(value) -> int:
    """Map a coordinate to a canvas index."""
    return min(CANVAS - 1, max(0, round(value / STEP)))


def _line_cells(a, b) -> list:
    """Return canvas cells on the line between two canvas indices."""
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    steps = max(abs(dx), abs(dy))
    if steps == 0:
        return [a]
    cells = []
    for k in range(steps + 1):
        cells.append((round(a[0] + dx * k / steps),
                      round(a[1] + dy * k / steps)))
    return cells


class DisplayManager:
    """Produces text output for status, orders, logs and the map."""

    def render_map(self, riders=None, orders=None, route=None) -> str:
        """Render the ASCII city map.

        Symbols: 'R' rider, 'S' restaurant, 'C' customer, '#' street,
        '.' empty block, '*' route line.

        Args:
            riders: Riders to draw (defaults to all riders).
            orders: Orders whose restaurant/customer to draw (defaults to
                all uncompleted orders).
            route: Optional list of (x, y) points drawn as connected lines.

        Returns:
            Multi-line string containing the map and a legend.
        """
        if riders is None:
            riders = get_value("riders", []) or []
        if orders is None:
            orders = [o for o in get_value("orders", []) or []
                      if o.status != "completed"]

        n = CANVAS
        canvas = [["#" if (r % 2 == 0 or c % 2 == 0) else "."
                   for c in range(n)] for r in range(n)]

        def put(ci, ri, symbol):
            canvas[n - 1 - ri][ci] = symbol

        if route:
            indices = [(_idx(x), _idx(y)) for x, y in route]
            for a, b in zip(indices, indices[1:]):
                for cell in _line_cells(a, b):
                    put(cell[0], cell[1], "*")
            if len(indices) == 1:
                put(indices[0][0], indices[0][1], "*")

        for order in orders:
            rx, ry = order.res_pos
            cx, cy = order.cus_pos
            put(_idx(rx), _idx(ry), "S")
            put(_idx(cx), _idx(cy), "C")

        for rider in riders:
            put(_idx(rider.x), _idx(rider.y), "R")

        lines = ["Map (y increases upwards; 1 char = 50 units):"]
        for r in range(n):
            y_value = (n - 1 - r) * STEP
            label = f"{y_value:>4} " if r % 2 == 0 else "     "
            lines.append(label + "".join(canvas[r]))
        lines.append("     " + "x: 0 .. 800")
        lines.append("Legend: R=Rider S=Restaurant C=Customer "
                     "#=Street .=Empty *=Route")
        return "\n".join(lines)

    def format_status(self) -> str:
        """Return the system status snapshot text."""
        riders = get_value("riders", []) or []
        lines = [
            f"=== System Status (tick {get_value('tick', 0)}) ===",
            f"System funds: {get_value('system_funds')}",
            f"Riders: {len(riders)}",
        ]
        if not riders:
            lines.append("  (no riders recruited yet)")
        for rider in riders:
            order_ids = [o.id for o in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id}: position=({rider.x}, {rider.y}) "
                f"status={rider.state_name} orders={len(order_ids)} "
                f"{order_ids}")
        return "\n".join(lines)

    def format_orders(self) -> str:
        """Return a table of all orders."""
        orders = get_value("orders", []) or []
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>22} "
                  f"{'Customer':>22} {'Dist':>8} {'Taken':>6} "
                  f"{'Rider':>6} {'Status':>11}")
        lines = [header, "-" * len(header)]
        for o in orders:
            taken = "-" if o.time_taken is None else str(o.time_taken)
            rider = "-" if o.rider_id is None else f"#{o.rider_id}"
            lines.append(
                f"{o.id:>4} {o.start_time:>6} "
                f"{str(o.res_pos):>22} {str(o.cus_pos):>22} "
                f"{o.distance:>8} {taken:>6} {rider:>6} {o.status:>11}")
        return "\n".join(lines)

    def format_rider_logs(self) -> str:
        """Return every recorded status change for all riders."""
        riders = get_value("riders", []) or []
        if not riders:
            return "No riders recruited yet."
        lines = []
        for rider in riders:
            lines.append(f"--- Rider #{rider.rider_id} ---")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None \
                    else f"order {entry['order_id']}"
                state = STATE_NAMES.get(entry["state"], "Unknown")
                lines.append(
                    f"  [t={entry['time']:>4}] {entry['event']:<22} "
                    f"{order:<10} pos=({entry['x']}, {entry['y']}) "
                    f"state={state}")
        return "\n".join(lines)

    def format_assignment(self, order, rider, new_rider: bool, route,
                          ticks: int) -> str:
        """Return the summary printed after an order has been processed.

        Args:
            order: The Order that was processed.
            rider: The Rider that served it.
            new_rider: Whether a new rider was recruited for this order.
            route: List of positions the rider visited.
            ticks: Number of ticks simulated.

        Returns:
            Multi-line summary text.
        """
        lines = [
            f"Order #{order.id} processed.",
            f"  Restaurant grid cell: {cell_label(*order.res_pos)} "
            f"centre {order.res_pos}",
            f"  Customer grid cell:   {cell_label(*order.cus_pos)} "
            f"centre {order.cus_pos}",
            f"  New rider added: {'yes' if new_rider else 'no'}",
            f"  Assigned rider: #{rider.rider_id} (speed {rider.speed} "
            f"units/tick)",
            f"  Distance (restaurant-customer): {order.distance}",
            f"  Ticks simulated: {ticks}",
            f"  Order status: {order.status}",
        ]
        if order.time_taken is not None:
            lines.append(f"  Time taken: {order.time_taken} ticks, "
                         f"efficiency {order.efficiency} units/tick")
        lines.append(f"  Route points recorded: {len(route)}")
        return "\n".join(lines)
