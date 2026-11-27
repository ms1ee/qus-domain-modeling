"""Status display and ASCII map rendering."""

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from path_planner import MAP_SIZE, NODES_PER_AXIS, STEP, Grid
from rider import STATE_NAMES

DEFAULT_SYMBOLS: Dict[str, str] = {
    "rider": "O",
    "restaurant": "R",
    "customer": "C",
    "empty": " ",
    "street": "+",
    "street_h": "-",
    "street_v": "|",
    "location": ".",
    "route": "*",
}

_FINISHED = ("completed", "failed", "rejected")


def _fmt(pos: Sequence[int]) -> str:
    """Format a coordinate pair as ``(x,y)``."""
    return f"({pos[0]},{pos[1]})"


class DisplayManager:
    """Renders system status, order tables, logs and the ASCII map.

    Attributes:
        map_symbols: Mapping from element name to the character drawn.
    """

    def __init__(self, map_symbols: Optional[Dict[str, str]] = None) -> None:
        self.map_symbols: Dict[str, str] = dict(DEFAULT_SYMBOLS)
        if map_symbols:
            self.map_symbols.update(map_symbols)
        self._grid = Grid()

    def render_status(self, system: Any) -> str:
        """Return the funds, rider count and per-rider details."""
        riders = system.riders
        lines = [
            f"System funds : {system.funds}",
            f"Current tick : {system.current_tick}",
            f"Riders       : {len(riders)}",
        ]
        if not riders:
            lines.append("  (no riders recruited yet)")
        for rider in riders:
            order_ids = ", ".join(f"#{o.id}" for o in rider.orders) or "none"
            lines.append(
                f"  Rider #{rider.rider_id}: position={_fmt(rider.position)} "
                f"state={rider.state_name} speed={rider.speed} "
                f"orders={len(rider.orders)} ({order_ids})"
            )
            for order in rider.orders:
                lines.append(
                    f"      order #{order.id} [{order.status}] "
                    f"restaurant={_fmt(order.restaurant_pos)} "
                    f"customer={_fmt(order.customer_pos)}"
                )
        return "\n".join(lines)

    def render_orders(self, orders: Iterable[Any]) -> str:
        """Return a table of all orders."""
        orders = list(orders)
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Distance':>9} {'Time':>6} {'Rider':>6} {'Status':<12}")
        lines = [header, "-" * len(header)]
        for order in orders:
            rider = f"#{order.rider_id}" if order.rider_id is not None else "-"
            time_taken = "-" if order.time_taken is None else str(order.time_taken)
            lines.append(
                f"{order.id:>4} {order.start_time:>6} "
                f"{_fmt(order.restaurant_pos):>12} {_fmt(order.customer_pos):>12} "
                f"{order.distance:>9} {time_taken:>6} {rider:>6} {order.status:<12}"
            )
        return "\n".join(lines)

    def render_rider_logs(self, riders: Iterable[Any]) -> str:
        """Return every recorded status change for every rider."""
        riders = list(riders)
        if not riders:
            return "No riders recruited yet."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} ({len(rider.log)} records)")
            if not rider.log:
                lines.append("  (no records)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                state = STATE_NAMES.get(entry["state"], "unknown")
                lines.append(
                    f"  tick {entry['tick']:>5} | {entry['event']:<20} | "
                    f"order {order:>5} | pos ({entry['x']},{entry['y']}) | {state}"
                )
        return "\n".join(lines)

    def render_map(self, riders: Iterable[Any], orders: Iterable[Any],
                   route: Optional[Sequence[Tuple[int, int]]] = None) -> str:
        """Render the 8x8 city map as ASCII art.

        The canvas is a 33x33 character grid. Lattice nodes are at even
        indices, and connectors sit between them. Streets are drawn with
        '-' and '|', cell centers with '.', and intersections with '+'.

        Args:
            riders: Riders to mark on the map.
            orders: Orders whose restaurant (R) and customer (C) to mark.
            route: Optional route as a list of consecutive lattice points,
                drawn with '*'.

        Returns:
            Multi-line string with the map and a legend.
        """
        size = 2 * (NODES_PER_AXIS - 1) + 1
        empty = self.map_symbols["empty"]
        canvas = [[empty] * size for _ in range(size)]

        for x in range(0, MAP_SIZE + 1, STEP):
            for y in range(0, MAP_SIZE + 1, STEP):
                row, col = self._to_canvas(x, y)
                canvas[row][col] = self._node_symbol(x, y)
                if x + STEP <= MAP_SIZE:
                    self._draw_edge(canvas, (x, y), (x + STEP, y))
                if y + STEP <= MAP_SIZE:
                    self._draw_edge(canvas, (x, y), (x, y + STEP))

        route_list = list(route or [])
        route_symbol = self.map_symbols["route"]
        for a, b in zip(route_list, route_list[1:]):
            ra, ca = self._to_canvas(*a)
            rb, cb = self._to_canvas(*b)
            canvas[(ra + rb) // 2][(ca + cb) // 2] = route_symbol
        for node in route_list:
            row, col = self._to_canvas(*node)
            canvas[row][col] = route_symbol

        for order in orders:
            if order.status in _FINISHED:
                continue
            row, col = self._to_canvas(*order.restaurant_pos)
            canvas[row][col] = self.map_symbols["restaurant"]
            row, col = self._to_canvas(*order.customer_pos)
            canvas[row][col] = self.map_symbols["customer"]

        for rider in riders:
            row, col = self._to_canvas(*rider.position)
            canvas[row][col] = self.map_symbols["rider"]

        lines = ["".join(row).rstrip() for row in canvas]
        legend = (f"Legend: {self.map_symbols['rider']} rider  "
                  f"{self.map_symbols['restaurant']} restaurant  "
                  f"{self.map_symbols['customer']} customer  "
                  f"{self.map_symbols['street']} intersection  "
                  f"{self.map_symbols['street_h']}{self.map_symbols['street_v']} street  "
                  f"{self.map_symbols['location']} cell center  "
                  f"{self.map_symbols['route']} route (y axis points up, 100 units per cell)")
        return "\n".join(lines) + "\n" + legend

    # ----- helpers ----------------------------------------------------
    @staticmethod
    def _to_canvas(x: int, y: int) -> Tuple[int, int]:
        """Convert map coordinates to canvas (row, col)."""
        row = (MAP_SIZE - y) // STEP * 2
        col = x // STEP * 2
        return row, col

    def _node_symbol(self, x: int, y: int) -> str:
        """Return the symbol for a lattice node."""
        if self._grid.is_location(x, y):
            return self.map_symbols["location"]
        if self._grid.is_street(x, y):
            return self.map_symbols["street"]
        return self.map_symbols["empty"]

    def _edge_symbol(self, a: Tuple[int, int], b: Tuple[int, int]) -> Optional[str]:
        """Return the connector symbol between two adjacent lattice nodes."""
        either_location = self._grid.is_location(*a) or self._grid.is_location(*b)
        if a[1] == b[1]:
            if a[1] % self._grid.cell_size == 0 or either_location:
                return self.map_symbols["street_h"]
            return None
        if a[0] % self._grid.cell_size == 0 or either_location:
            return self.map_symbols["street_v"]
        return None

    def _draw_edge(self, canvas: List[List[str]],
                   a: Tuple[int, int], b: Tuple[int, int]) -> None:
        """Draw the connector between two lattice nodes, if it is a street."""
        symbol = self._edge_symbol(a, b)
        if symbol is None:
            return
        ra, ca = self._to_canvas(*a)
        rb, cb = self._to_canvas(*b)
        canvas[(ra + rb) // 2][(ca + cb) // 2] = symbol
