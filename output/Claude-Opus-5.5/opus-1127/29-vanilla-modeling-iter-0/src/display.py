"""Status display and ASCII map rendering."""

from path_planner import PathPlanner, GRID_DIM
from rider import STATE_NAMES


class DisplayManager:
    """Builds textual views of the system."""

    def render_map(self, system, route=None, orders=None):
        """Render the 8x8 ASCII map.

        'R' rider, 'S' restaurant, 'C' customer, '#' route/street, '.' empty.
        ``route`` is (start, waypoints); ``orders`` restricts S/C markers.
        """
        grid = [["." for _ in range(GRID_DIM)] for _ in range(GRID_DIM)]
        if route:
            start, waypoints = route
            for pt in PathPlanner.sample_points(start, waypoints):
                c, r = PathPlanner.to_cell(*pt)
                grid[r][c] = "#"
        if orders is None:
            orders = [o for o in system.orders if o.status != "completed"]
        for o in orders:
            c, r = PathPlanner.to_cell(*o.cus_pos)
            grid[r][c] = "C"
        for o in orders:
            c, r = PathPlanner.to_cell(*o.res_pos)
            grid[r][c] = "S"
        for rider in system.riders:
            c, r = PathPlanner.to_cell(rider.x, rider.y)
            grid[r][c] = "R"
        lines = ["    " + " ".join(str(i) for i in range(GRID_DIM)) + "   (x/100)"]
        for r in range(GRID_DIM):
            lines.append("%2d  " % r + " ".join(grid[r]))
        lines.append("(y/100)  R=Rider S=Restaurant C=Customer #=Route .=Empty")
        return "\n".join(lines)

    def rider_route(self, rider, order):
        """Return (start, waypoints, eta_ticks) for ``order`` on ``rider``."""
        start = (rider.x, rider.y)
        eta_before = 0
        prev = start
        for o in rider.orders:
            if o is order:
                break
            wps = []
            if o.status in ("assigned", "pending", "picking_up"):
                wps = PathPlanner.multi_route(prev, [o.res_pos, o.cus_pos])
            else:
                wps = PathPlanner.plan_route(prev, o.cus_pos)
            eta_before += PathPlanner.route_length(prev, wps)
            prev = o.cus_pos
        waypoints = PathPlanner.multi_route(prev, [order.res_pos, order.cus_pos])
        length = PathPlanner.route_length(prev, waypoints)
        eta = PathPlanner.estimate_ticks(eta_before + length, rider.speed)
        return prev, waypoints, eta, length

    def show_start_result(self, system, order, rider, new_rider):
        """Text output for the start command."""
        lines = [
            "Order #%d created at tick %d" % (order.id, order.start_time),
            "Restaurant grid coordinates: (%d, %d)" % order.res_pos,
            "Customer grid coordinates:   (%d, %d)" % order.cus_pos,
            "New rider added: %s" % (
                "yes (rider %d)" % new_rider.rider_id if new_rider else "no"),
        ]
        if rider is None:
            lines.append("No rider available; order is pending "
                         "(funds: %d)." % system.funds)
            lines.append(self.render_map(system, orders=[order]))
            return "\n".join(lines)
        start, waypoints, eta, length = self.rider_route(rider, order)
        path = " -> ".join("(%d,%d)" % p for p in [start] + waypoints)
        lines.append("Assigned rider: %d at (%d, %d)" % (rider.rider_id,
                                                          rider.x, rider.y))
        lines.append("Speed: %d units/tick  Route length: %d  "
                     "Estimated time: %d ticks" % (rider.speed, length, eta))
        lines.append("Route: " + path)
        lines.append(self.render_map(system, route=(start, waypoints),
                                     orders=[order]))
        return "\n".join(lines)

    def show_status(self, system):
        """System snapshot."""
        lines = ["Tick: %d" % system.tick,
                 "Funds: %d" % system.funds,
                 "Riders: %d" % len(system.riders)]
        for r in system.riders:
            lines.append("  Rider %d at (%d, %d) state=%s orders=%d %s%s" % (
                r.rider_id, r.x, r.y, STATE_NAMES.get(r.state, "?"),
                len(r.orders), [o.id for o in r.orders],
                " [special]" if r.special_case else ""))
        lines.append(self.render_map(system))
        return "\n".join(lines)

    def show_orders(self, system):
        """Order table."""
        if not system.orders:
            return "No orders."
        lines = ["%-4s %-6s %-11s %-11s %-9s %-6s %-6s %-11s" % (
            "ID", "Start", "Restaurant", "Customer", "Distance", "Time",
            "Rider", "Status")]
        for o in system.orders:
            lines.append("%-4d %-6d %-11s %-11s %-9.2f %-6s %-6s %-11s" % (
                o.id, o.start_time, "(%d,%d)" % o.res_pos,
                "(%d,%d)" % o.cus_pos, o.distance,
                "-" if o.time_taken is None else str(o.time_taken),
                "-" if o.rider_id is None else str(o.rider_id), o.status))
        return "\n".join(lines)

    def show_riders(self, system):
        """Rider status-change history."""
        if not system.riders:
            return "No riders."
        lines = []
        for r in system.riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s (%d, %d) %-22s order=%s" % (
                    e.get("time"), e.get("x", 0), e.get("y", 0), e["event"],
                    "-" if e["order_id"] is None else e["order_id"]))
        return "\n".join(lines)
