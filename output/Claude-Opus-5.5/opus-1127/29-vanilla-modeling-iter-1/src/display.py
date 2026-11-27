"""Status displays and ASCII map rendering."""

from path_planner import GRID_DIM, PathPlanner, _clamp_cell
from rider import RiderState


class DisplayManager:
    """Formats system information as text."""

    def __init__(self, system):
        self.system = system

    @staticmethod
    def _fmt_pos(pos):
        return "(%d, %d)" % (pos[0], pos[1])

    def render_map(self, riders=None, orders=None, route_points=None):
        """Render the 8x8 map.

        Symbols: R rider, S restaurant, C customer, # route/street, . empty.
        """
        riders = self.system.riders if riders is None else riders
        if orders is None:
            orders = [o for o in self.system.order_manager.orders
                      if o.status != "completed"]
        grid = [["." for _ in range(GRID_DIM)] for _ in range(GRID_DIM)]
        if route_points:
            for (c, r) in PathPlanner.cells_on_path(route_points):
                grid[r][c] = "#"
        for o in orders:
            grid[_clamp_cell(o.cus_pos[1])][_clamp_cell(o.cus_pos[0])] = "C"
        for o in orders:
            grid[_clamp_cell(o.res_pos[1])][_clamp_cell(o.res_pos[0])] = "S"
        for rd in riders:
            grid[_clamp_cell(rd.y)][_clamp_cell(rd.x)] = "R"
        lines = ["    " + " ".join(str(i) for i in range(GRID_DIM))]
        for idx, row in enumerate(grid):
            lines.append("%3d " % (idx * 100) + " ".join(row))
        lines.append("Legend: R=Rider S=Restaurant C=Customer #=Route .=Empty")
        return "\n".join(lines)

    def format_order_result(self, result):
        """Format output of SystemManager.place_order."""
        order = result["order"]
        lines = [
            "Order #%d created" % order.id,
            "  Restaurant grid position: %s" % self._fmt_pos(order.res_pos),
            "  Customer grid position:   %s" % self._fmt_pos(order.cus_pos),
        ]
        if result["new_riders"]:
            ids = ", ".join(str(r.rider_id) for r in result["new_riders"])
            lines.append("  New rider added: yes (id %s), funds now %d"
                         % (ids, self.system.funds))
        else:
            lines.append("  New rider added: no")
        rider = result["rider"]
        if rider is None:
            lines.append("  No rider available; order is pending.")
            return "\n".join(lines)
        route = result["route"]
        lines.append("  Assigned rider: %d at %s (%s, %d queued orders)"
                     % (rider.rider_id, self._fmt_pos(rider.position),
                        rider.state_name, len(rider.orders)))
        lines.append("  Route: " + " -> ".join(self._fmt_pos(p) for p in route.points))
        lines.append("  Speed: %d units/tick, Distance: %d, Estimated time: %d ticks"
                     % (route.speed, route.length, route.estimated_time))
        lines.append(self.render_map(riders=[rider], orders=[order],
                                     route_points=route.points))
        return "\n".join(lines)

    def format_status(self):
        """Snapshot of funds and riders."""
        s = self.system
        lines = ["Time: %d   Funds: %d   Riders: %d"
                 % (s.current_tick, s.funds, len(s.riders))]
        for r in s.riders:
            lines.append("  Rider %d: pos=%s state=%s orders=%d %s"
                         % (r.rider_id, self._fmt_pos(r.position),
                            RiderState.NAMES.get(r.state, r.state),
                            len(r.orders), [o.id for o in r.orders
                                            if hasattr(o, "id")]))
        pending = s.order_manager.pending_orders()
        lines.append("Pending (unassigned) orders: %d" % len(pending))
        lines.append(self.render_map())
        return "\n".join(lines)

    def format_orders(self):
        """Table of all orders."""
        orders = self.system.order_manager.orders
        if not orders:
            return "No orders."
        lines = ["%-4s %-6s %-12s %-12s %-8s %-6s %-6s %-10s"
                 % ("ID", "Start", "Restaurant", "Customer", "Distance",
                    "Taken", "Rider", "Status")]
        for o in orders:
            lines.append("%-4d %-6d %-12s %-12s %-8d %-6s %-6s %-10s" % (
                o.id, o.start_time or 0, self._fmt_pos(o.res_pos),
                self._fmt_pos(o.cus_pos), o.distance,
                "-" if o.time_taken is None else o.time_taken,
                "-" if o.rider_id is None else o.rider_id, o.status))
        return "\n".join(lines)

    def format_rider_logs(self):
        """Every recorded status change for all riders."""
        if not self.system.riders:
            return "No riders."
        lines = []
        for r in self.system.riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s %-22s pos=(%s, %s) order=%s" % (
                    e.get("time"), e.get("event"), e.get("x"), e.get("y"),
                    "-" if e.get("order_id") is None else e.get("order_id")))
        return "\n".join(lines)
