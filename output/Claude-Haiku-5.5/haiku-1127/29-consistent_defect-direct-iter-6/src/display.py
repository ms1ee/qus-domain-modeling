"""Status displays and ASCII map visualisation."""

from typing import Any, Iterable, List, Optional, Sequence

from order_model import STATUS_COMPLETED
from path_planner import DISPLAY_STEP, Point, expand_route

MAP_CELLS = 16
EMPTY = "."
STREET = "#"
ROUTE = "*"
RIDER = "R"
RESTAURANT = "S"
CUSTOMER = "C"


def _index(value: int) -> int:
    """Map a coordinate (0-800) to a character index (0-15)."""
    return max(0, min(MAP_CELLS - 1, int(value) // DISPLAY_STEP))


class DisplayManager:
    """Renders the map, rider status, orders and rider history as text."""

    def render_map(self, riders: Iterable[Any], orders: Optional[Sequence[Any]] = None,
                   route: Optional[Sequence[Point]] = None) -> str:
        """Render the 16x16 ASCII map.

        Each character represents 50x50 units. Streets are drawn with '#'
        and empty blocks with '.'. The route, if given, is drawn with '*'.
        Restaurants ('S') and customers ('C') from active orders are drawn,
        followed by riders ('R').

        Args:
            riders: Riders to display.
            orders: Orders whose locations should be shown.
            route: Optional polyline (start point included) to highlight.

        Returns:
            The multi-line map string.
        """
        grid = [
            [STREET if (c % 2 == 0 or r % 2 == 0) else EMPTY for c in range(MAP_CELLS)]
            for r in range(MAP_CELLS)
        ]

        def place(point: Point, symbol: str) -> None:
            grid[_index(point[1])][_index(point[0])] = symbol

        if route:
            for point in expand_route(list(route)):
                place(point, ROUTE)
        for order in orders or []:
            if order.status == STATUS_COMPLETED:
                continue
            place(order.res_pos, RESTAURANT)
            place(order.cus_pos, CUSTOMER)
        for rider in riders:
            place(rider.position, RIDER)

        border = "+" + "-" * MAP_CELLS + "+"
        lines = [border]
        lines.extend("|" + "".join(row) + "|" for row in grid)
        lines.append(border)
        lines.append("Legend: R rider  S restaurant  C customer  # street  "
                     ". empty  * route")
        lines.append("Map 800x800 units, 8x8 blocks of 100 units, "
                     "one character = 50 units, origin top-left.")
        return "\n".join(lines)

    def render_status(self, funds: int, riders: Sequence[Any]) -> str:
        """Render the status snapshot.

        Args:
            funds: Current system funds.
            riders: All riders.

        Returns:
            Multi-line status text.
        """
        lines: List[str] = [
            f"System funds: {funds}",
            f"Riders: {len(riders)}",
        ]
        for rider in riders:
            lines.append(
                f"  Rider #{rider.rider_id}: position=({rider.x}, {rider.y}) "
                f"status={rider.state_name} assigned_orders={len(rider.active_orders())} "
                f"speed={rider.speed} special_case={rider.special_case}"
            )
            if not rider.orders:
                lines.append("    orders: none")
            for order in rider.orders:
                lines.append(f"    Order #{order.id}: {order.status}")
        return "\n".join(lines)

    def render_orders(self, orders: Sequence[Any]) -> str:
        """Render a table of all orders.

        Args:
            orders: Orders to display.

        Returns:
            Multi-line table text.
        """
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Distance':>8} {'Taken':>6} {'Rider':>6} {'Status':<11} {'Eff/tick':>8}")
        lines = [header, "-" * len(header)]
        for o in orders:
            rest = f"({o.res_pos[0]},{o.res_pos[1]})"
            cust = f"({o.cus_pos[0]},{o.cus_pos[1]})"
            taken = o.time_taken if o.time_taken is not None else "-"
            rider = o.rider_id if o.rider_id is not None else "-"
            eff = f"{o.efficiency:.2f}" if o.efficiency is not None else "-"
            lines.append(
                f"{o.id:>4} {o.start_time:>6} {rest:>12} {cust:>12} "
                f"{o.distance:>8} {str(taken):>6} {str(rider):>6} {o.status:<11} {eff:>8}"
            )
        return "\n".join(lines)

    def render_rider_history(self, riders: Sequence[Any]) -> str:
        """Render every recorded status change for all riders.

        Args:
            riders: Riders whose logs should be shown.

        Returns:
            Multi-line log text ordered by rider, then time.
        """
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} ({len(rider.log)} events):")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order_text = entry["order_id"] if entry["order_id"] is not None else "-"
                lines.append(
                    f"  [t={entry['time']:>5}] {entry['event']:<20} "
                    f"order={order_text!s:<5} pos=({entry['x']},{entry['y']}) "
                    f"state={entry['state']}"
                )
        return "\n".join(lines) if lines else "No riders yet."
