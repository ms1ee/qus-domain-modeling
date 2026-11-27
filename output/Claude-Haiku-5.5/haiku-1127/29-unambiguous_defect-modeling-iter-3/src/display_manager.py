"""Text rendering: ASCII map, status, order and rider reports."""

from grid import CELL_SIZE, GRID_DIM, INTERSECTIONS, MAP_SIZE
from rider import STATE_NAMES

COLS_PER_CELL = 4
ROWS_PER_CELL = 2
MAP_COLS = GRID_DIM * COLS_PER_CELL + 1
MAP_ROWS = GRID_DIM * ROWS_PER_CELL + 1


class DisplayManager:
    """Builds all text output for the command-line interface.

    Attributes:
        symbol_map (dict): Symbols used on the ASCII map.
    """

    HELP_TEXT = (
        "Commands:\n"
        "  start [rx ry cx cy]  Place an order (restaurant x y, customer x y, 0-800)\n"
        "                       Without arguments you will be prompted for each value.\n"
        "  tick [n]             Advance the simulation by n ticks (default 1)\n"
        "  status               System funds, riders and their current state\n"
        "  orders               Details of all orders\n"
        "  riders               Full status-change log for every rider\n"
        "  map                  ASCII map with riders and active orders\n"
        "  history              Previously entered commands\n"
        "  save                 Save state to the JSON state file\n"
        "  help                 Show this help\n"
        "  quit / exit          Save and exit\n"
        "Shortcuts: s=start t=tick st=status o=orders r=riders m=map h=help q=quit\n"
        "History:   !! repeats the last command, !n repeats history entry n"
    )

    def __init__(self):
        """Create the display manager with the default symbol mapping."""
        self.symbol_map = {
            "empty": ".",
            "street_h": "-",
            "street_v": "|",
            "intersection": "+",
            "restaurant": "M",
            "customer": "C",
            "rider": "R",
            "route": "*",
        }

    @staticmethod
    def to_cell(x, y):
        """Convert a map coordinate into a (column, row) canvas index.

        Args:
            x: X coordinate, 0-800.
            y: Y coordinate, 0-800 (y grows upward).

        Returns:
            tuple[int, int]: Column and row on the ASCII canvas.
        """
        col = int(x) * COLS_PER_CELL // CELL_SIZE
        row = (MAP_SIZE - int(y)) * ROWS_PER_CELL // CELL_SIZE
        return col, row

    def _put(self, canvas, x, y, symbol):
        """Write a symbol at the canvas position of a map coordinate."""
        col, row = self.to_cell(x, y)
        canvas[row][col] = symbol

    def render_map(self, riders=(), orders=(), route=None):
        """Render the 8x8 grid as ASCII art.

        Intersections are shown as '+', streets as '-' and '|', restaurants
        as 'M', customers as 'C', riders as 'R' and a route as '*'.

        Args:
            riders: Riders to mark on the map.
            orders: Orders whose restaurant and customer should be marked.
            route: Optional list of (x, y) points to draw as a route.

        Returns:
            str: Multi-line map with legend.
        """
        sym = self.symbol_map
        canvas = [[sym["empty"]] * MAP_COLS for _ in range(MAP_ROWS)]

        for ix in range(GRID_DIM):
            for iy in range(GRID_DIM + 1):
                col_a, row = self.to_cell(ix * CELL_SIZE, iy * CELL_SIZE)
                col_b, _ = self.to_cell((ix + 1) * CELL_SIZE, iy * CELL_SIZE)
                for col in range(col_a + 1, col_b):
                    canvas[row][col] = sym["street_h"]
        for ix in range(GRID_DIM + 1):
            for iy in range(GRID_DIM):
                col, row_top = self.to_cell(ix * CELL_SIZE, (iy + 1) * CELL_SIZE)
                _, row_bottom = self.to_cell(ix * CELL_SIZE, iy * CELL_SIZE)
                for row in range(row_top + 1, row_bottom):
                    canvas[row][col] = sym["street_v"]
        for x, y in INTERSECTIONS:
            self._put(canvas, x, y, sym["intersection"])

        for x, y in route or []:
            self._put(canvas, x, y, sym["route"])
        for order in orders:
            if order.status == "completed":
                continue
            self._put(canvas, order.restaurant_x, order.restaurant_y, sym["restaurant"])
            self._put(canvas, order.customer_x, order.customer_y, sym["customer"])
        for rider in riders:
            self._put(canvas, rider.x, rider.y, sym["rider"])

        rows = ["".join(row) for row in canvas]
        legend = ("Legend: + intersection  - | street  . empty  M restaurant  "
                  "C customer  R rider  * route")
        return "\n".join(rows) + "\n" + legend

    def render_status(self, tick, funds, riders, active_orders, issues):
        """Render the system status snapshot.

        Args:
            tick: Current simulated tick.
            funds: System fund balance.
            riders: List of Rider objects.
            active_orders: List of unfinished orders.
            issues: List of consistency problem strings.

        Returns:
            str: Formatted status report.
        """
        lines = [
            "Tick: %d" % tick,
            "System funds: %d" % funds,
            "Riders: %d" % len(riders),
            "Active orders: %d" % len(active_orders),
            "",
        ]
        if riders:
            lines.append("{:<6} {:<12} {:<12} {:<8} {:<6} {}".format(
                "Rider", "Position", "State", "Orders", "Speed", "Order IDs"))
            for rider in riders:
                position = "(%d, %d)" % (rider.x, rider.y)
                order_ids = ", ".join(str(o.id) for o in rider.orders) or "-"
                lines.append("{:<6} {:<12} {:<12} {:<8} {:<6} {}".format(
                    rider.rider_id, position, STATE_NAMES[rider.state],
                    len(rider.orders), rider.speed, order_ids))
        else:
            lines.append("No riders on duty.")
        lines.append("")
        if issues:
            lines.append("Consistency issues:")
            lines.extend("  - " + issue for issue in issues)
        else:
            lines.append("Consistency check: OK")
        return "\n".join(lines)

    def render_orders(self, orders):
        """Render a table of order details.

        Args:
            orders: List of Order objects.

        Returns:
            str: Formatted table, or a notice if there are no orders.
        """
        if not orders:
            return "No orders yet."
        lines = ["{:<4} {:<6} {:<12} {:<12} {:<6} {:<10} {:<9} {:<6} {}".format(
            "ID", "Start", "Restaurant", "Customer", "Rider", "Status",
            "Distance", "Time", "Efficiency")]
        for order in orders:
            restaurant = "(%d, %d)" % order.restaurant_pos
            customer = "(%d, %d)" % order.customer_pos
            rider = str(order.rider_id) if order.rider_id is not None else "-"
            distance = "%.1f" % order.distance
            time_taken = str(order.time_taken) if order.time_taken is not None else "-"
            efficiency = ("%.3f" % order.efficiency) if order.efficiency is not None else "-"
            lines.append("{:<4} {:<6} {:<12} {:<12} {:<6} {:<10} {:<9} {:<6} {}".format(
                order.id, order.start_time, restaurant, customer, rider,
                order.status, distance, time_taken, efficiency))
        return "\n".join(lines)

    def render_rider_events(self, riders):
        """Render every recorded rider status change, ordered by time.

        Args:
            riders: List of Rider objects.

        Returns:
            str: One line per event.
        """
        entries = []
        for rider in riders:
            for index, entry in enumerate(rider.log):
                entries.append((entry["time"], rider.rider_id, index, entry))
        if not entries:
            return "No rider events recorded."
        entries.sort(key=lambda item: (item[0], item[1], item[2]))
        lines = []
        for time, rider_id, _, entry in entries:
            order_text = "-" if entry["order_id"] is None else str(entry["order_id"])
            lines.append("[t=%4d] rider %-3d %-20s order=%-4s at (%d, %d) state=%s %s" % (
                time, rider_id, entry["event"], order_text, entry["x"], entry["y"],
                STATE_NAMES[entry["state"]], entry["description"]))
        return "\n".join(lines)

    def render_order_result(self, order, rider, new_rider, route, funds, eta, speed):
        """Render the confirmation shown after an order is accepted.

        Args:
            order: The accepted Order.
            rider: The assigned Rider.
            new_rider: True if a rider was recruited for this order.
            route: List of (x, y) points from the rider to the restaurant to
                the customer.
            funds: System funds after the order was processed.
            eta: Estimated ticks to deliver.
            speed: Rider speed in units per tick.

        Returns:
            str: Formatted confirmation with an ASCII route map.
        """
        distance = max(0, len(route) - 1)
        lines = [
            "Order #%d accepted." % order.id,
            "  Restaurant grid position: (%d, %d)" % order.restaurant_pos,
            "  Customer grid position:   (%d, %d)" % order.customer_pos,
            "  New rider added: %s" % ("yes (rider #%d)" % rider.rider_id if new_rider else "no"),
            "  Assigned rider: #%d (state: %s, speed: %d units/tick)" % (
                rider.rider_id, STATE_NAMES[rider.state], speed),
            "  Estimated route distance: %d units, estimated time: %d ticks" % (distance, eta),
            "  System funds: %d" % funds,
            "  Route map:",
            self.render_map(riders=[rider], orders=[order], route=route),
        ]
        return "\n".join(lines)
