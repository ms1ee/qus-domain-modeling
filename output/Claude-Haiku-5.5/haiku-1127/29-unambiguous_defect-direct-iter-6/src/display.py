"""Status text formatting and ASCII map rendering."""

import logging

import config
from path_planner import PathPlanner

logger = logging.getLogger(__name__)


class DisplayManager:
    """Render the map, status snapshots, order tables, and rider logs."""

    LEGEND = (
        "Legend: + intersection  - | street  R restaurant  C customer  "
        "* route  0-9 rider id (mod 10)  blank = empty"
    )

    def render_map(self, riders=None, orders=None, route=None):
        """Render the 8x8 grid map as ASCII art.

        The map is drawn on a canvas with one character per lattice point and
        one connector character between adjacent points. Streets appear as
        lines, restaurants as ``R``, customers as ``C``, the planned route as
        ``*``, and riders as their ID modulo 10.

        Args:
            riders: Optional list of Rider objects to draw.
            orders: Optional list of Order objects whose endpoints are marked.
            route: Optional list of lattice points to draw as a route.

        Returns:
            Multi-line string containing the map and legend.
        """
        step = config.LATTICE_STEP
        size_units = config.MAP_SIZE
        cell = config.CELL_SIZE
        canvas_size = (size_units // step) * 2 + 1
        canvas = [[" "] * canvas_size for _ in range(canvas_size)]

        def put(point, symbol):
            x, y = point
            canvas[(y // step) * 2][(x // step) * 2] = symbol

        def put_link(a, b, symbol):
            canvas[(a[1] + b[1]) // step][(a[0] + b[0]) // step] = symbol

        for x in range(0, size_units + 1, step):
            for y in range(0, size_units + 1, step):
                point = (x, y)
                if not PathPlanner.is_street(point):
                    continue
                if x % cell == 0 and y % cell == 0:
                    symbol = "+"
                elif y % cell == 0:
                    symbol = "-"
                else:
                    symbol = "|"
                put(point, symbol)
                right = (x + step, y)
                if x + step <= size_units and y % cell == 0 and PathPlanner.is_street(right):
                    put_link(point, right, "-")
                up = (x, y + step)
                if y + step <= size_units and x % cell == 0 and PathPlanner.is_street(up):
                    put_link(point, up, "|")

        if route:
            for a, b in zip(route, route[1:]):
                put_link(a, b, "*")
            for point in route:
                put(point, "*")

        if orders:
            for order in orders:
                if order.status == "completed":
                    continue
                put(order.res_pos, "R")
                put(order.cus_pos, "C")

        if riders:
            for rider in riders:
                put(rider.position, str(rider.rider_id % 10))

        lines = ["".join(row).rstrip() for row in canvas]
        return "\n".join(lines) + "\n" + self.LEGEND

    def format_status(self, funds, tick, riders):
        """Format the system status snapshot.

        Args:
            funds: Current fund balance.
            tick: Current simulated tick.
            riders: List of Rider objects.

        Returns:
            Multi-line status string.
        """
        lines = [
            f"System funds : {funds}",
            f"Simulated tick: {tick}",
            f"Riders       : {len(riders)}",
        ]
        if riders:
            lines.append(
                f"{'ID':<5}{'Position':<14}{'State':<13}{'Speed':<7}{'Orders':<8}Order IDs"
            )
            for rider in riders:
                order_ids = [order.id for order in rider.orders]
                lines.append(
                    f"{rider.rider_id:<5}{str(rider.position):<14}{rider.state_name:<13}"
                    f"{rider.speed:<7}{len(rider.orders):<8}{order_ids}"
                )
        return "\n".join(lines)

    def format_orders(self, orders):
        """Format a table of all orders.

        Args:
            orders: List of Order objects.

        Returns:
            Multi-line table string.
        """
        if not orders:
            return "No orders yet."
        lines = [
            f"{'ID':<5}{'Start':<7}{'Restaurant':<13}{'Customer':<13}"
            f"{'Distance':<10}{'Time':<7}{'Rider':<7}Status"
        ]
        for order in orders:
            time_taken = order.time_taken if order.time_taken is not None else "-"
            rider = order.rider_id if order.rider_id is not None else "-"
            lines.append(
                f"{order.id:<5}{order.start_tick:<7}{str(order.res_pos):<13}"
                f"{str(order.cus_pos):<13}{order.distance:<10}{str(time_taken):<7}"
                f"{str(rider):<7}{order.status}"
            )
        return "\n".join(lines)

    def format_rider_logs(self, riders):
        """Format the event history of every rider.

        Args:
            riders: List of Rider objects.

        Returns:
            Multi-line string with one block per rider.
        """
        if not riders:
            return "No riders have been recruited."
        blocks = []
        for rider in riders:
            blocks.append(f"Rider {rider.rider_id} (speed {rider.speed}):")
            if not rider.log:
                blocks.append("  no events")
            for entry in rider.log:
                order_text = entry["order_id"] if entry["order_id"] is not None else "-"
                state_name = {0: "idle", 1: "picking up", 2: "delivering"}.get(
                    entry["state"], "unknown"
                )
                blocks.append(
                    f"  t={entry['time']:<5} {entry['event']:<22} order={order_text:<5}"
                    f" pos=({entry['x']},{entry['y']}) state={state_name}"
                )
        return "\n".join(blocks)

    def format_start_result(self, order, rider, new_rider, length, eta):
        """Format the result of accepting a new order.

        Args:
            order: The accepted Order.
            rider: The assigned Rider.
            new_rider: True if a new rider was recruited for this order.
            length: Route length in map units.
            eta: Estimated ticks to complete the route.

        Returns:
            Multi-line string.
        """
        return "\n".join([
            f"Order {order.id} accepted.",
            f"Restaurant grid : {order.res_pos}",
            f"Customer grid   : {order.cus_pos}",
            f"New rider added : {'yes' if new_rider else 'no'}",
            f"Assigned rider  : {rider.rider_id} at {rider.position}, "
            f"speed {rider.speed} units/tick",
            f"Route           : {length} units, about {eta} tick(s)",
        ])

    @staticmethod
    def format_error(message):
        """Format an error message for display.

        Args:
            message: Error text.

        Returns:
            Formatted error string.
        """
        return f"Error: {message}"
