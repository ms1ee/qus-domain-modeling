"""Status display and ASCII map visualisation."""

from grid_map import MAP_SIZE
from order_model import STATUS_COMPLETED
from rider import STATE_NAMES

STEP = 50
SIZE = MAP_SIZE // STEP + 1  # 17 positions per axis

EVENT_NAMES = {
    "spawn": "spawned",
    "accepted_order": "accepted order",
    "arrived_at_merchant": "arrived at merchant",
    "delivered_to_customer": "delivered to customer",
}


def _idx(value):
    return max(0, min(SIZE - 1, int(round(value / STEP))))


class DisplayManager:
    """Formats system state into text. All methods return strings."""

    LEGEND = ("Legend: R=restaurant C=customer @=rider start digit=rider id "
              "*=route +=intersection -,|=streets (y grows downward)")

    def __init__(self, system):
        self.system = system

    # ------------------------------------------------------------------ maps
    @staticmethod
    def _base_grid():
        grid = []
        for r in range(SIZE):
            row = []
            for c in range(SIZE):
                if r % 2 == 0 and c % 2 == 0:
                    row.append("+")
                elif r % 2 == 0:
                    row.append("-")
                elif c % 2 == 0:
                    row.append("|")
                else:
                    row.append(" ")
            grid.append(row)
        return grid

    @staticmethod
    def _draw_route(grid, points):
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            c1, r1, c2, r2 = _idx(x1), _idx(y1), _idx(x2), _idx(y2)
            if r1 == r2:
                for c in range(min(c1, c2), max(c1, c2) + 1):
                    grid[r1][c] = "*"
            else:
                for r in range(min(r1, r2), max(r1, r2) + 1):
                    grid[r][c1] = "*"

    @staticmethod
    def _render(grid):
        header = "     " + " ".join(str(c // 2) if c % 2 == 0 else " "
                                    for c in range(SIZE))
        lines = [header + "   (x100)"]
        for r, row in enumerate(grid):
            label = f"{(r // 2) * 100:>3}" if r % 2 == 0 else "   "
            lines.append(f"{label}  " + " ".join(row))
        return "\n".join(lines)

    def render_map(self, route_points=None, highlight_order=None, rider=None):
        """Render the 8x8 grid with riders, active orders and an optional route."""
        grid = self._base_grid()
        if route_points:
            self._draw_route(grid, route_points)
        orders = [highlight_order] if highlight_order else [
            o for o in self.system.orders if o.status != STATUS_COMPLETED]
        for order in orders:
            grid[_idx(order.restaurant_y)][_idx(order.restaurant_x)] = "R"
            grid[_idx(order.customer_y)][_idx(order.customer_x)] = "C"
        if route_points:
            sx, sy = route_points[0]
            grid[_idx(sy)][_idx(sx)] = "@"
        riders = [rider] if rider is not None else self.system.riders
        for r in riders:
            if route_points and r is rider:
                continue
            grid[_idx(r.y)][_idx(r.x)] = str(r.rider_id % 10)
        return self._render(grid) + "\n" + self.LEGEND

    # --------------------------------------------------------------- reports
    def format_order_result(self, result):
        """Format the result of a ``start`` command."""
        order, rider, route = result["order"], result["rider"], result["route"]
        lines = [
            f"Order #{order.id} created at t={order.start_time}",
            f"  Input: {order.raw_input}",
            f"  Restaurant grid position: {order.res_pos}",
            f"  Customer grid position:   {order.cus_pos}",
        ]
        if result["new_rider"]:
            lines.append(f"  New rider added: Yes (Rider #{rider.rider_id}, cost "
                         f"{self.system.recruitment_cost}, funds now {self.system.funds})")
        else:
            lines.append("  New rider added: No")
        lines.append(f"  Assigned rider: #{rider.rider_id} at {rider.position} "
                     f"({rider.state_name}, {len(rider.active_orders())} order(s) queued)")
        pts = " -> ".join(f"({x},{y})" for x, y in route.points)
        lines.append(f"  Route: {pts}")
        lines.append(f"  Speed: {route.speed} units/tick, length: {route.length} units, "
                     f"estimated time: {route.estimated_time} ticks")
        lines.append(self.render_map(route.points, order, rider))
        return "\n".join(lines)

    def format_status(self):
        """Snapshot of funds, riders and their orders."""
        riders = self.system.riders
        lines = [
            f"=== Status at t={self.system.current_time} ===",
            f"Funds: {self.system.funds}",
            f"Riders: {len(riders)}",
        ]
        if not riders:
            lines.append("  (no riders yet)")
        for r in riders:
            ids = [getattr(o, "id", "?") for o in r.active_orders()]
            lines.append(
                f"  Rider #{r.rider_id}: pos=({r.x},{r.y}) state={r.state} "
                f"({STATE_NAMES.get(r.state, '?')}) speed={r.speed} "
                f"orders={ids} completed={r.completed_orders}"
                + (" [special case]" if r.special_case else ""))
        lines.append(self.render_map())
        return "\n".join(lines)

    def format_orders(self):
        """Table of all orders."""
        orders = self.system.orders
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>3} {'Start':>5} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Dist':>5} {'Taken':>5} {'Rider':>5}  Status")
        lines = [header, "-" * len(header)]
        for o in orders:
            taken = "-" if o.time_taken is None else str(o.time_taken)
            rider = "-" if o.rider_id is None else str(o.rider_id)
            lines.append(
                f"{o.id:>3} {o.start_time:>5} {str(o.res_pos):>12} {str(o.cus_pos):>12} "
                f"{o.distance:>5} {taken:>5} {rider:>5}  {o.status}")
        return "\n".join(lines)

    def format_rider_logs(self):
        """All recorded status changes for every rider."""
        riders = self.system.riders
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append(f"Rider #{r.rider_id} (travelled {r.distance_travelled} units):")
            for e in r.log:
                order = "" if e.get("order_id") is None else f" order #{e['order_id']}"
                lines.append(f"  t={e.get('time', 0):>4} ({e.get('x')},{e.get('y')}) "
                             f"{EVENT_NAMES.get(e['event'], e['event'])}{order}")
        return "\n".join(lines)

    @staticmethod
    def format_events(events):
        """Format tick events."""
        lines = []
        for rider_id, e in events:
            order = "" if e.get("order_id") is None else f" order #{e['order_id']}"
            lines.append(f"[t={e.get('time')}] Rider #{rider_id} "
                         f"{EVENT_NAMES.get(e['event'], e['event'])}{order} "
                         f"at ({e.get('x')},{e.get('y')})")
        return "\n".join(lines)

    @staticmethod
    def help_text():
        """Command help."""
        return "\n".join([
            "Commands (shortcut in brackets):",
            "  start [n] [rx ry cx cy]  create an order (coords 0-800)",
            "  status [s]               funds, riders and map",
            "  orders [o]               all order details",
            "  riders [r]               rider status-change history",
            "  map [m]                  show the map",
            "  tick [t] [N]             advance N ticks (default 1)",
            "  run                      run until all orders are delivered",
            "  history [h]              command history",
            "  save                     save state to JSON",
            "  help [?]                 this help",
            "  quit / exit [q]          exit",
            "Each command iteration advances the simulation by one tick.",
        ])
