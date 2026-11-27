"""Status displays and ASCII map visualisation.

The map is a 16x16 character grid covering the 800x800 unit area, so each
character cell represents 50x50 units. Symbols:
    R  rider          S  restaurant      C  customer
    #  street         .  empty space     *  planned route
"""

from typing import Iterable, List, Sequence, Tuple

from order_model import Order, manhattan
from path_planner import PathPlanner
from rider import STATE_NAMES, Rider

Point = Tuple[int, int]


class DisplayManager:
    """Formats status tables, order/rider logs and the ASCII map.

    Attributes:
        map_dimension (int): Characters per side of the map (16).
        map_size (int): Size of the represented area in units (800).
        unit (int): Units represented by one map character.
        street_spacing (int): Distance between street lines (100).
    """

    def __init__(self, map_dimension: int = 16, map_size: int = 800,
                 street_spacing: int = 100) -> None:
        """Create a display manager.

        Args:
            map_dimension: Number of characters per map side.
            map_size: Size of the map area in units.
            street_spacing: Distance between streets in units.
        """
        self.map_dimension = map_dimension
        self.map_size = map_size
        self.unit = map_size // map_dimension
        self.street_spacing = street_spacing

    def _cell(self, value: int) -> int:
        """Convert a coordinate to a map index, clamped to the map."""
        return min(max(int(value), 0) // self.unit, self.map_dimension - 1)

    def render_map(self, riders: Iterable[Rider] = (),
                   orders: Iterable[Order] = (),
                   route: Sequence[Point] = ()) -> str:
        """Render the ASCII map with riders, orders and an optional route.

        Args:
            riders: Riders to draw as 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') are drawn.
            route: Points of a planned route drawn as '*'.

        Returns:
            Multi-line string containing the map and a legend.
        """
        size = self.map_dimension
        grid: List[List[str]] = []
        for row in range(size):
            y = row * self.unit
            line = []
            for col in range(size):
                x = col * self.unit
                on_street = x % self.street_spacing == 0 or y % self.street_spacing == 0
                line.append("#" if on_street else ".")
            grid.append(line)

        for x, y in route:
            row, col = self._cell(y), self._cell(x)
            if grid[row][col] in "#.":
                grid[row][col] = "*"
        for order in orders:
            grid[self._cell(order.restaurant_y)][self._cell(order.restaurant_x)] = "S"
            grid[self._cell(order.customer_y)][self._cell(order.customer_x)] = "C"
        for rider in riders:
            grid[self._cell(rider.y)][self._cell(rider.x)] = "R"

        lines = ["    " + " ".join(str(col % 10) for col in range(size))]
        for row in range(size):
            lines.append(f"{row * self.unit:>4} " + " ".join(grid[row]))
        lines.append("Legend: R=rider S=restaurant C=customer #=street .=empty *=route")
        return "\n".join(lines)

    def format_status(self, system) -> str:
        """Return a snapshot of funds, riders and their orders.

        Args:
            system: The SystemManager instance.
        """
        riders = system.riders
        pending = len(system.order_manager.pending_orders())
        lines = [
            f"Simulated time: {system.simulated_time} tick(s)",
            f"System funds: {system.funds}",
            f"Riders: {len(riders)} (idle: {len(system.idle_riders())})",
            f"Pending orders: {pending}",
        ]
        if not riders:
            lines.append("  (no riders yet)")
        for rider in riders:
            order_ids = [order.id for order in rider.active_orders()]
            lines.append(
                f"  Rider #{rider.rider_id}: position=({rider.x}, {rider.y}) "
                f"state={STATE_NAMES[rider.state]} speed={rider.speed} "
                f"active_orders={len(order_ids)} order_ids={order_ids}"
            )
        return "\n".join(lines)

    def format_orders(self, orders: Sequence[Order]) -> str:
        """Return a table with details for all orders.

        Args:
            orders: Orders to display.
        """
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Distance':>8} {'Taken':>6} {'Efficiency':>10} "
                  f"{'Rider':>6} {'Status':>12}")
        lines = [header, "-" * len(header)]
        for order in orders:
            taken = "-" if order.time_taken is None else str(order.time_taken)
            eff = "-" if order.efficiency is None else f"{order.efficiency:.2f}"
            rider = "-" if order.rider_id is None else str(order.rider_id)
            restaurant = f"({order.restaurant_x},{order.restaurant_y})"
            customer = f"({order.customer_x},{order.customer_y})"
            lines.append(
                f"{order.id:>4} {order.start_time:>6} {restaurant:>12} {customer:>12} "
                f"{order.distance:>8} {taken:>6} {eff:>10} {rider:>6} {order.status:>12}"
            )
        return "\n".join(lines)

    def format_rider_logs(self, riders: Sequence[Rider]) -> str:
        """Return the status change history of every rider.

        Args:
            riders: Riders whose logs are displayed.
        """
        if not riders:
            return "No riders yet."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} (current state: {STATE_NAMES[rider.state]})")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order_text = "-" if entry["order_id"] is None else str(entry["order_id"])
                lines.append(
                    f"  t={entry['time']:>4} {entry['event']:<20} order={order_text:<5} "
                    f"at ({entry['x']},{entry['y']}) state={STATE_NAMES[entry['state']]}"
                )
        return "\n".join(lines)

    def format_route_summary(self, order: Order, rider: Rider,
                             planner: PathPlanner) -> str:
        """Return speed and time estimates for serving an order.

        Args:
            order: The assigned order.
            rider: The rider serving it.
            planner: Path planner used for tick estimates.
        """
        pickup = manhattan(rider.position(), order.restaurant_pos)
        delivery = order.distance
        pickup_ticks = planner.ticks_needed(pickup, rider.speed)
        delivery_ticks = planner.ticks_needed(delivery, rider.speed)
        return (
            f"Speed: {rider.speed} units/tick | pickup: {pickup} units "
            f"(~{pickup_ticks} ticks) | delivery: {delivery} units "
            f"(~{delivery_ticks} ticks) | total ~{pickup_ticks + delivery_ticks} ticks"
        )

    def format_event(self, entry: dict) -> str:
        """Return a one-line description of a rider log entry.

        Args:
            entry: A rider log dictionary.
        """
        order_text = "-" if entry["order_id"] is None else str(entry["order_id"])
        return (f"t={entry['time']} Rider #{entry['rider_id']} {entry['event']} "
                f"order={order_text} at ({entry['x']},{entry['y']})")
