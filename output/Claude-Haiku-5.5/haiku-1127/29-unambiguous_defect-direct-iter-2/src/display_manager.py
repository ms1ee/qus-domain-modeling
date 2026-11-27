"""Status reports and ASCII map visualisation."""

import logging
from typing import Any, Iterable, List, Optional, Sequence, Tuple

from order_model import STATUS_ASSIGNED
from path_planner import CELL_SIZE, GRID_SIZE, MAP_SIZE, NODE_COUNT, PathPlanner, Point
from rider import STATE_NAMES

logger = logging.getLogger(__name__)


class DisplayManager:
    """Formats system status and renders the ASCII map.

    The map is drawn on a character canvas of ``2*GRID_SIZE+1`` cells square:
    intersections sit on even rows/columns, streets are drawn between them,
    and blocks are the empty positions at odd/odd coordinates.

    Symbols:
        ``+`` intersection, ``-`` / ``|`` street, `` `` empty block,
        ``*`` planned route, ``R`` restaurant, ``C`` customer,
        ``0``-``9`` rider (rider ID modulo 10).
    """

    SYMBOL_INTERSECTION = "+"
    SYMBOL_STREET_H = "-"
    SYMBOL_STREET_V = "|"
    SYMBOL_EMPTY = " "
    SYMBOL_ROUTE = "*"
    SYMBOL_RESTAURANT = "R"
    SYMBOL_CUSTOMER = "C"

    def __init__(self) -> None:
        self._size = 2 * GRID_SIZE + 1

    @staticmethod
    def to_char(x: int, y: int) -> Tuple[int, int]:
        """Convert a map point to a ``(row, col)`` canvas position.

        Row 0 is the top of the map (``y = 800``).
        """
        size = 2 * GRID_SIZE
        col = int(round(x * 2 / CELL_SIZE))
        row = int(round(size - y * 2 / CELL_SIZE))
        return max(0, min(size, row)), max(0, min(size, col))

    def render_map(
        self,
        riders: Iterable[Any],
        orders: Optional[Iterable[Any]] = None,
        route: Optional[Sequence[Point]] = None,
    ) -> str:
        """Render the street map with riders, orders and an optional route.

        Args:
            riders: Riders to display (by position and ID).
            orders: Orders whose restaurant (R) and customer (C) to display.
            route: Optional list of points drawn as a connected line.

        Returns:
            Multi-line string containing the map and a legend.
        """
        size = self._size
        canvas = [[self.SYMBOL_EMPTY] * size for _ in range(size)]

        for i in range(NODE_COUNT):
            for j in range(NODE_COUNT):
                row, col = self.to_char(i * CELL_SIZE, j * CELL_SIZE)
                canvas[row][col] = self.SYMBOL_INTERSECTION
                if i < GRID_SIZE:
                    canvas[row][col + 1] = self.SYMBOL_STREET_H
                if j < GRID_SIZE:
                    canvas[row - 1][col] = self.SYMBOL_STREET_V

        if route:
            points = [self.to_char(x, y) for x, y in route]
            for (r1, c1), (r2, c2) in zip(points, points[1:]):
                if r1 == r2:
                    for c in range(min(c1, c2), max(c1, c2) + 1):
                        canvas[r1][c] = self.SYMBOL_ROUTE
                elif c1 == c2:
                    for r in range(min(r1, r2), max(r1, r2) + 1):
                        canvas[r][c1] = self.SYMBOL_ROUTE
            for row, col in points:
                canvas[row][col] = self.SYMBOL_ROUTE

        for rider in riders:
            row, col = self.to_char(rider.x, rider.y)
            canvas[row][col] = str(rider.rider_id % 10)

        for order in orders or []:
            if order.status not in (STATUS_ASSIGNED, "pending"):
                continue
            row, col = self.to_char(*order.res_pos)
            canvas[row][col] = self.SYMBOL_RESTAURANT
            row, col = self.to_char(*order.cus_pos)
            canvas[row][col] = self.SYMBOL_CUSTOMER

        lines = []
        for r in range(size):
            if r % 2 == 0:
                label = f"{MAP_SIZE - (r // 2) * CELL_SIZE:>4} |"
            else:
                label = "     |"
            lines.append(label + "".join(canvas[r]))
        lines.append("     +" + "-" * size)
        lines.append("      x: 0 (left) to 800 (right); grid lines every 100 units")
        lines.append(self.legend())
        return "\n".join(lines)

    @staticmethod
    def legend() -> str:
        """Return the map legend."""
        return (
            "Legend: + intersection  - | street  * route  R restaurant  "
            "C customer  0-9 rider (id mod 10)"
        )

    def status_report(self, funds: int, riders: Sequence[Any], tick: int) -> str:
        """Return the system status snapshot as text."""
        lines = [
            f"System funds : {funds}",
            f"Simulated tick: {tick}",
            f"Rider count  : {len(riders)}",
        ]
        for rider in riders:
            order_ids = ", ".join(str(o.id) for o in rider.orders) or "-"
            lines.append(
                f"  Rider {rider.rider_id:<3} pos=({rider.x},{rider.y})  "
                f"state={STATE_NAMES.get(rider.state, 'unknown'):<11} "
                f"orders={len(rider.orders)} [{order_ids}]  "
                f"special={'yes' if rider.special_case else 'no'}"
            )
        return "\n".join(lines)

    @staticmethod
    def orders_report(orders: Sequence[Any]) -> str:
        """Return a table of all orders with timing and efficiency data."""
        if not orders:
            return "No orders yet."
        header = (
            f"{'ID':>4} {'start':>6} {'restaurant':>12} {'customer':>12} "
            f"{'dist':>6} {'taken':>6} {'rider':>6} {'status':<10} {'eff':>6}"
        )
        lines = [header, "-" * len(header)]
        for o in orders:
            rider = "-" if o.rider_id is None else str(o.rider_id)
            taken = "-" if o.time_taken is None else str(o.time_taken)
            eff = "-" if o.efficiency is None else f"{o.efficiency:.2f}"
            lines.append(
                f"{o.id:>4} {o.start_tick:>6} {str(o.res_pos):>12} {str(o.cus_pos):>12} "
                f"{o.distance:>6} {taken:>6} {rider:>6} {o.status:<10} {eff:>6}"
            )
        return "\n".join(lines)

    @staticmethod
    def riders_report(riders: Sequence[Any]) -> str:
        """Return the status-change log of every rider."""
        if not riders:
            return "No riders recruited yet."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider {rider.rider_id}:")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else str(entry["order_id"])
                lines.append(
                    f"  t={entry['tick']:>5}  {entry['event']:<22} order={order:<5} "
                    f"pos=({entry['x']},{entry['y']})  "
                    f"state={STATE_NAMES.get(entry['state'], 'unknown')}"
                )
        return "\n".join(lines)

    @staticmethod
    def order_report(
        order: Any,
        rider: Any,
        route_length: int,
        estimated_ticks: int,
        is_new: bool,
    ) -> str:
        """Return the summary shown after a successful ``start`` command."""
        res = order.res_pos
        cus = order.cus_pos
        lines = [
            f"Order #{order.id} accepted at tick {order.start_tick}.",
            f"  Restaurant grid point: {res}  cell={(PathPlanner.cell_index(res[0]), PathPlanner.cell_index(res[1]))}"
            f"  centre=({PathPlanner.grid_center(res[0])}, {PathPlanner.grid_center(res[1])})",
            f"  Customer grid point  : {cus}  cell={(PathPlanner.cell_index(cus[0]), PathPlanner.cell_index(cus[1]))}"
            f"  centre=({PathPlanner.grid_center(cus[0])}, {PathPlanner.grid_center(cus[1])})",
            f"  Assigned rider: #{rider.rider_id} "
            f"({'newly recruited' if is_new else 'existing rider'}), "
            f"state={STATE_NAMES.get(rider.state, 'unknown')}, queued orders={len(rider.orders)}",
            f"  Rider speed: {rider.speed} units/tick",
            f"  Route length: {route_length} units, estimated time: {estimated_ticks} ticks",
            "  Planned route (* = path):",
        ]
        return "\n".join(lines)
