"""Status text and ASCII map rendering for the dispatch simulator.

Map symbols: 'R' rider, 'S' restaurant, 'C' customer, '.' empty grid cell,
'#' street segment on the highlighted route. The 8x8 cells are drawn at even
character positions; connectors between cells sit at odd positions. Columns
run left to right (x) and rows run top to bottom (y).
"""

from typing import Iterable, List, Optional, Sequence, Tuple

from order_model import STATUS_COMPLETED
from pathplanner import GRID_SIZE, grid_cell
from rider import STATE_NAMES

SYMBOL_RIDER = "R"
SYMBOL_RESTAURANT = "S"
SYMBOL_CUSTOMER = "C"
SYMBOL_EMPTY = "."
SYMBOL_STREET = "#"


class DisplayManager:
    """Formats the system state for the command line."""

    def render_map(self, riders: Iterable, orders: Iterable,
                   route_points: Optional[Sequence[Tuple[int, int]]] = None) -> str:
        """Render the 8x8 ASCII map.

        Args:
            riders: Riders whose positions are shown as 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') cells are
                shown. Completed orders are skipped.
            route_points: Optional route as ``(x, y)`` points; the streets
                between consecutive points are drawn with '#'.

        Returns:
            Multi-line string containing the map.
        """
        size = 2 * GRID_SIZE - 1
        canvas: List[List[str]] = [[" "] * size for _ in range(size)]
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                canvas[2 * row][2 * col] = SYMBOL_EMPTY

        if route_points:
            previous = None
            for point in route_points:
                cell = grid_cell(point[0], point[1])
                if previous is not None and previous != cell:
                    c1, r1 = previous
                    c2, r2 = cell
                    if (c1 == c2) != (r1 == r2):
                        canvas[r1 + r2][c1 + c2] = SYMBOL_STREET
                previous = cell

        for order in orders:
            if order.status == STATUS_COMPLETED:
                continue
            col, row = grid_cell(*order.res_pos)
            canvas[2 * row][2 * col] = SYMBOL_RESTAURANT
            col, row = grid_cell(*order.cus_pos)
            canvas[2 * row][2 * col] = SYMBOL_CUSTOMER

        for rider in riders:
            col, row = grid_cell(rider.x, rider.y)
            canvas[2 * row][2 * col] = SYMBOL_RIDER

        lines = ["Map (x: column 0-7 left->right, y: row 0-7 top->bottom)"]
        header = "  " + " ".join(str(j // 2) if j % 2 == 0 else " " for j in range(size))
        lines.append(header)
        for i in range(size):
            label = str(i // 2) if i % 2 == 0 else " "
            lines.append(f"{label} " + " ".join(canvas[i]))
        lines.append("Legend: R=Rider S=Restaurant C=Customer .=Empty #=Street(route)")
        return "\n".join(lines)

    def format_status(self, funds: int, tick: int, riders: Sequence,
                      pending_count: int) -> str:
        """Format a snapshot of the system state.

        Args:
            funds: Current system funds.
            tick: Current simulated tick.
            riders: List of riders.
            pending_count: Number of orders waiting for a rider.

        Returns:
            Multi-line status text.
        """
        lines = [
            f"Tick: {tick}",
            f"System funds: {funds}",
            f"Riders: {len(riders)}   Pending orders: {pending_count}",
        ]
        for rider in riders:
            order_ids = [order.id for order in rider.orders]
            lines.append(
                f"  Rider {rider.rider_id}: pos=({rider.x},{rider.y}) "
                f"state={rider.state}({STATE_NAMES.get(rider.state, '?')}) "
                f"speed={rider.speed} orders={order_ids} "
                f"special_case={rider.special_case}"
            )
        if not riders:
            lines.append("  No riders on duty.")
        return "\n".join(lines)

    def format_orders(self, orders: Sequence) -> str:
        """Format the order table.

        Args:
            orders: All orders (history).

        Returns:
            Multi-line table text.
        """
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Distance':>9} {'Taken':>6} {'Rider':>6} {'Status':>12}")
        lines = [header, "-" * len(header)]
        for order in orders:
            taken = order.time_taken if order.time_taken is not None else "-"
            rider = order.rider_id if order.rider_id is not None else "-"
            restaurant = f"({order.res_pos[0]},{order.res_pos[1]})"
            customer = f"({order.cus_pos[0]},{order.cus_pos[1]})"
            lines.append(
                f"{order.id:>4} {order.start_tick:>6} {restaurant:>12} {customer:>12} "
                f"{order.distance:>9} {str(taken):>6} {str(rider):>6} {order.status:>12}"
            )
        return "\n".join(lines)

    def format_rider_logs(self, riders: Sequence) -> str:
        """Format every status change recorded by every rider.

        Args:
            riders: Riders whose logs should be shown.

        Returns:
            Multi-line log text.
        """
        if not riders:
            return "No riders on duty."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider {rider.rider_id}:")
            for entry in rider.log:
                order_text = entry["order_id"] if entry["order_id"] is not None else "-"
                lines.append(
                    f"  tick={entry['tick']:<5} event={entry['event']:<22} "
                    f"order={order_text:<5} pos=({entry['x']},{entry['y']}) "
                    f"state={entry['state']}"
                )
        return "\n".join(lines)

    def format_route(self, rider_speed: int, distance: int, eta: Optional[int]) -> str:
        """Describe a planned route including speed and time.

        Args:
            rider_speed: Speed of the assigned rider (units per tick).
            distance: Planned route length in units.
            eta: Estimated ticks to finish, or None.

        Returns:
            Single-line description.
        """
        eta_text = f"{eta} ticks" if eta is not None else "unknown"
        return (f"Planned route: {distance} units at speed {rider_speed} units/tick, "
                f"estimated time {eta_text}")
