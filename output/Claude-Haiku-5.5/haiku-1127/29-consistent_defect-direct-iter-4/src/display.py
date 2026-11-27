"""Status text and ASCII map rendering for the command line."""

import logging

from order_model import COMPLETED
from path_planner import is_on_street
from rider import STATE_NAMES  # noqa: F401  (kept for readers of this module)

logger = logging.getLogger(__name__)

MAP_CELLS = 16
MAP_STEP = 50
SYMBOL_EMPTY = "."
SYMBOL_STREET = "#"
SYMBOL_RESTAURANT = "S"
SYMBOL_CUSTOMER = "C"
SYMBOL_RIDER = "R"
SYMBOL_ROUTE = "*"

MAP_LEGEND = ("Legend: R=rider S=restaurant C=customer #=street .=empty "
              "*=route (each cell = 50 units; rows labelled by y)")


def _index(value):
    """Map a coordinate to a 16x16 map index (clamped)."""
    return min(MAP_CELLS - 1, max(0, int(round(value / MAP_STEP))))


class DisplayManager:
    """Renders status snapshots, order tables, logs and the ASCII map."""

    def render_map(self, riders, orders, route=None, show_completed=False):
        """Render the 16x16 ASCII map.

        Args:
            riders: Riders to draw as 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') points
                are drawn.
            route: Optional list of ``(x, y)`` polyline points drawn as '*'.
            show_completed: Whether completed orders are also drawn.

        Returns:
            str: Multi-line map text.
        """
        canvas = [[SYMBOL_STREET if is_on_street(col * MAP_STEP,
                                                 row * MAP_STEP)
                   else SYMBOL_EMPTY
                   for col in range(MAP_CELLS)]
                  for row in range(MAP_CELLS)]
        if route:
            self._draw_route(canvas, route)
        for order in orders:
            if order.status == COMPLETED and not show_completed:
                continue
            self._put(canvas, order.res_pos, SYMBOL_RESTAURANT)
            self._put(canvas, order.cus_pos, SYMBOL_CUSTOMER)
        for rider in riders:
            self._put(canvas, (rider.x, rider.y), SYMBOL_RIDER)
        rows = [f"{row * MAP_STEP:>4} " + " ".join(canvas[row])
                for row in range(MAP_CELLS)]
        return "\n".join(rows + [MAP_LEGEND])

    @staticmethod
    def _put(canvas, pos, symbol):
        """Place a symbol at the map cell nearest to ``pos``."""
        canvas[_index(pos[1])][_index(pos[0])] = symbol

    @staticmethod
    def _draw_route(canvas, route):
        """Draw route segments as connected '*' lines on the canvas."""
        for (x1, y1), (x2, y2) in zip(route, route[1:]):
            c1, r1 = _index(x1), _index(y1)
            c2, r2 = _index(x2), _index(y2)
            if r1 == r2:
                for col in range(min(c1, c2), max(c1, c2) + 1):
                    canvas[r1][col] = SYMBOL_ROUTE
            elif c1 == c2:
                for row in range(min(r1, r2), max(r1, r2) + 1):
                    canvas[row][c1] = SYMBOL_ROUTE
            else:
                # Non-axis segment (should not occur); mark endpoints only.
                canvas[r1][c1] = SYMBOL_ROUTE
                canvas[r2][c2] = SYMBOL_ROUTE

    def render_status(self, funds, riders, issues=None):
        """Render the system status snapshot.

        Args:
            funds: Current system funds.
            riders: List of riders.
            issues: Optional list of consistency warnings.

        Returns:
            str: Status text.
        """
        lines = [f"System funds: {funds}", f"Riders: {len(riders)}"]
        if not riders:
            lines.append("  (no riders recruited yet)")
        for rider in riders:
            active = rider.active_orders()
            order_list = ", ".join(f"#{o.id}" for o in rider.orders) or "none"
            lines.append(
                f"  Rider #{rider.rider_id}: position ({rider.x}, {rider.y}),"
                f" speed {rider.speed}, status {rider.state_name},"
                f" assigned orders {len(rider.orders)}"
                f" (active {len(active)}), order list: {order_list}")
        if issues:
            lines.append("Consistency warnings:")
            lines.extend(f"  - {issue}" for issue in issues)
        return "\n".join(lines)

    def render_orders(self, orders):
        """Render a table of all orders.

        Args:
            orders: Orders to display.

        Returns:
            str: Table text.
        """
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} "
                  f"{'Customer':>12} {'Dist':>6} {'Time':>6} "
                  f"{'Rider':>6} {'Status':>10}")
        lines = [header, "-" * len(header)]
        for order in orders:
            taken = order.time_taken()
            rider = f"#{order.rider_id}" if order.rider_id else "-"
            lines.append(
                f"{order.id:>4} {order.created_tick:>6} "
                f"{str(order.res_pos):>12} {str(order.cus_pos):>12} "
                f"{order.distance:>6} "
                f"{(str(taken) if taken is not None else '-'):>6} "
                f"{rider:>6} {order.status:>10}")
        return "\n".join(lines)

    def render_rider_log(self, riders):
        """Render every recorded status change for all riders.

        Args:
            riders: Riders whose logs should be printed.

        Returns:
            str: Log text.
        """
        if not riders:
            return "No riders recruited yet."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} log:")
            for entry in rider.log:
                order = (f"order #{entry['order_id']}"
                         if entry["order_id"] is not None else "-")
                lines.append(
                    f"  [t={entry['time']}] {entry['event']} | {order} | "
                    f"at ({entry['x']}, {entry['y']}) | "
                    f"state {entry['state']}")
        return "\n".join(lines)

    def render_start_summary(self, order, rider, new_rider, distance, eta):
        """Render the result of the 'start' command.

        Args:
            order: The newly dispatched order.
            rider: The assigned rider.
            new_rider: Whether a rider was recruited for this order.
            distance: Route length in units (rider -> restaurant -> customer).
            eta: Estimated ticks to finish the route.

        Returns:
            str: Summary text.
        """
        recruit = (f"yes (Rider #{rider.rider_id} recruited)"
                   if new_rider else "no")
        return "\n".join([
            f"Order #{order.id} dispatched.",
            f"  Restaurant grid point: {order.res_pos[0]}, {order.res_pos[1]}",
            f"  Customer grid point:   {order.cus_pos[0]}, {order.cus_pos[1]}",
            f"  New rider added: {recruit}",
            f"  Assigned rider: #{rider.rider_id} at ({rider.x}, {rider.y}), "
            f"speed {rider.speed} units/tick, status {rider.state_name}",
            f"  Route length: {distance} units; estimated time: {eta} ticks",
            "  Route map (connected line '*'):",
        ])
