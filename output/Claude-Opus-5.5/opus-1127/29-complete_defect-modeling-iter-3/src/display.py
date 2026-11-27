"""Status displays and ASCII map visualisation."""

from grid_map import MAP_SIZE
from order_model import OrderStatus
from rider import RiderState

HALF = 50
CANVAS = MAP_SIZE // HALF + 1  # 17 characters: streets on even indices


def _idx(v):
    return max(0, min(CANVAS - 1, (int(v) + HALF // 2) // HALF))


class DisplayManager:
    """Renders system status, order/rider reports and the ASCII map."""

    def __init__(self, system):
        self.system = system

    # Map ----------------------------------------------------------------
    def render_map(self, route_points=None, orders=None, riders=None):
        """Return the ASCII map.

        '#' streets, '.' blocks, 'S' restaurant, 'C' customer, 'R' rider,
        '-', '|', '+' route segments.
        """
        if orders is None:
            orders = [o for o in self.system.orders
                      if o.status != OrderStatus.COMPLETED]
        if riders is None:
            riders = self.system.riders
        grid = [["#" if (r % 2 == 0 or c % 2 == 0) else "."
                 for c in range(CANVAS)] for r in range(CANVAS)]
        if route_points:
            pts = [(_idx(x), _idx(y)) for x, y in route_points]
            for (c1, r1), (c2, r2) in zip(pts, pts[1:]):
                if r1 == r2:
                    for c in range(min(c1, c2), max(c1, c2) + 1):
                        grid[r1][c] = "-"
                elif c1 == c2:
                    for r in range(min(r1, r2), max(r1, r2) + 1):
                        grid[r][c1] = "|"
            for c, r in pts:
                grid[r][c] = "+"
        for o in orders:
            grid[_idx(o.res_pos[1])][_idx(o.res_pos[0])] = "S"
            grid[_idx(o.cus_pos[1])][_idx(o.cus_pos[0])] = "C"
        for rd in riders:
            grid[_idx(rd.y)][_idx(rd.x)] = "R"
        lines = ["y\\x  " + " ".join(str(c // 2) if c % 2 == 0 else " "
                                      for c in range(CANVAS))]
        for r in range(CANVAS):
            label = str(r // 2) if r % 2 == 0 else " "
            lines.append("%3s  %s" % (label, " ".join(grid[r])))
        lines.append("(axis labels x100 units; # street, . block, S restaurant,"
                     " C customer, R rider, -|+ route)")
        return "\n".join(lines)

    # Reports ------------------------------------------------------------
    def status_text(self):
        s = self.system
        lines = ["=== System Status (t=%d) ===" % s.current_time,
                 "Funds: %d" % s.funds,
                 "Riders: %d" % len(s.riders),
                 "Pending (unassigned) orders: %d"
                 % len(s.order_manager.pending_orders())]
        for r in s.riders:
            lines.append(
                "  Rider #%d at (%d,%d) speed=%d state=%d(%s) orders=%s "
                "special=%s distance=%d delivered=%d"
                % (r.rider_id, r.x, r.y, r.speed, r.state,
                   RiderState.name(r.state),
                   [o.id for o in r.pending_orders()], r.special_case,
                   r.total_distance, r.completed_count))
        return "\n".join(lines)

    def orders_text(self):
        orders = self.system.orders
        if not orders:
            return "No orders yet."
        lines = ["%-4s %-6s %-12s %-12s %-6s %-6s %-6s %-11s %s"
                 % ("ID", "Start", "Restaurant", "Customer", "Dist",
                    "Taken", "Rider", "Status", "Efficiency")]
        for o in orders:
            lines.append("%-4d %-6d %-12s %-12s %-6d %-6s %-6s %-11s %s" % (
                o.id, o.start_time, "(%d,%d)" % o.res_pos,
                "(%d,%d)" % o.cus_pos, o.distance,
                "-" if o.time_taken is None else o.time_taken,
                "-" if o.rider_id is None else "#%d" % o.rider_id,
                o.status, "-" if o.efficiency is None else o.efficiency))
        return "\n".join(lines)

    def riders_text(self):
        riders = self.system.riders
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider #%d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s %-22s at (%d,%d) order=%s state=%s"
                             % (e.get("time"), e.get("event"), e.get("x", 0),
                                e.get("y", 0),
                                "-" if e.get("order_id") is None
                                else "#%s" % e.get("order_id"),
                                e.get("state_name", "")))
        return "\n".join(lines)

    def start_report(self, result):
        order = result["order"]
        rider = result["rider"]
        new_rider = result["new_rider"]
        route = result["route"]
        lines = [
            "Order #%d created at t=%d" % (order.id, order.start_time),
            "Restaurant: input %s -> grid cell %s, center %s"
            % (order.raw_res_pos, order.res_grid, order.res_pos),
            "Customer:   input %s -> grid cell %s, center %s"
            % (order.raw_cus_pos, order.cus_grid, order.cus_pos),
            "New rider added: %s" % ("Yes (rider #%d)" % new_rider.rider_id
                                     if new_rider else "No"),
            "Funds: %d" % self.system.funds,
        ]
        if rider is None:
            lines.append("No rider available; order queued as pending.")
            lines.append(self.render_map(orders=[order]))
        else:
            lines.append("Assigned rider: #%d (speed %d units/tick)"
                         % (rider.rider_id, rider.speed))
            lines.append("Route: %s" % " -> ".join(
                "(%d,%d)" % p for p in route.waypoints()))
            lines.append("Route distance: %d units, estimated time: %d ticks%s"
                         % (route.total_distance, route.estimated_time,
                            " (special-case detour)" if route.special_case
                            else ""))
            lines.append(self.render_map(route.waypoints(), orders=[order],
                                         riders=[rider]))
        return "\n".join(lines)
