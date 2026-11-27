"""Status display and ASCII map rendering."""

from typing import Any, List, Optional, Sequence, Tuple

import globalvar
from order_model import ORDER_COMPLETED, ORDER_PENDING
from path_planner import PathPlanner
from rider import STATE_LABELS

Point = Tuple[int, int]


class DisplayManager:
    """Builds text output for status, orders, rider logs and the map.

    The ASCII map uses one character per 50 units, so the 800x800 area is
    drawn as 17x17 nodes (16 cells in each direction plus the boundary).
    Legend: R rider, S restaurant, C customer, # street, * route, . empty.

    Attributes:
        system: The SystemManager providing riders and funds.
    """

    MAP_STEP = 50
    MAP_CELLS = 17

    def __init__(self, system: Any) -> None:
        """Bind the display to a SystemManager.

        Args:
            system: SystemManager instance.
        """
        self.system = system

    @staticmethod
    def _all_orders() -> List[Any]:
        """Return all orders recorded in the global store."""
        return list(globalvar.get_value("orders") or [])

    def render_status(self) -> str:
        """Return a snapshot of funds, riders and their order lists."""
        riders = self.system.riders
        pending = [o for o in self._all_orders() if o.status == ORDER_PENDING]
        lines = [
            "=== System Status ===",
            f"Tick: {globalvar.current_tick()}",
            f"System funds: {self.system.funds}",
            f"Riders: {len(riders)}",
            f"Pending orders: {len(pending)}",
        ]
        if not riders:
            lines.append("No riders on duty.")
        for rider in riders:
            lines.append(
                f"Rider #{rider.rider_id}: location=({rider.x}, {rider.y}) "
                f"status={STATE_LABELS[rider.state]} "
                f"active_orders={rider.active_order_count()} "
                f"total_orders={len(rider.orders)}"
            )
            for order in rider.orders:
                lines.append(
                    f"    order #{order.id}: {order.status} "
                    f"restaurant={order.res_pos} customer={order.cus_pos}"
                )
        return "\n".join(lines)

    def render_orders(self) -> str:
        """Return a table of all orders with delivery details."""
        orders = self._all_orders()
        header = (
            f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
            f"{'Dist':>6} {'Status':>10} {'Taken':>6} {'Rider':>6} {'Eff':>7}"
        )
        if not orders:
            return "No orders yet."
        lines = ["=== Orders ===", header]
        for o in orders:
            taken = "-" if o.time_taken is None else str(o.time_taken)
            eff = "-" if o.efficiency is None else f"{o.efficiency:.2f}"
            rider = "-" if o.rider_id is None else f"#{o.rider_id}"
            lines.append(
                f"{o.id:>4} {o.start_time:>6} {str(o.res_pos):>12} {str(o.cus_pos):>12} "
                f"{o.distance:>6} {o.status:>10} {taken:>6} {rider:>6} {eff:>7}"
            )
        return "\n".join(lines)

    def render_rider_log(self) -> str:
        """Return every recorded status change of every rider."""
        lines = ["=== Rider Status Log ==="]
        any_entry = False
        for rider in self.system.riders:
            for entry in rider.log:
                any_entry = True
                order = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                lines.append(
                    f"t={entry['time']:>4} rider #{entry['rider_id']:<3} "
                    f"{entry['event']:<22} order={order:<5} "
                    f"at ({entry['x']}, {entry['y']}) "
                    f"state={STATE_LABELS[entry['state']]}"
                )
        if not any_entry:
            lines.append("No rider events recorded.")
        return "\n".join(lines)

    @classmethod
    def _axis_index(cls, value: float) -> int:
        """Map a coordinate to a column/row index of the ASCII map."""
        idx = (int(round(value)) + cls.MAP_STEP // 2) // cls.MAP_STEP
        return min(max(idx, 0), cls.MAP_CELLS - 1)

    @classmethod
    def _grid_index(cls, x: float, y: float) -> Tuple[int, int]:
        """Return ``(col, row)`` for a map coordinate; row 0 is the top (y=800)."""
        col = cls._axis_index(x)
        row = cls.MAP_CELLS - 1 - cls._axis_index(y)
        return col, row

    @classmethod
    def _walk(cls, a: Point, b: Point) -> List[Tuple[int, int]]:
        """Return grid cells visited when walking axis-aligned from a to b."""
        c, r = cls._grid_index(a[0], a[1])
        c1, r1 = cls._grid_index(b[0], b[1])
        cells = [(c, r)]
        while (c, r) != (c1, r1):
            if c != c1:
                c += 1 if c1 > c else -1
            else:
                r += 1 if r1 > r else -1
            cells.append((c, r))
        return cells

    def render_map(self, route: Optional[Sequence[Point]] = None) -> str:
        """Render the ASCII map with streets, riders, orders and an optional route.

        Args:
            route: Optional ordered route points to draw as a connected line.

        Returns:
            Multi-line string containing the map and a legend.
        """
        n = self.MAP_CELLS
        grid = [["." for _ in range(n)] for _ in range(n)]
        for row in range(n):
            y = (n - 1 - row) * self.MAP_STEP
            for col in range(n):
                x = col * self.MAP_STEP
                if PathPlanner.is_street(x, y):
                    grid[row][col] = "#"
        if route:
            for a, b in zip(route, route[1:]):
                for col, row in self._walk(a, b):
                    grid[row][col] = "*"
        for order in self._all_orders():
            if order.status == ORDER_COMPLETED:
                continue
            col, row = self._grid_index(*order.res_pos)
            grid[row][col] = "S"
            col, row = self._grid_index(*order.cus_pos)
            grid[row][col] = "C"
        for rider in self.system.riders:
            col, row = self._grid_index(rider.x, rider.y)
            grid[row][col] = "R"

        lines = ["Map (y increases upward, 1 char = 50 units):"]
        for row in range(n):
            y = (n - 1 - row) * self.MAP_STEP
            label = f"{y:>4} " if y % 200 == 0 else "     "
            lines.append(label + " ".join(grid[row]))
        lines.append("     x: 0 (left) to 800 (right)")
        lines.append("Legend: R rider  S restaurant  C customer  # street  * route  . empty")
        return "\n".join(lines)

    def render_start_result(self, result: dict) -> str:
        """Render the response to a ``start`` command.

        Args:
            result: Dictionary returned by ``OrderManager.submit``.

        Returns:
            Formatted multi-line text.
        """
        order = result["order"]
        lines = [
            f"Order #{order.id} created at tick {order.start_time}",
            f"Restaurant grid point: {order.res_pos}",
            f"Customer grid point: {order.cus_pos}",
            f"Street distance: {order.distance} units",
        ]
        rider = result["rider"]
        if rider is None:
            lines.append(
                f"No rider available (funds: {self.system.funds}). Order remains pending."
            )
            return "\n".join(lines)
        new_rider = result["new_rider"]
        if new_rider is not None:
            lines.append(f"New rider added: #{new_rider.rider_id} (funds: {self.system.funds})")
        else:
            lines.append("New rider added: no")
        lines.append(
            f"Assigned rider: #{rider.rider_id} at ({rider.x}, {rider.y}) "
            f"speed {rider.speed} units/tick, active orders {rider.active_order_count()}"
        )
        eta = result["eta"]
        lines.append(
            f"Route length: {result['distance']} units; estimated time: "
            f"{eta if eta is not None else '-'} ticks"
        )
        lines.append(self.render_map(route=result["route"]))
        return "\n".join(lines)
