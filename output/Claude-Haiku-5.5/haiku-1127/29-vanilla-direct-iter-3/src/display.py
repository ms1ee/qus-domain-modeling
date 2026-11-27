"""Status display and ASCII map rendering.

Map layout: the 800x800 area is drawn as a 17x17 character canvas. Each
canvas index corresponds to 50 map units, so even indices are street lines
and odd-odd indices are grid-cell centres.

Symbols:
    R rider, S restaurant, C customer, . empty cell, # street, * route.
"""

from typing import Any, Iterable, List, Optional, Sequence, Tuple

from rider import STATE_NAMES

Point = Tuple[int, int]

HALF = 50
CANVAS_SIZE = 17
LEGEND = ("Legend: R=Rider  S=Restaurant  C=Customer  "
          ".=Empty  #=Street  *=Route  (x right, y up, 0-800)")


def _index(value: int) -> int:
    """Map a coordinate to a canvas index, clamped to the canvas."""
    return min(CANVAS_SIZE - 1, max(0, (value + HALF // 2) // HALF))


class DisplayManager:
    """Renders status snapshots, order tables, rider logs and the map."""

    def render_map(self, riders: Iterable[Any] = (),
                   orders: Iterable[Any] = (),
                   route: Optional[Sequence[Point]] = None) -> str:
        """Render the ASCII map with riders, orders and an optional route.

        Args:
            riders: Rider objects to plot.
            orders: Orders whose restaurant (S) and customer (C) points
                should be plotted. Completed orders are skipped.
            route: Optional waypoint list drawn with '*'.

        Returns:
            The multi-line map string.
        """
        n = CANVAS_SIZE
        canvas = [["#" if (i % 2 == 0 or j % 2 == 0) else "."
                   for i in range(n)] for j in range(n)]

        def place(x: int, y: int, symbol: str, overwrite_all: bool) -> None:
            i, j = _index(x), _index(y)
            if overwrite_all or canvas[j][i] in "#.*":
                canvas[j][i] = symbol

        if route:
            for x, y in route:
                place(x, y, "*", overwrite_all=False)
        for order in orders:
            if order.status == "completed":
                continue
            place(order.res_pos[0], order.res_pos[1], "S", True)
            place(order.cus_pos[0], order.cus_pos[1], "C", True)
        for rider in riders:
            place(rider.x, rider.y, "R", True)

        lines = []
        for j in range(n - 1, -1, -1):
            label = f"{j * HALF:>4} " if j % 2 == 0 else "     "
            lines.append(label + " ".join(canvas[j]))
        return "\n".join(lines + ["", LEGEND])

    def render_status(self, funds: int, time: int,
                      riders: Sequence[Any]) -> str:
        """Render the system status snapshot.

        Args:
            funds: Current system funds.
            time: Current simulated tick.
            riders: All riders.

        Returns:
            Multi-line status text.
        """
        lines = [
            f"System time : {time} tick(s)",
            f"System funds: {funds}",
            f"Riders      : {len(riders)}",
        ]
        for rider in riders:
            order_ids = [o.id for o in rider.orders]
            waiting = " [waiting]" if rider.special_case else ""
            lines.append(
                f"  Rider #{rider.rider_id:<3} pos=({rider.x},{rider.y})  "
                f"status={STATE_NAMES.get(rider.state, 'unknown')}{waiting}  "
                f"orders={len(order_ids)} {order_ids if order_ids else ''}"
            )
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
        header = (f"{'ID':>4}  {'Start':>5}  {'Restaurant':<11} "
                  f"{'Customer':<11} {'Dist':>6}  {'Taken':>5}  "
                  f"{'Rider':>6}  Status")
        rows: List[str] = [header, "-" * len(header)]
        for order in orders:
            rest = f"({order.res_pos[0]},{order.res_pos[1]})"
            cust = f"({order.cus_pos[0]},{order.cus_pos[1]})"
            taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else f"#{order.rider_id}"
            rows.append(
                f"{order.id:>4}  {order.start_time:>5}  {rest:<11} "
                f"{cust:<11} {order.distance:>6}  {taken:>5}  "
                f"{rider:>6}  {order.status}"
            )
        return "\n".join(rows)

    def render_rider_logs(self, riders: Sequence[Any]) -> str:
        """Render every recorded status change for all riders.

        Args:
            riders: Riders whose logs are shown.

        Returns:
            Multi-line log text.
        """
        if not riders:
            return "No riders."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} (speed {rider.speed}, "
                         f"{len(rider.log)} event(s))")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = ("-" if entry["order_id"] is None
                         else f"#{entry['order_id']}")
                lines.append(
                    f"  t={entry['time']:>4}  {entry['event']:<22} "
                    f"order={order:<5} pos=({entry['x']},{entry['y']})  "
                    f"state={STATE_NAMES.get(entry['state'], 'unknown')}"
                )
        return "\n".join(lines)
