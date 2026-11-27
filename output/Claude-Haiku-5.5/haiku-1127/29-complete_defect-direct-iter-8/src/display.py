"""Status display and ASCII map visualisation.

Map symbols:
    'R' rider, 'S' restaurant, 'C' customer, '.' empty cell,
    '#' street segment used by a route, ' ' empty street junction.
"""

import math
from typing import Iterable, List, Optional, Sequence

import globalvar
from order_model import Order
from path_planner import (CELL_SIZE, GRID_SIZE, Point, PathPlanner,
                          grid_index)
from rider import STATE_NAMES, Rider

ACTIVE_STATUSES = ("pending", "assigned", "pickup", "delivering")


def _canvas_pos(point: Point) -> tuple:
    """Map a unit coordinate to a (row, col) position on the ASCII canvas.

    Each grid cell occupies canvas position (2*row, 2*col); the odd positions
    between cells are used for street connectors.
    """
    col = 2 * grid_index(point[0])
    row = 2 * (GRID_SIZE - 1 - grid_index(point[1]))
    return row, col


class DisplayManager:
    """Renders status tables, order and log listings, and the map."""

    # ----- text reports ----------------------------------------------------
    def render_status(self) -> str:
        """Return the system snapshot: funds, riders and their orders."""
        riders: List[Rider] = globalvar.get_value("riders", []) or []
        orders: List[Order] = globalvar.get_value("orders", []) or []
        pending = sum(1 for o in orders if o.status == "pending")
        lines = [
            f"Tick: {globalvar.get_value('tick', 0)}",
            f"System funds: {globalvar.get_value('funds', 0)}",
            f"Riders: {len(riders)}",
            f"Pending orders: {pending}",
        ]
        if not riders:
            lines.append("  (no riders yet)")
        for rider in riders:
            order_ids = [o.id for o in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id}: {rider.state_name:<11} "
                f"pos=({rider.x},{rider.y}) speed={rider.speed} "
                f"orders={order_ids} special_case={rider.special_case}")
        return "\n".join(lines)

    def render_orders(self) -> str:
        """Return a table of all orders."""
        orders: List[Order] = globalvar.get_value("orders", []) or []
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} "
                  f"{'Customer':>12} {'Dist':>6} {'Ticks':>6} "
                  f"{'Rider':>6} {'Status':<10}")
        lines = [header, "-" * len(header)]
        for o in orders:
            rider = "-" if o.rider_id is None else f"#{o.rider_id}"
            duration = "-" if o.duration is None else str(o.duration)
            lines.append(
                f"{o.id:>4} {o.start_time:>6} "
                f"{str(o.restaurant_raw):>12} {str(o.customer_raw):>12} "
                f"{o.distance:>6} {duration:>6} {rider:>6} {o.status:<10}")
        return "\n".join(lines)

    def render_rider_log(self) -> str:
        """Return every recorded status change for all riders."""
        riders: List[Rider] = globalvar.get_value("riders", []) or []
        if not riders:
            return "No riders yet."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} ({len(rider.log)} events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None \
                    else f"#{entry['order_id']}"
                lines.append(
                    f"  t={entry['tick']:<5} {entry['event']:<22} "
                    f"order {order:<6} "
                    f"state={STATE_NAMES.get(entry['state'], '?'):<11} "
                    f"pos=({entry['x']},{entry['y']})")
        return "\n".join(lines)

    def render_assignment(self, rider: Optional[Rider], order: Order,
                          new_rider: bool) -> str:
        """Return the report shown after an order is submitted.

        Includes the grid coordinates, whether a rider was added, the
        assigned rider's speed and estimated time, and the route map.
        """
        lines = [
            f"Order #{order.id} created at tick {order.start_time}.",
            f"Restaurant: input {order.restaurant_raw} -> grid cell center "
            f"{order.res_pos}",
            f"Customer:   input {order.customer_raw} -> grid cell center "
            f"{order.cus_pos}",
            f"New rider added: {'yes' if new_rider else 'no'}",
        ]
        if rider is None:
            lines.append("No rider is available; the order is queued and will "
                         "be assigned automatically.")
            lines.append(self.render_map())
            return "\n".join(lines)

        route = PathPlanner.full_route(
            rider.position, [order.res_pos, order.cus_pos],
            [r.position for r in globalvar.get_value("riders", [])
             if r is not rider])
        length = PathPlanner.route_length(route)
        ticks = math.ceil(length / rider.speed) if rider.speed > 0 else 0
        lines.append(f"Assigned to rider #{rider.rider_id} "
                     f"(speed {rider.speed} units/tick)")
        lines.append(f"Route length {length} units, estimated {ticks} ticks "
                     f"for this order's route")
        lines.append("Route map (# = route, R = rider, S = restaurant, "
                     "C = customer):")
        lines.append(self.render_map(route=route))
        return "\n".join(lines)

    # ----- map -----------------------------------------------------------
    def render_map(self, route: Optional[Sequence[Point]] = None) -> str:
        """Render the 8x8 ASCII map.

        Args:
            route: Optional list of route points to draw as connected
                line segments.

        Returns:
            Multi-line string containing the map with axis labels.
        """
        size = 2 * GRID_SIZE - 1
        canvas = [[" "] * size for _ in range(size)]
        for r in range(0, size, 2):
            for c in range(0, size, 2):
                canvas[r][c] = "."

        if route:
            self._draw_route(canvas, route)

        orders: List[Order] = globalvar.get_value("orders", []) or []
        for order in orders:
            if order.status not in ACTIVE_STATUSES:
                continue
            row, col = _canvas_pos(order.res_pos)
            canvas[row][col] = "S"
            row, col = _canvas_pos(order.cus_pos)
            canvas[row][col] = "C"

        riders: List[Rider] = globalvar.get_value("riders", []) or []
        for rider in riders:
            row, col = _canvas_pos(rider.position)
            canvas[row][col] = "R"

        lines = ["     +" + "-" * (size + 1)]
        for r in range(size):
            if r % 2 == 0:
                label = f"y{GRID_SIZE - 1 - r // 2:>2}"
            else:
                label = "   "
            row_text = "".join(canvas[r])
            lines.append(f"{label}  | {row_text} |")
        lines.append("     +" + "-" * (size + 1))
        header = "".join(str(i) if i % 1 == 0 and c % 2 == 0 else " "
                         for i, c in enumerate([0] * size))
        x_labels = [" "] * size
        for i in range(GRID_SIZE):
            x_labels[2 * i] = str(i)
        lines.append("       " + "".join(x_labels) + "   (x index)")
        lines.append(f"Cell size {CELL_SIZE} units; y index labels on the left.")
        return "\n".join(lines)

    @staticmethod
    def _draw_route(canvas: List[List[str]], route: Iterable[Point]) -> None:
        """Draw connected street segments for a route onto the canvas."""
        points = list(route)
        for a, b in zip(points, points[1:]):
            row_a, col_a = _canvas_pos(a)
            row_b, col_b = _canvas_pos(b)
            if row_a == row_b:
                for c in range(min(col_a, col_b), max(col_a, col_b) + 1):
                    if canvas[row_a][c] in (" ", "."):
                        canvas[row_a][c] = "#"
            elif col_a == col_b:
                for r in range(min(row_a, row_b), max(row_a, row_b) + 1):
                    if canvas[r][col_a] in (" ", "."):
                        canvas[r][col_a] = "#"
        if points:
            row, col = _canvas_pos(points[0])
            if canvas[row][col] in (" ", "."):
                canvas[row][col] = "#"
