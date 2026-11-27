"""Status displays and ASCII map rendering for the command line."""

from typing import Iterable, List, Optional, Sequence, Tuple

from config import CELL_SIZE, MAP_SIZE
from rider import STATE_NAMES, Rider

Point = Tuple[int, int]


class DisplayManager:
    """Formats status, order, rider-log and map output as text.

    The ASCII map samples the 800x800 world every 50 units, giving a
    17x17 character canvas (8x8 cells with street intersections on even
    positions). Symbols:
      ``R`` rider, ``S`` restaurant, ``C`` customer, ``#`` street,
      ``*`` route, ``.`` empty space.
    """

    SAMPLE = CELL_SIZE // 2
    SIZE = MAP_SIZE // SAMPLE + 1

    ROAD = "#"
    EMPTY = "."
    ROUTE = "*"
    RESTAURANT = "S"
    CUSTOMER = "C"
    RIDER = "R"

    def _cell_index(self, value: int) -> int:
        """Convert a world coordinate to a canvas index."""
        index = int(round(value / self.SAMPLE))
        return max(0, min(index, self.SIZE - 1))

    def _put(self, grid: List[List[str]], x: int, y: int, symbol: str) -> None:
        """Place a symbol at the canvas cell corresponding to ``(x, y)``."""
        grid[self._cell_index(y)][self._cell_index(x)] = symbol

    def _draw_route(self, grid: List[List[str]], points: Sequence[Point]) -> None:
        """Draw connected line segments for a route on the canvas."""
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            if ax == bx:
                step = self.SAMPLE if by >= ay else -self.SAMPLE
                for y in range(ay, by + step, step):
                    self._put(grid, ax, y, self.ROUTE)
            elif ay == by:
                step = self.SAMPLE if bx >= ax else -self.SAMPLE
                for x in range(ax, bx + step, step):
                    self._put(grid, x, ay, self.ROUTE)
            else:
                self._put(grid, ax, ay, self.ROUTE)
                self._put(grid, bx, by, self.ROUTE)
        if points:
            self._put(grid, points[0][0], points[0][1], self.ROUTE)
            self._put(grid, points[-1][0], points[-1][1], self.ROUTE)

    def render_map(self, riders: Iterable[Rider], orders: Iterable = (),
                   route: Optional[Sequence[Point]] = None) -> str:
        """Render the ASCII map with riders, orders and an optional route.

        Args:
            riders: Riders to display as ``R``.
            orders: Orders whose restaurant (``S``) and customer (``C``)
                points are shown.
            route: Optional list of corner points drawn as ``*`` segments.

        Returns:
            Multi-line string containing the map and a legend.
        """
        grid = [[self.EMPTY] * self.SIZE for _ in range(self.SIZE)]
        for row in range(self.SIZE):
            for col in range(self.SIZE):
                x = col * self.SAMPLE
                y = row * self.SAMPLE
                if x % CELL_SIZE == 0 or y % CELL_SIZE == 0:
                    grid[row][col] = self.ROAD
        if route:
            self._draw_route(grid, list(route))
        for order in orders:
            self._put(grid, order.res_pos[0], order.res_pos[1], self.RESTAURANT)
            self._put(grid, order.cus_pos[0], order.cus_pos[1], self.CUSTOMER)
        for rider in riders:
            self._put(grid, rider.x, rider.y, self.RIDER)

        header = "      " + "".join(
            "|" if (col * self.SAMPLE) % CELL_SIZE == 0 else " "
            for col in range(self.SIZE))
        lines = ["Map (800x800 units, 100-unit cells; y grows downward)", header]
        for row in range(self.SIZE):
            y = row * self.SAMPLE
            label = f"{y:>4} -" if y % CELL_SIZE == 0 else "     "
            lines.append(label + "".join(grid[row]))
        lines.append("Legend: R=rider S=restaurant C=customer #=street "
                     "*=route .=empty")
        return "\n".join(lines)

    def format_status(self, funds: int, riders: Sequence[Rider], now: int = 0) -> str:
        """Format a snapshot of funds and every rider.

        Args:
            funds: Current system funds.
            riders: All riders.
            now: Current simulated tick.

        Returns:
            Multi-line status text.
        """
        lines = [
            "=== System Status ===",
            f"Time: {now} tick(s)",
            f"System funds: {funds}",
            f"Riders: {len(riders)}",
        ]
        for rider in riders:
            active = rider.active_orders()
            order_ids = [o.id for o in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id}: position=({rider.x}, {rider.y}) "
                f"speed={rider.speed} state={STATE_NAMES[rider.state]} "
                f"active_orders={len(active)} total_orders={len(rider.orders)} "
                f"order_ids={order_ids}")
        if not riders:
            lines.append("  (no riders recruited yet)")
        return "\n".join(lines)

    def format_orders(self, orders: Sequence) -> str:
        """Format a table of all orders.

        Args:
            orders: Orders to display.

        Returns:
            Multi-line table text.
        """
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Distance':>9} {'Time':>6} {'Rider':>6} {'Status':<11}")
        lines = ["=== Orders ===", header, "-" * len(header)]
        for o in orders:
            taken = o.time_taken
            rider = f"#{o.rider_id}" if o.rider_id is not None else "-"
            lines.append(
                f"{o.id:>4} {o.start_time:>6} {str(o.res_pos):>12} "
                f"{str(o.cus_pos):>12} {o.distance:>9} "
                f"{(str(taken) if taken is not None else '-'):>6} "
                f"{rider:>6} {o.status:<11}")
        return "\n".join(lines)

    def format_rider_log(self, riders: Sequence[Rider]) -> str:
        """Format every recorded status change for all riders.

        Args:
            riders: Riders whose logs should be shown.

        Returns:
            Multi-line log text.
        """
        if not riders:
            return "No riders recruited yet."
        lines = ["=== Rider Status Log ==="]
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id}:")
            for entry in rider.log:
                order = entry["order_id"] if entry["order_id"] is not None else "-"
                lines.append(
                    f"  t={entry['time']:>5}  {entry['event']:<22} "
                    f"order={order:<5} pos=({entry['x']}, {entry['y']}) "
                    f"state={STATE_NAMES[entry['state']]}")
        return "\n".join(lines)

    def format_order_report(self, order, rider: Rider, start_pos: Point,
                            route_distance: int, estimated_ticks: int,
                            actual_ticks: int, recruited: bool) -> str:
        """Format the summary shown after the ``start`` command.

        Args:
            order: The processed order.
            rider: The assigned rider.
            start_pos: Rider position when the order was assigned.
            route_distance: Total route length in units.
            estimated_ticks: Estimated ticks based on rider speed.
            actual_ticks: Ticks actually elapsed until delivery.
            recruited: Whether a new rider was added for this order.

        Returns:
            Multi-line report text.
        """
        return "\n".join([
            f"Order #{order.id} assigned to Rider #{rider.rider_id}",
            f"Restaurant grid coordinates: {order.res_pos}",
            f"Customer grid coordinates:   {order.cus_pos}",
            f"New rider added: {'yes' if recruited else 'no'}",
            f"Rider speed: {rider.speed} units/tick (started from {start_pos})",
            f"Route distance: {route_distance} units",
            f"Estimated time: {estimated_ticks} tick(s); actual: {actual_ticks} tick(s)",
            f"Order status: {order.status}",
        ])

    @staticmethod
    def format_help() -> str:
        """Return the command reference text."""
        return "\n".join([
            "Commands (shortcut in brackets):",
            "  start [rx ry cx cy]  (s)  Create an order: restaurant then customer coordinates (0-1000)",
            "  status               (st) Show funds and rider snapshot",
            "  orders               (o)  Show all order details",
            "  riders               (r)  Show every rider status change",
            "  map                  (m)  Show the ASCII map with riders and active orders",
            "  tick [n]             (t)  Advance the simulation by n ticks (default 1)",
            "  save [path]               Save state to JSON (default dispatch_state.json)",
            "  history                   Show command history",
            "  !! / !n                   Repeat the last command / history entry n",
            "  help                 (h)  Show this help",
            "  quit / exit          (q)  Exit the program",
        ])
