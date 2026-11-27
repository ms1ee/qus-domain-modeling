"""Status and map display."""

STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Formats system information."""

    def __init__(self, system):
        self.system = system

    def map_text(self, route=None, order=None):
        n = self.system.grid.grid_dimension
        g = self.system.grid
        cells = [["." for _ in range(n)] for _ in range(n)]
        for p in route or []:
            cx, cy = g.cell_of(*p)
            cells[cy][cx] = "#"
        for r in self.system.riders:
            cx, cy = g.cell_of(r.x, r.y)
            cells[cy][cx] = "R"
        for o in self.system.order_manager.orders:
            if o.status == "completed":
                continue
            cx, cy = g.cell_of(*o.res_pos)
            cells[cy][cx] = "S"
            cx, cy = g.cell_of(*o.cus_pos)
            cells[cy][cx] = "C"
        return "\n".join(" ".join(row) for row in cells)

    def route_text(self, rider, order):
        from path_planner import PathPlanner
        pp = PathPlanner()
        pts = pp.plan_multi([(rider.x, rider.y), order.res_pos, order.cus_pos])
        length = pp.path_length(pts)
        time = -(-length // rider.speed)
        path = " -> ".join("(%d,%d)" % p for p in pts)
        return "%s\nSpeed: %d, estimated time: %d ticks\n%s" % (
            path, rider.speed, time, self.map_text(route=pts))

    def status_text(self):
        s = self.system
        lines = ["Tick: %d  Funds: %d  Riders: %d" % (s.tick, s.funds, len(s.riders))]
        for r in s.riders:
            lines.append("Rider %d at (%d,%d) %s orders=%s" % (
                r.rider_id, r.x, r.y, STATE_NAMES[r.state],
                [o.id for o in r.orders]))
        lines.append(self.map_text())
        return "\n".join(lines)

    def orders_text(self):
        orders = self.system.order_manager.orders
        if not orders:
            return "No orders."
        lines = []
        for o in orders:
            lines.append("Order %d start=%d restaurant=%s customer=%s dist=%d "
                         "time=%s rider=%s status=%s" % (
                             o.id, o.start_time, o.res_pos, o.cus_pos,
                             o.distance, o.time_taken, o.rider_id, o.status))
        return "\n".join(lines)

    def riders_text(self):
        if not self.system.riders:
            return "No riders."
        lines = []
        for r in self.system.riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%d (%d,%d) %s order=%s" % (
                    e["time"], e["x"], e["y"], e["event"], e["order_id"]))
        return "\n".join(lines)
