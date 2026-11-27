"""Status display and ASCII map visualisation."""

from typing import Iterable, List, Optional, Sequence, Set, Tuple

from order_model import STATUS_COMPLETED, Order
from path_planner import CELL_SIZE, GRID_CELLS, PathPlanner
from rider import Rider

Point = Tuple[int, int]

SYMBOL_EMPTY = "."
SYMBOL_STREET = "#"
SYMBOL_CUSTOMER = "C"
SYMBOL_RESTAURANT = "S"
SYMBOL_RIDER = "R"

_PRIORITY = {
    SYMBOL_EMPTY: 0,
    SYMBOL_STREET: 1,
    SYMBOL_CUSTOMER: 2,
    SYMBOL_RESTAURANT: 3,
    SYMBOL_RIDER: 4,
}


class DisplayManager:
    """Formats system status, order tables, rider logs and the map."""

    @staticmethod
    def _cell_label(x: int, y: int) -> str:
        """Return a readable grid-cell label such as ``(4,3)``."""
        col, row = PathPlanner.cell_of(x, y)
        return f"({col},{row})"

    def render_status(self, system) -> str:
        """Render funds, time and a snapshot of every rider.

        Args:
            system: The SystemManager instance.

        Returns:
            Multi-line status text.
        """
        lines = [
            f"System time : tick {system.time}",
            f"System funds: {system.funds}",
            f"Riders      : {len(system.riders)}",
        ]
        if not system.riders:
            lines.append("  (no riders recruited yet)")
        for rider in system.riders:
            order_ids = [order.id for order in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id}: location=({rider.x}, {rider.y}) "
                f"cell={self._cell_label(rider.x, rider.y)} "
                f"state={rider.state_name} speed={rider.speed} "
                f"orders={len(rider.orders)} {order_ids}"
            )
        return "\n".join(lines)

    def render_orders(self, orders: Iterable[Order]) -> str:
        """Render a table of all orders.

        Args:
            orders: Orders to display.

        Returns:
            Multi-line table text.
        """
        orders = list(orders)
        header = (
            f"{'ID':>4} {'Start':>6} {'Restaurant':>14} {'Customer':>14} "
            f"{'Dist':>6} {'Taken':>6} {'Rider':>6} {'Status':>10}"
        )
        lines = [header, "-" * len(header)]
        if not orders:
            lines.append("(no orders yet)")
        for order in orders:
            restaurant = f"({order.res_pos[0]},{order.res_pos[1]})"
            customer = f"({order.cus_pos[0]},{order.cus_pos[1]})"
            taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else f"#{order.rider_id}"
            lines.append(
                f"{order.id:>4} {order.start_time:>6} {restaurant:>14} {customer:>14} "
                f"{order.distance:>6} {taken:>6} {rider:>6} {order.status:>10}"
            )
        return "\n".join(lines)

    def render_rider_log(self, riders: Sequence[Rider]) -> str:
        """Render every status-change entry for all riders.

        Args:
            riders: Riders whose logs should be shown.

        Returns:
            Multi-line log text.
        """
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} (current: {rider.state_name})")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                lines.append(
                    f"  t={entry['time']:>5}  {entry['event']:<22} order={order:<6} "
                    f"location=({entry['x']}, {entry['y']})"
                )
        if not lines:
            return "(no riders recruited yet)"
        return "\n".join(lines)

    def render_map(
        self,
        riders: Sequence[Rider],
        orders: Iterable[Order],
        trail: Optional[Iterable[Point]] = None,
    ) -> str:
        """Render the 8x8 ASCII map.

        Symbols: 'R' rider, 'S' restaurant, 'C' customer, '#' street/route,
        '.' empty. Only active (not completed) orders are drawn. When several
        symbols share a cell, the higher-priority one is shown (R > S > C > #).

        Args:
            riders: Riders to draw.
            orders: Orders whose restaurant/customer markers are drawn.
            trail: Optional sequence of points whose cells are drawn as route.

        Returns:
            Multi-line map text.
        """
        grid = [[SYMBOL_EMPTY] * GRID_CELLS for _ in range(GRID_CELLS)]

        def place(point: Point, symbol: str) -> None:
            col, row = PathPlanner.cell_of(point[0], point[1])
            if _PRIORITY[symbol] >= _PRIORITY[grid[row][col]]:
                grid[row][col] = symbol

        for x, y in trail or []:
            place((x, y), SYMBOL_STREET)
        for order in orders:
            if order.status == STATUS_COMPLETED:
                continue
            place(order.cus_pos, SYMBOL_CUSTOMER)
            place(order.res_pos, SYMBOL_RESTAURANT)
        for rider in riders:
            place((rider.x, rider.y), SYMBOL_RIDER)

        lines = ["Map (rows = y cell, columns = x cell; each cell is 100x100 units):"]
        lines.append(" " * 16 + "  ".join(str(col) for col in range(GRID_CELLS)))
        for row in reversed(range(GRID_CELLS)):
            cells = "  ".join(grid[row][col] for col in range(GRID_CELLS))
            lines.append(f"row {row} [y {row * CELL_SIZE:>3}] | {cells}")
        lines.append(
            "Legend: R rider, S restaurant, C customer, # route/street, . empty"
        )
        return "\n".join(lines)

    def render_route(
        self,
        order: Order,
        rider: Rider,
        trail: Sequence[Point],
        ticks: int,
        new_rider: bool,
    ) -> str:
        """Render the route summary and route map for an assigned order.

        Args:
            order: The order that was dispatched.
            rider: The rider that serves the order.
            trail: Positions of the rider at every tick, starting at the
                position before the first move.
            ticks: Number of simulation ticks the trip took.
            new_rider: Whether a new rider was recruited for this order.

        Returns:
            Multi-line report text.
        """
        route_cells: Set[Tuple[int, int]] = {PathPlanner.cell_of(x, y) for x, y in trail}
        res_cell = PathPlanner.cell_of(order.raw_res_pos[0], order.raw_res_pos[1])
        cus_cell = PathPlanner.cell_of(order.raw_cus_pos[0], order.raw_cus_pos[1])
        pickup = "-" if order.pickup_time is None else str(order.pickup_time)
        done = "-" if order.complete_time is None else str(order.complete_time)
        lines = [
            f"Order #{order.id} assigned to Rider #{rider.rider_id}",
            f"Restaurant: input {order.raw_res_pos} -> grid cell {res_cell} "
            f"-> centre {order.res_pos}",
            f"Customer  : input {order.raw_cus_pos} -> grid cell {cus_cell} "
            f"-> centre {order.cus_pos}",
            f"New rider added: {'yes' if new_rider else 'no'}",
            f"Rider speed: {rider.speed} units/tick",
            f"Time: started tick {order.start_time}, picked up tick {pickup}, "
            f"delivered tick {done} (trip ticks: {ticks})",
            f"Route cells visited: {len(route_cells)}",
            "",
            self.render_map([rider], [order], trail),
        ]
        return "\n".join(lines)
