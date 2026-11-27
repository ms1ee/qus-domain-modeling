"""Text rendering: status snapshots, order tables, rider history, and the ASCII map."""

from typing import Iterable, List, Optional, Sequence, Set, Tuple

from order_model import STATUS_COMPLETED
from path_planner import BLOCK_SIZE, MAP_SIZE
from rider import STATE_NAMES, Rider

MAP_STEP = 50  # map resolution: one character every 50 units


class DisplayManager:
    """Formats simulator output for the command line.

    Map symbols: ``R`` restaurant, ``C`` customer, ``+`` intersection,
    ``-`` horizontal street, ``|`` vertical street, ``*`` route, digits
    ``0``-``9`` riders (rider ID modulo 10), and a blank for empty space.
    """

    LEGEND = (
        "Legend: R restaurant  C customer  + intersection  - | street  "
        "* route  0-9 riders (ID mod 10)  blank = empty"
    )

    def format_status(self, funds: int, riders: Sequence[Rider], tick: int, max_riders: int) -> str:
        """Return a snapshot of funds and every rider's state.

        Args:
            funds: Current system fund balance.
            riders: All riders.
            tick: Current simulation tick.
            max_riders: Configured maximum number of riders.
        """
        lines = [
            f"=== System status (tick {tick}) ===",
            f"System funds: {funds}",
            f"Riders: {len(riders)} / {max_riders}",
        ]
        if not riders:
            lines.append("No riders on duty.")
            return "\n".join(lines)
        lines.append(f"{'ID':>4} {'Position':>12} {'State':<12} {'Orders':>6}  Order IDs")
        for rider in riders:
            ids = ", ".join(str(o.id) for o in rider.orders) or "-"
            position = f"({rider.x}, {rider.y})"
            lines.append(
                f"{rider.rider_id:>4} {position:>12} {STATE_NAMES.get(rider.state, '?'):<12} "
                f"{len(rider.orders):>6}  {ids}"
            )
        return "\n".join(lines)

    def format_orders(self, orders: Sequence) -> str:
        """Return a table of all orders.

        Args:
            orders: Order objects to display.
        """
        if not orders:
            return "No orders yet."
        lines = [
            f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
            f"{'Distance':>8} {'Time':>6} {'Rider':>6}  Status"
        ]
        for o in orders:
            time_text = str(o.time_taken) if o.time_taken is not None else "-"
            rider_text = str(o.rider_id) if o.rider_id is not None else "-"
            restaurant = f"({o.res_pos[0]}, {o.res_pos[1]})"
            customer = f"({o.cus_pos[0]}, {o.cus_pos[1]})"
            lines.append(
                f"{o.id:>4} {o.start_time:>6} {restaurant:>12} {customer:>12} "
                f"{o.distance:>8} {time_text:>6} {rider_text:>6}  {o.status}"
            )
        return "\n".join(lines)

    def format_rider_history(self, riders: Sequence[Rider]) -> str:
        """Return every recorded status change for all riders.

        Args:
            riders: Riders whose logs should be shown.
        """
        if not riders:
            return "No riders."
        blocks: List[str] = []
        for rider in riders:
            blocks.append(
                f"Rider #{rider.rider_id} (speed {rider.speed} units/tick, "
                f"{len(rider.log)} events)"
            )
            for entry in rider.log:
                order_text = f"order #{entry['order_id']}" if entry["order_id"] is not None else "-"
                state_text = STATE_NAMES.get(entry["state"], "?")
                blocks.append(
                    f"  t={entry['tick']:<5} {entry['event']:<22} {order_text:<12} "
                    f"pos=({entry['x']}, {entry['y']}) state={state_text}"
                )
        return "\n".join(blocks)

    def render_map(
        self,
        riders: Iterable[Rider] = (),
        orders: Iterable = (),
        route: Optional[Iterable[Tuple[int, int]]] = None,
    ) -> str:
        """Render the 800x800 street map as ASCII art at 50-unit resolution.

        Args:
            riders: Riders to mark on the map.
            orders: Orders whose active restaurants and customers are marked.
            route: Optional sequence of points drawn with ``*``.

        Returns:
            Multi-line string containing the map and a legend.
        """
        rider_marks = {}
        for rider in riders:
            rider_marks[rider.position()] = str(rider.rider_id % 10)

        active = [o for o in orders if o.status != STATUS_COMPLETED]
        restaurants: Set[Tuple[int, int]] = {o.res_pos for o in active}
        customers: Set[Tuple[int, int]] = {o.cus_pos for o in active}
        route_points: Set[Tuple[int, int]] = set(route or [])

        steps = range(0, MAP_SIZE + 1, MAP_STEP)
        header = "      " + "".join(
            str(x // BLOCK_SIZE) if x % BLOCK_SIZE == 0 else " " for x in steps
        )
        lines = [self.LEGEND, header + "   <- x in hundreds"]
        for y in reversed(list(steps)):
            label = f"{y:>5} " if y % BLOCK_SIZE == 0 else "      "
            row = "".join(
                self._symbol((x, y), rider_marks, restaurants, customers, route_points)
                for x in steps
            )
            lines.append(label + row)
        return "\n".join(lines)

    @staticmethod
    def _symbol(
        point: Tuple[int, int],
        rider_marks: dict,
        restaurants: Set[Tuple[int, int]],
        customers: Set[Tuple[int, int]],
        route_points: Set[Tuple[int, int]],
    ) -> str:
        """Return the map character for a single point, by display priority.

        Riders are drawn first, then restaurants, customers, the route, and
        finally the streets and empty space.
        """
        if point in rider_marks:
            return rider_marks[point]
        if point in restaurants:
            return "R"
        if point in customers:
            return "C"
        if point in route_points:
            return "*"
        x, y = point
        on_x = x % BLOCK_SIZE == 0
        on_y = y % BLOCK_SIZE == 0
        if on_x and on_y:
            return "+"
        if on_y:
            return "-"
        if on_x:
            return "|"
        return " "
