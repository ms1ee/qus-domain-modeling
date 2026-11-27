"""Status displays and ASCII map rendering for the command line.

The map is drawn on an 8x8 node grid. Each node is a street intersection drawn
as '.', and route segments between nodes are drawn as '#'. Riders are 'R',
restaurants are 'S' and customers are 'C'.
"""

from typing import Iterable, List, Optional, Sequence

from location import grid_dimensions, to_grid_index
from order_model import Order
from path_planner import Route
from rider import STATE_NAMES, Rider


class DisplayManager:
    """Renders the map, rider details, order tables and logs as text."""

    def __init__(self) -> None:
        self.map_symbols = {
            "rider": "R",
            "restaurant": "S",
            "customer": "C",
            "empty": ".",
            "street": "#",
        }

    def render_map(self, riders: Sequence[Rider] = (),
                   orders: Iterable[Order] = (),
                   route: Optional[Route] = None) -> str:
        """Render the ASCII map.

        Args:
            riders: Riders to mark with 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') to mark.
            route: Optional route to draw with '#' segments.

        Returns:
            The map as a multi-line string.
        """
        dim = grid_dimensions()
        size = 2 * dim - 1
        canvas = [[" "] * size for _ in range(size)]
        for row in range(dim):
            for col in range(dim):
                canvas[2 * row][2 * col] = self.map_symbols["empty"]

        if route is not None:
            nodes = [(wp.grid_x, wp.grid_y) for wp in route.waypoints]
            for (c1, r1), (c2, r2) in zip(nodes, nodes[1:]):
                canvas[r1 + r2][c1 + c2] = self.map_symbols["street"]

        for order in orders:
            self._mark(canvas, order.res_pos.node, "restaurant")
            self._mark(canvas, order.cus_pos.node, "customer")

        for rider in riders:
            node = (to_grid_index(rider.x), to_grid_index(rider.y))
            self._mark(canvas, node, "rider")

        return self._compose(canvas, dim)

    def _mark(self, canvas: List[List[str]], node, key: str) -> None:
        """Place a symbol on the canvas at a grid node."""
        col, row = node
        canvas[2 * row][2 * col] = self.map_symbols[key]

    @staticmethod
    def _compose(canvas: List[List[str]], dim: int) -> str:
        """Join the canvas rows with axis labels and a legend."""
        header = [" "] * len(canvas[0])
        for col in range(dim):
            header[2 * col] = str(col % 10)
        lines = ["    " + "".join(header)]
        for index, row in enumerate(canvas):
            label = f"{index // 2:>2}  " if index % 2 == 0 else "    "
            lines.append(label + "".join(row))
        lines.append("Columns: grid x (0-7) | Rows: grid y (0-7)")
        lines.append("Legend: R=rider  S=restaurant  C=customer  "
                     ".=intersection  #=route street")
        return "\n".join(lines)

    def render_status(self, funds: int, simulated_time: int, riders: Sequence[Rider],
                      pending: int, active: int, completed: int) -> str:
        """Render the system snapshot and a summary of every rider."""
        lines = [
            f"Simulated time : t={simulated_time}",
            f"System funds   : {funds}",
            f"Riders         : {len(riders)}",
            f"Pending orders : {pending}",
            f"Active orders  : {active}",
            f"Completed      : {completed}",
            "",
            self.render_riders(riders),
        ]
        return "\n".join(lines)

    def render_riders(self, riders: Sequence[Rider]) -> str:
        """Render detailed information for each rider."""
        if not riders:
            return "No riders on duty."
        lines = [f"Riders ({len(riders)}):"]
        for rider in riders:
            col, row = to_grid_index(rider.x), to_grid_index(rider.y)
            order_ids = ", ".join(f"#{o.id}" for o in rider.orders) or "none"
            special = "yes" if rider.special_case else "no"
            lines.append(
                f"  Rider #{rider.rider_id}: pos ({rider.x},{rider.y}) "
                f"cell ({col},{row}) | state: {rider.status_name} | "
                f"speed: {rider.speed} | orders: {order_ids} | special: {special}"
            )
        return "\n".join(lines)

    def render_rider_logs(self, riders: Sequence[Rider]) -> str:
        """Render every recorded status change for every rider."""
        if not riders:
            return "No riders on duty."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} log:")
            if not rider.log:
                lines.append("  (no records)")
            for entry in rider.log:
                order = entry["order_id"] if entry["order_id"] is not None else "-"
                x, y = entry["location"]
                state = STATE_NAMES.get(entry["state"], "unknown")
                lines.append(
                    f"  t={entry['time']:>5}  {entry['event']:<22} "
                    f"order={str(order):<5} at ({x},{y})  state={state}"
                )
        return "\n".join(lines)

    def render_orders(self, orders: Sequence[Order]) -> str:
        """Render a table of all orders."""
        if not orders:
            return "No orders yet."
        header = (f"{'ID':<5}{'Start':>7}  {'Restaurant':<12}{'Customer':<12}"
                  f"{'Distance':>9}{'Taken':>7}  {'Rider':<7}{'Status':<12}")
        lines = [header, "-" * len(header)]
        for order in orders:
            restaurant = f"({order.res_pos.x},{order.res_pos.y})"
            customer = f"({order.cus_pos.x},{order.cus_pos.y})"
            taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else f"#{order.rider_id}"
            lines.append(
                f"{'#' + str(order.id):<5}{order.start_time:>7}  "
                f"{restaurant:<12}{customer:<12}{order.distance:>9}{taken:>7}  "
                f"{rider:<7}{order.status:<12}"
            )
        return "\n".join(lines)

    def render_delivery(self, order: Order) -> str:
        """Render a one-line delivery notice for a completed order."""
        return (f"  Order #{order.id} delivered at t={order.completion_time} "
                f"by rider #{order.rider_id} (time taken: {order.time_taken}, "
                f"distance: {order.distance})")
