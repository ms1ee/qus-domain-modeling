"""Status displays and ASCII map rendering for the dispatch simulator.

The 8x8 grid is drawn on a 15x15 character canvas. Cell centres are placed on
even rows and columns, so 'street' characters can be drawn between them.
Legend: R = rider, S = restaurant, C = customer, '.' = intersection (empty),
'#' = street segment on a route.
"""

import math

from path_planner import (CELL_CENTER_OFFSET, CELL_SIZE, GRID_SIZE,
                          manhattan, route_length, ticks_for_distance)
from rider import STATE_NAMES

CANVAS_SIZE = 2 * GRID_SIZE - 1
LEGEND = ("Legend: R=rider  S=restaurant  C=customer  "
          ".=intersection  #=street on route")


def _axis_index(value):
    """Map a coordinate to a canvas index along one axis (0-14)."""
    index = math.floor((value - CELL_CENTER_OFFSET) / (CELL_SIZE / 2) + 0.5)
    return max(0, min(CANVAS_SIZE - 1, index))


def _to_canvas(point):
    """Convert a map point to a (row, column) canvas position.

    Row 0 is the top of the map, so larger y values appear higher.
    """
    col = _axis_index(point[0])
    row = CANVAS_SIZE - 1 - _axis_index(point[1])
    return row, col


def _fmt_point(point):
    """Format a point as '(x,y)'."""
    return f"({point[0]},{point[1]})"


class DisplayManager:
    """Renders maps, route plans, status snapshots and tables as text."""

    def render_map(self, riders=(), orders=(), route=None):
        """Render the 8x8 grid as an ASCII map.

        Args:
            riders: Riders to mark with 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') positions
                are marked. Completed orders are skipped.
            route: Optional list of waypoints drawn with '#'.

        Returns:
            Multi-line string containing the map and a legend.
        """
        canvas = [["." if r % 2 == 0 and c % 2 == 0 else " "
                   for c in range(CANVAS_SIZE)] for r in range(CANVAS_SIZE)]
        if route:
            for start, end in zip(route, route[1:]):
                self._draw_segment(canvas, start, end)
        for order in orders:
            if order.status == "completed":
                continue
            self._put(canvas, order.res_pos, "S")
            self._put(canvas, order.cus_pos, "C")
        for rider in riders:
            self._put(canvas, rider.position, "R")

        header = "  " + "".join(
            str(c // 2) if c % 2 == 0 else " " for c in range(CANVAS_SIZE))
        lines = [header.rstrip()]
        for row_index, row in enumerate(canvas):
            axis = CANVAS_SIZE - 1 - row_index
            label = f"{axis // 2} " if axis % 2 == 0 else "  "
            lines.append(label + "".join(row))
        lines.append("  (columns: grid x, rows: grid y, top = largest y)")
        lines.append(LEGEND)
        return "\n".join(lines)

    def render_route(self, rider, order, route_points):
        """Describe the planned route of an assigned order with its map.

        Args:
            rider: Rider that received the order (order already appended).
            order: The newly assigned order.
            route_points: Waypoints from the rider through restaurant to customer.

        Returns:
            Multi-line string with the route map, speed and time estimate.
        """
        queued = 0
        prev = rider.position
        for queued_order in rider.orders:
            if queued_order is order:
                break
            queued += manhattan(prev, queued_order.res_pos)
            queued += manhattan(queued_order.res_pos, queued_order.cus_pos)
            prev = queued_order.cus_pos
        route_dist = route_length(route_points)
        total = queued + route_dist
        eta = ticks_for_distance(total, rider.speed)
        lines = [
            f"Route map for rider #{rider.rider_id} "
            f"(speed {rider.speed} units/tick, state {rider.state_name}):",
            self.render_map(riders=[rider], orders=[order],
                            route=route_points),
            "Route: " + " -> ".join(_fmt_point(p) for p in route_points),
            f"Route length {route_dist} units; queued work {queued} units; "
            f"estimated {ticks_for_distance(total, rider.speed)} ticks "
            f"(eta {eta}).",
        ]
        return "\n".join(lines)

    def status_text(self, riders, funds, tick, issues=()):
        """Return a snapshot of funds, riders and their orders.

        Args:
            riders: Iterable of Rider objects.
            funds: Current system funds.
            tick: Current simulated tick.
            issues: Optional consistency issue strings to report.

        Returns:
            Multi-line status string.
        """
        riders = list(riders)
        lines = [f"Tick: {tick}", f"System funds: {funds}",
                 f"Riders: {len(riders)}"]
        if not riders:
            lines.append("  No riders on duty.")
        for rider in riders:
            cell = (rider.x // CELL_SIZE, rider.y // CELL_SIZE)
            order_ids = [o.id for o in rider.orders] or "none"
            lines.append(
                f"  Rider #{rider.rider_id} | {rider.state_name:<11} | "
                f"pos ({rider.x},{rider.y}) cell {cell} | "
                f"speed {rider.speed} | orders {order_ids}"
                + (" | special" if rider.special_case else ""))
        if issues:
            lines.append("Consistency issues:")
            lines.extend(f"  ! {issue}" for issue in issues)
        return "\n".join(lines)

    def orders_text(self, orders):
        """Return a table of all orders with timing and rider data.

        Args:
            orders: Iterable of Order objects.

        Returns:
            Multi-line table string.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        header = (f"{'ID':<5}{'Start':>7}  {'Restaurant':<12}"
                  f"{'Customer':<12}{'Dist':>6}{'Taken':>7}  "
                  f"{'Rider':<7}Status")
        lines = [header, "-" * len(header)]
        for order in orders:
            rider = f"#{order.rider_id}" if order.rider_id is not None else "-"
            taken = (str(order.time_taken) if order.time_taken is not None
                     else "-")
            lines.append(
                f"{order.id:<5}{order.start_time:>7}  "
                f"{_fmt_point(order.res_pos):<12}"
                f"{_fmt_point(order.cus_pos):<12}"
                f"{order.distance:>6}{taken:>7}  {rider:<7}{order.status}")
        return "\n".join(lines)

    def riders_text(self, riders):
        """Return the full status-change log of every rider.

        Args:
            riders: Iterable of Rider objects.

        Returns:
            Multi-line string with one line per recorded event.
        """
        riders = list(riders)
        if not riders:
            return "No riders on duty."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} (currently "
                         f"{rider.state_name}):")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = (f"order #{entry['order_id']}"
                         if entry["order_id"] is not None else "-")
                lines.append(
                    f"  tick {entry['tick']:>5} | {entry['event']:<22} | "
                    f"{order:<10} | pos ({entry['x']},{entry['y']}) | "
                    f"state {entry['state']}")
        return "\n".join(lines)

    def history_text(self, history):
        """Return the numbered command history."""
        if not history:
            return "No commands in history."
        return "\n".join(f"{i:>4}  {cmd}" for i, cmd in
                         enumerate(history, start=1))

    @staticmethod
    def _put(canvas, point, symbol):
        """Place ``symbol`` at the canvas position of ``point``."""
        row, col = _to_canvas(point)
        canvas[row][col] = symbol

    @staticmethod
    def _draw_segment(canvas, start, end):
        """Draw an axis-aligned street segment with '#' between nodes."""
        r1, c1 = _to_canvas(start)
        r2, c2 = _to_canvas(end)
        for row in range(min(r1, r2), max(r1, r2) + 1):
            for col in range(min(c1, c2), max(c1, c2) + 1):
                if canvas[row][col] == " ":
                    canvas[row][col] = "#"


__all__ = ["DisplayManager", "STATE_NAMES"]
