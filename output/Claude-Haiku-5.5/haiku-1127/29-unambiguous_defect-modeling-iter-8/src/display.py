"""Status display and ASCII map rendering."""

from typing import Any, Dict, Iterable, List, Optional, Sequence

from grid_map import CELL_SIZE, LATTICE_STEP, GridMap, Point
from rider import STATE_NAMES


class DisplayManager:
    """Renders the map, status, order table and rider logs as text."""

    def __init__(self, grid: Optional[GridMap] = None) -> None:
        """Create the display manager.

        Args:
            grid: Grid map to render. A default 8x8 map is created if None.
        """
        self.grid = grid if grid is not None else GridMap()
        self.map_symbols: Dict[str, str] = {
            "empty": " ",
            "street_h": "-",
            "street_v": "|",
            "intersection": "+",
            "restaurant": "R",
            "customer": "C",
            "both": "X",
            "route": "*",
        }

    # ------------------------------------------------------------------
    # Map
    # ------------------------------------------------------------------
    def _place_marker(self, canvas: List[List[str]], pos: Point, kind: str) -> None:
        """Place a restaurant or customer marker on the canvas.

        Args:
            canvas: Character grid being drawn.
            pos: Location point.
            kind: "restaurant" or "customer".
        """
        x, y = pos
        ix, iy = x // LATTICE_STEP, y // LATTICE_STEP
        current = canvas[iy][ix]
        symbol = self.map_symbols[kind]
        restaurant = self.map_symbols["restaurant"]
        customer = self.map_symbols["customer"]
        both = self.map_symbols["both"]
        if current == both or (current in (restaurant, customer) and current != symbol):
            symbol = both
        canvas[iy][ix] = symbol

    def _axis_header(self, n: int) -> str:
        """Build a header line with x-axis labels in hundreds.

        Args:
            n: Number of lattice points per row.

        Returns:
            The header string.
        """
        chars = [" "] * (2 * n - 1)
        for ix in range(n):
            x = ix * LATTICE_STEP
            if x % CELL_SIZE == 0:
                chars[2 * ix] = str(x // CELL_SIZE)
        return " " * 5 + "".join(chars)

    def render_map(self, routes: Optional[Iterable[Sequence[Point]]] = None,
                   riders: Optional[Iterable[Any]] = None,
                   orders: Optional[Iterable[Any]] = None) -> str:
        """Render the ASCII map.

        Riders are drawn with the last digit of their ID, restaurants with R,
        customers with C, and routes with '*'. The top row is y=800.

        Args:
            routes: Optional lists of lattice points to draw as routes.
            riders: Optional riders to display.
            orders: Optional active orders whose locations are displayed.

        Returns:
            Multi-line string containing the map and legend.
        """
        step = LATTICE_STEP
        grid = self.grid
        n = grid.map_length // step + 1
        canvas = [[self.map_symbols["empty"] for _ in range(n)] for _ in range(n)]

        for iy in range(n):
            for ix in range(n):
                x, y = ix * step, iy * step
                if not grid.is_street(x, y):
                    continue
                if x % CELL_SIZE == 0 and y % CELL_SIZE == 0:
                    symbol = self.map_symbols["intersection"]
                elif y % CELL_SIZE == 0:
                    symbol = self.map_symbols["street_h"]
                else:
                    symbol = self.map_symbols["street_v"]
                canvas[iy][ix] = symbol

        for route in routes or []:
            for x, y in route:
                if grid.is_street(x, y):
                    canvas[y // step][x // step] = self.map_symbols["route"]

        for order in orders or []:
            self._place_marker(canvas, order.res_pos, "restaurant")
            self._place_marker(canvas, order.cus_pos, "customer")

        for rider in riders or []:
            canvas[rider.y // step][rider.x // step] = str(rider.rider_id % 10)

        lines = [self._axis_header(n)]
        for iy in reversed(range(n)):
            y = iy * step
            label = f"{y:4d} " if y % CELL_SIZE == 0 else "     "
            lines.append(label + " ".join(canvas[iy]))
        lines.append("")
        lines.append(
            "Legend: R=restaurant C=customer X=both 0-9=rider id (mod 10) "
            "*=route +=intersection -=horizontal street |=vertical street"
        )
        lines.append("Axes: x labels are hundreds (left->right), y labels are hundreds (bottom->top).")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Text reports
    # ------------------------------------------------------------------
    def render_status(self, funds: int, riders: Sequence[Any], tick: int) -> str:
        """Render the system snapshot.

        Args:
            funds: Current system funds.
            riders: All riders.
            tick: Current simulated time.

        Returns:
            Multi-line status report.
        """
        lines = [
            f"=== System status (tick {tick}) ===",
            f"Funds: {funds}",
            f"Riders: {len(riders)}",
        ]
        if not riders:
            lines.append("  (no riders recruited yet)")
        for rider in riders:
            lines.append(
                f"  Rider #{rider.rider_id}: position=({rider.x}, {rider.y}) "
                f"state={STATE_NAMES.get(rider.state, rider.state)} "
                f"speed={rider.speed} orders={len(rider.orders)} "
                f"special_case={rider.special_case}"
            )
            for order in rider.orders:
                lines.append(
                    f"      order #{order.id}: {order.status} "
                    f"restaurant={order.res_pos} customer={order.cus_pos}"
                )
        return "\n".join(lines)

    def render_orders(self, orders: Sequence[Any]) -> str:
        """Render a table of all orders.

        Args:
            orders: All orders.

        Returns:
            Multi-line order table.
        """
        if not orders:
            return "No orders yet."
        header = (
            f"{'ID':<5}{'status':<13}{'start':<8}{'restaurant':<14}"
            f"{'customer':<14}{'distance':<10}{'taken':<8}{'rider':<6}"
        )
        lines = [header, "-" * len(header)]
        for o in orders:
            taken = "-" if o.time_taken is None else str(o.time_taken)
            rider = "-" if o.rider_id is None else str(o.rider_id)
            lines.append(
                f"{o.id:<5}{o.status:<13}{o.start_time:<8}"
                f"{str(o.res_pos):<14}{str(o.cus_pos):<14}"
                f"{o.distance:<10.0f}{taken:<8}{rider:<6}"
            )
        return "\n".join(lines)

    def render_rider_logs(self, riders: Sequence[Any]) -> str:
        """Render the status-change history of every rider.

        Args:
            riders: All riders.

        Returns:
            Multi-line log report.
        """
        if not riders:
            return "No riders recruited yet."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} ({len(rider.log)} events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else str(entry["order_id"])
                lines.append(
                    f"  tick {entry['tick']:>5} | {entry['event']:<22} | "
                    f"pos=({entry['x']}, {entry['y']}) | order={order}"
                )
        return "\n".join(lines)
