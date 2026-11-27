"""Display management: status reports, order details and ASCII map."""

import math
from typing import Iterable, List, Optional, Sequence, Tuple

from order_model import Order
from path_planner import PathPlanner
from rider import Rider

MAP_CELLS = 16
MAP_STEP = 50  # units represented by one map character (800 / 16)
CELL_SIZE = 100

EVENT_LABELS = {
    "spawn": "spawned",
    "accepted_order": "accepted order",
    "arrived_at_merchant": "arrived at merchant",
    "delivered_to_customer": "delivered to customer",
}

MAP_LEGEND = "R rider | S restaurant | C customer | # street | * planned route | . empty"


def _map_index(coord: int) -> int:
    """Convert a map coordinate to a character index (0-15)."""
    return max(0, min(int(coord) // MAP_STEP, MAP_CELLS - 1))


class DisplayManager:
    """Formats system state for the command line."""

    def __init__(self, system) -> None:
        """Create the display bound to a SystemManager-like object.

        Args:
            system: Object exposing ``riders``, ``funds``, ``current_tick``
                and ``order_manager``.
        """
        self.system = system

    def format_status(self, issues: Sequence[str] = ()) -> str:
        """Return a snapshot of funds, riders and their orders.

        Args:
            issues: Consistency issues found and repaired during the check.

        Returns:
            Multi-line status text.
        """
        riders = self.system.riders
        pending = self.system.order_manager.pending_orders()
        lines = [
            "=== System Status ===",
            f"Tick: {self.system.current_tick}",
            f"System funds: {self.system.funds}",
            f"Riders: {len(riders)}",
            f"Pending orders: {len(pending)}",
        ]
        for rider in riders:
            active = [order.id for order in rider.active_orders()]
            special = "yes" if rider.special_case else "no"
            lines.append(
                f"  Rider #{rider.rider_id} | position ({rider.x}, {rider.y}) | "
                f"status: {rider.state_name} | speed: {rider.speed} | "
                f"assigned orders: {len(active)} {active if active else ''} | "
                f"special case: {special}"
            )
        if issues:
            lines.append("Consistency repairs:")
            lines.extend(f"  - {issue}" for issue in issues)
        else:
            lines.append("Consistency check: OK")
        return "\n".join(lines)

    def format_orders(self) -> str:
        """Return details for every order in the session."""
        orders: Iterable[Order] = self.system.order_manager._orders()
        lines = ["=== Orders ==="]
        orders = list(orders)
        if not orders:
            lines.append("No orders yet.")
            return "\n".join(lines)
        lines.append(
            "ID | start tick | restaurant | customer | distance | time taken | efficiency | rider | status"
        )
        for order in orders:
            taken = order.time_taken()
            taken_text = f"{taken} ticks" if taken is not None else "in progress"
            eff = order.efficiency()
            eff_text = f"{eff:.2f} u/tick" if eff is not None else "-"
            rider_text = f"#{order.rider_id}" if order.rider_id is not None else "-"
            lines.append(
                f"{order.id} | {order.created_tick} | {order.res_pos} | {order.cus_pos} | "
                f"{order.distance} units | {taken_text} | {eff_text} | {rider_text} | {order.status}"
            )
        return "\n".join(lines)

    def format_rider_log(self) -> str:
        """Return every recorded status change for all riders."""
        lines = ["=== Rider Event Log ==="]
        entries = []
        for rider in self.system.riders:
            for entry in rider.log:
                entries.append((entry["tick"], rider.rider_id, entry))
        if not entries:
            lines.append("No rider events recorded.")
            return "\n".join(lines)
        entries.sort(key=lambda item: (item[0], item[1]))
        for tick, rider_id, entry in entries:
            label = EVENT_LABELS.get(entry["event"], entry["event"])
            order_text = f"order #{entry['order_id']}" if entry["order_id"] is not None else "-"
            lines.append(
                f"[tick {tick}] Rider #{rider_id}: {label} | {order_text} | "
                f"position ({entry['x']}, {entry['y']}) | state {entry['state']}"
            )
        return "\n".join(lines)

    def render_map(self, route_points: Optional[Sequence[Tuple[int, int]]] = None) -> str:
        """Render the 16x16 ASCII map.

        Each character covers 50x50 units. Grid lines at multiples of 100 are
        drawn as streets. Active orders show restaurants (S) and customers (C),
        and riders are shown as R.

        Args:
            route_points: Optional points to highlight with '*'.

        Returns:
            Multi-line map text including a legend.
        """
        grid = [["." for _ in range(MAP_CELLS)] for _ in range(MAP_CELLS)]
        for row in range(MAP_CELLS):
            for col in range(MAP_CELLS):
                x = col * MAP_STEP
                y = row * MAP_STEP
                if x % CELL_SIZE == 0 or y % CELL_SIZE == 0:
                    grid[row][col] = "#"
        if route_points:
            for x, y in route_points:
                row, col = _map_index(y), _map_index(x)
                if grid[row][col] in ".#":
                    grid[row][col] = "*"
        for order in self.system.order_manager._orders():
            if order.status == "completed":
                continue
            row, col = _map_index(order.res_pos[1]), _map_index(order.res_pos[0])
            grid[row][col] = "S"
            row, col = _map_index(order.cus_pos[1]), _map_index(order.cus_pos[0])
            grid[row][col] = "C"
        for rider in self.system.riders:
            grid[_map_index(rider.y)][_map_index(rider.x)] = "R"
        lines = [f"Map (each character = {MAP_STEP} units, origin top-left)"]
        for row in range(MAP_CELLS):
            lines.append(f"{row * MAP_STEP:>4} " + " ".join(grid[row]))
        lines.append(MAP_LEGEND)
        return "\n".join(lines)

    def format_new_order(
        self, order: Order, rider: Optional[Rider], recruited: bool
    ) -> str:
        """Return the summary shown after the ``start`` command.

        Args:
            order: The newly created order.
            rider: Rider assigned to the order, or None.
            recruited: Whether a new rider was added for this order.

        Returns:
            Multi-line summary including the route map.
        """
        lines = [
            f"Order #{order.id} created.",
            f"Restaurant (grid cell corner): {order.res_pos}",
            f"Customer (grid cell corner): {order.cus_pos}",
            f"New rider added: {'yes' if recruited else 'no'}",
        ]
        if rider is None:
            lines.append("No rider is available. The order is pending and will be dispatched later.")
            lines.append(self.render_map())
            return "\n".join(lines)

        route = PathPlanner.plan_route(rider.position, [order.res_pos, order.cus_pos])
        length = PathPlanner.route_length(rider.position, route)
        ticks = math.ceil(length / rider.speed) if rider.speed > 0 else 0
        points = PathPlanner.trace_points(rider.position, route)
        lines.extend(
            [
                f"Assigned rider: #{rider.rider_id} at ({rider.x}, {rider.y}), "
                f"status {rider.state_name}, active orders {len(rider.active_orders())}",
                f"Speed: {rider.speed} units/tick",
                f"Route: rider -> restaurant -> customer, length {length} units",
                f"Estimated time: {ticks} ticks",
                "Route map:",
                self.render_map(points),
            ]
        )
        return "\n".join(lines)
