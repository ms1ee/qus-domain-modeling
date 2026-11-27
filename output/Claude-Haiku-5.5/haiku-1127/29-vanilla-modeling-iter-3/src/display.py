"""Status displays, route summaries and ASCII map rendering."""

import math
from typing import Iterable, List, Optional, Sequence

from path_planner import PathPlanner, Point, manhattan
from rider import IDLE, Rider

from order_model import STATUS_COMPLETED


class DisplayManager:
    """Formats system state for the command line.

    Symbols: 'R' rider, 'S' restaurant, 'C' customer, '.' empty, '#' street,
    '*' route line.

    Attributes:
        planner: Planner providing map geometry.
        rider_symbol, restaurant_symbol, customer_symbol, empty_symbol,
        street_symbol, route_symbol: Characters used for rendering.
    """

    def __init__(
        self,
        planner: Optional[PathPlanner] = None,
        rider_symbol: str = "R",
        restaurant_symbol: str = "S",
        customer_symbol: str = "C",
        empty_symbol: str = ".",
        street_symbol: str = "#",
        route_symbol: str = "*",
    ) -> None:
        """Create a display manager with the given symbols."""
        self.planner = planner or PathPlanner()
        self.rider_symbol = rider_symbol
        self.restaurant_symbol = restaurant_symbol
        self.customer_symbol = customer_symbol
        self.empty_symbol = empty_symbol
        self.street_symbol = street_symbol
        self.route_symbol = route_symbol

    def _index(self, point: Sequence[int]) -> tuple:
        """Map a coordinate point to the rendering node indices (column, row)."""
        size = self.planner.nodes_per_side
        step = self.planner.step
        col = min(max((int(point[0]) + step // 2) // step, 0), size - 1)
        row = min(max((int(point[1]) + step // 2) // step, 0), size - 1)
        return col, row

    def _background(self, col: int, row: int) -> str:
        """Return the base symbol for a rendering node."""
        step = self.planner.step
        cell = self.planner.cell_size
        x = col * step
        y = row * step
        if x % cell == 0 or y % cell == 0:
            return self.street_symbol
        return self.empty_symbol

    def render_map(
        self,
        riders: Optional[Iterable[Rider]] = None,
        orders: Optional[Iterable] = None,
        route: Optional[Sequence[Point]] = None,
    ) -> str:
        """Render the 8x8 grid as ASCII.

        Points are drawn every 50 units so that cell centres are visible.
        Street lines (multiples of 100) are drawn with '#'.

        Args:
            riders: Riders to mark with 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') are shown
                if the order is not completed.
            route: Optional sequence of points to draw as a connected line.

        Returns:
            Multi-line string containing the map and a legend.
        """
        size = self.planner.nodes_per_side
        step = self.planner.step
        grid = [
            [self._background(col, row) for col in range(size)]
            for row in range(size)
        ]
        for point in route or []:
            col, row = self._index(point)
            grid[row][col] = self.route_symbol
        for order in orders or []:
            if order.status == STATUS_COMPLETED:
                continue
            col, row = self._index(order.res_pos)
            grid[row][col] = self.restaurant_symbol
            col, row = self._index(order.cus_pos)
            grid[row][col] = self.customer_symbol
        for rider in riders or []:
            col, row = self._index(rider.position)
            grid[row][col] = self.rider_symbol

        lines = []
        for row in reversed(range(size)):
            cells = " ".join(grid[row])
            lines.append(f"{row * step:>4} | {cells}")
        lines.append("     " + "-" * (2 * size))
        lines.append("x: 0 (left) to 800 (right); y: 0 (bottom) to 800 (top)")
        lines.append(
            "Legend: R=Rider S=Restaurant C=Customer .=Empty #=Street *=Route"
        )
        return "\n".join(lines)

    def format_status(self, system) -> str:
        """Return the system snapshot: funds, riders and their orders."""
        lines = [
            f"=== System Status (tick {system.current_tick}) ===",
            f"Funds: {system.funds}",
            f"Riders: {len(system.riders)}",
            f"Pending orders: {len(system.order_manager.pending)}",
        ]
        for rider in system.riders:
            order_ids = [order.id for order in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id}: location=({rider.x}, {rider.y}) "
                f"status={rider.state_name} orders={len(rider.orders)} "
                f"order_ids={order_ids} speed={rider.speed}"
                + (" special_case" if rider.special_case else "")
            )
        return "\n".join(lines)

    def format_orders(self, orders: Iterable) -> str:
        """Return a table of order details."""
        header = (
            f"{'ID':>4} | {'Start':>5} | {'Restaurant':<12} | {'Customer':<12} | "
            f"{'Distance':>8} | {'Taken':>5} | {'Rider':>5} | {'Status':<11} | Efficiency"
        )
        lines = ["=== Orders ===", header, "-" * len(header)]
        count = 0
        for order in orders:
            count += 1
            taken = str(order.time_taken) if order.time_taken is not None else "-"
            rider = str(order.rider_id) if order.rider_id is not None else "-"
            eff = order.efficiency
            eff_text = f"{eff:.2f}" if eff is not None else "-"
            lines.append(
                f"{order.id:>4} | {order.start_time:>5} | "
                f"{str(order.res_pos):<12} | {str(order.cus_pos):<12} | "
                f"{order.distance:>8.1f} | {taken:>5} | {rider:>5} | "
                f"{order.status:<11} | {eff_text}"
            )
        if count == 0:
            lines.append("No orders yet.")
        return "\n".join(lines)

    def format_rider_logs(self, riders: Iterable[Rider]) -> str:
        """Return every recorded status change for all riders, in time order."""
        entries = []
        for rider in riders:
            entries.extend(rider.log)
        entries.sort(key=lambda e: (e["tick"], e["rider_id"]))
        lines = ["=== Rider Status Changes ==="]
        if not entries:
            lines.append("No rider events recorded.")
        for entry in entries:
            order_text = (
                f"order #{entry['order_id']}" if entry["order_id"] is not None else "-"
            )
            lines.append(
                f"[tick {entry['tick']:>4}] Rider #{entry['rider_id']} "
                f"event={entry['event']:<20} location=({entry['x']}, {entry['y']}) "
                f"{order_text}"
            )
        return "\n".join(lines)

    def format_route_summary(self, order, rider: Rider, route: Sequence[Point]) -> str:
        """Describe the assigned route with speed and estimated time.

        Args:
            order: The newly assigned order.
            rider: The assigned rider.
            route: Full route including the starting position.

        Returns:
            Multi-line summary text.
        """
        length = sum(manhattan(route[i], route[i + 1]) for i in range(len(route) - 1))
        speed = max(rider.speed, 1)
        ticks = math.ceil(length / speed) if length else 0
        return "\n".join(
            [
                f"Order #{order.id} route for rider #{rider.rider_id}:",
                f"  Restaurant cell centre: {order.res_pos}",
                f"  Customer cell centre:   {order.cus_pos}",
                f"  Rider speed: {speed} units/tick",
                f"  Route length: {length} units",
                f"  Estimated time: {ticks} tick(s)",
            ]
        )
