"""Text rendering for status, orders, rider logs and the ASCII map."""

from typing import Iterable, List, Optional, Sequence, Tuple

from grid_map import GridMap
from order_model import Order
from rider import Rider

Point = Tuple[int, int]


class DisplayManager:
    """Builds human-readable text views of the simulation.

    The ASCII map uses a lattice of ``2 * grid_dimension + 1`` characters per
    side (17x17 for the 8x8 city). Even indices are streets ('#'), odd-odd
    indices are the blocks ('.'). Intersections are the even-even cells.
    """

    def __init__(self, map_display_size: Optional[int] = None, grid_map: Optional[GridMap] = None) -> None:
        """Create a display manager.

        Args:
            map_display_size: Side length of the ASCII map in characters.
            grid_map: Map geometry. Defaults to the 800x800 city.
        """
        self.grid_map = grid_map if grid_map is not None else GridMap()
        if map_display_size is None:
            map_display_size = 2 * self.grid_map.grid_dimension + 1
        self.map_display_size = map_display_size

    def _index(self, value: float) -> int:
        """Convert a map coordinate to a canvas index."""
        scale = (self.map_display_size - 1) / self.grid_map.map_size
        index = int(round(value * scale))
        return min(max(index, 0), self.map_display_size - 1)

    def render_map(
        self,
        riders: Optional[Iterable[Rider]] = None,
        orders: Optional[Iterable[Order]] = None,
        route: Optional[Sequence[Point]] = None,
    ) -> str:
        """Render the ASCII city map.

        Symbols: 'R' rider, 'S' restaurant, 'C' customer, '.' empty block,
        '#' street, '*' planned route.

        Args:
            riders: Riders to draw.
            orders: Orders whose restaurant and customer points are drawn
                (completed orders are skipped).
            route: Optional list of waypoints drawn as a connected line.

        Returns:
            Multi-line string containing the map and a legend.
        """
        size = self.map_display_size
        canvas: List[List[str]] = [
            ["#" if (r % 2 == 0 or c % 2 == 0) else "." for c in range(size)]
            for r in range(size)
        ]

        if route:
            for (ax, ay), (bx, by) in zip(route, route[1:]):
                r1, c1 = self._index(ay), self._index(ax)
                r2, c2 = self._index(by), self._index(bx)
                for r in range(min(r1, r2), max(r1, r2) + 1):
                    for c in range(min(c1, c2), max(c1, c2) + 1):
                        canvas[r][c] = "*"

        for order in orders or []:
            if order.status == "completed":
                continue
            canvas[self._index(order.restaurant_y)][self._index(order.restaurant_x)] = "S"
            canvas[self._index(order.customer_y)][self._index(order.customer_x)] = "C"

        for rider in riders or []:
            canvas[self._index(rider.y)][self._index(rider.x)] = "R"

        rows = [" ".join(row) for row in canvas]
        legend = "Legend: R=Rider S=Restaurant C=Customer .=Block #=Street *=Route"
        return "\n".join(rows) + "\n" + legend

    def render_status(self, system) -> str:
        """Render the system snapshot: funds, time, and every rider's state."""
        riders = system.riders
        lines = [
            f"System funds : {system.funds}",
            f"Current tick : {system.current_time}",
            f"Rider count  : {len(riders)}",
        ]
        if not riders:
            lines.append("No riders on duty.")
        for rider in riders:
            order_ids = ", ".join(str(o.id) for o in rider.orders) or "none"
            current = rider.current_order.id if rider.current_order is not None else "-"
            lines.append(
                f"  Rider #{rider.rider_id}: location=({rider.x},{rider.y}) "
                f"status={rider.state_name} assigned={len(rider.orders)} "
                f"active={rider.active_order_count()} current_order={current} "
                f"orders=[{order_ids}]"
            )
        return "\n".join(lines)

    def render_orders(self, orders: Iterable[Order]) -> str:
        """Render a table of all orders with timing and rider data."""
        header = (
            f"{'ID':>4}  {'Start':>5}  {'Restaurant':>12}  {'Customer':>12}  "
            f"{'Distance':>8}  {'Taken':>5}  {'Rider':>5}  {'Status':<10}"
        )
        lines = [header, "-" * len(header)]
        count = 0
        for o in orders:
            count += 1
            rider = "-" if o.rider_id is None else str(o.rider_id)
            lines.append(
                f"{o.id:>4}  {o.start_time:>5}  {str(o.restaurant_pos):>12}  "
                f"{str(o.customer_pos):>12}  {o.distance:>8.1f}  "
                f"{o.time_taken:>5}  {rider:>5}  {o.status:<10}"
            )
        if count == 0:
            lines.append("No orders yet.")
        return "\n".join(lines)

    def render_rider_log(self, riders: Iterable[Rider]) -> str:
        """Render every recorded status change for all riders."""
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id}:")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else str(entry["order_id"])
                lines.append(
                    f"  t={entry['time']:<5} event={entry['event']:<20} "
                    f"order={order:<4} at=({entry['x']},{entry['y']}) "
                    f"state={entry['state']}"
                )
        return "\n".join(lines) if lines else "No riders on duty."

    def render_route(
        self,
        route: Sequence[Point],
        speed: int,
        ticks: int,
        riders: Optional[Iterable[Rider]] = None,
        orders: Optional[Iterable[Order]] = None,
    ) -> str:
        """Render a planned route with speed and time estimate plus the map."""
        header = (
            f"Route waypoints: {' -> '.join(str(p) for p in route)}\n"
            f"Speed: {speed} units/tick | Estimated time: {ticks} ticks"
        )
        return header + "\n" + self.render_map(riders, orders, route)
