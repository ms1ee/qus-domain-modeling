"""Display manager: status and ASCII map."""

import globalvar
from gridmap import GRID
from pathplanner import PathPlanner

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Renders status, orders, logs, and map."""

    def __init__(self, system):
        self.system = system
        self.planner = PathPlanner()

    def render_map(self, route_cells=(), riders=True, orders=True):
        grid = [["." for _ in range(GRID.cols)] for _ in range(GRID.rows)]
        for c, r in route_cells:
            grid[r][c] = "#"
        if orders:
            for o in globalvar.get_value("orders", []):
                if o.status == "completed":
                    continue
                c, r = GRID.cell_of(*o.res_pos)
                grid[r][c] = "S"
                if o.status != "pending" or True:
                    if o.rider_id is not None and \
                            self._picked(o):
                        pass
                c, r = GRID.cell_of(*o.cus_pos)
                grid[r][c] = "C"
        if riders:
            for rd in self.system.riders:
                c, r = GRID.cell_of(rd.x, rd.y)
                grid[r][c] = "R"
        return "\n".join(" ".join(row) for row in grid)

    def _picked(self, o):
        return False

    def route_cells(self, start, stops):
        """Cells covered by the path start -> stops."""
        cells = []
        cur = start
        pts = [start] + self.planner.plan_multi(start, stops)
        for a, b in zip(pts, pts[1:]):
            steps = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
            for i in range(0, steps + 1, 10):
                x = a[0] + (0 if b[0] == a[0] else (i if b[0] > a[0] else -i))
                y = a[1] + (0 if b[1] == a[1] else (i if b[1] > a[1] else -i))
                cell = GRID.cell_of(x, y)
                if cell not in cells:
                    cells.append(cell)
        return cells

    def route_report(self, rider, order):
        start = (rider.x, rider.y)
        stops = [order.res_pos, order.cus_pos]
        pts = self.planner.plan_multi(start, stops)
        total = 0
        cur = start
        for p in pts:
            total += abs(p[0] - cur[0]) + abs(p[1] - cur[1])
            cur = p
        ticks = -(-total // rider.speed)
        cells = self.route_cells(start, stops)
        return (self.render_map(cells) +
                "\nRoute length: %d, speed: %d/tick, estimated time: %d ticks"
                % (total, rider.speed, ticks))

    def status(self):
        s = self.system
        lines = ["Tick: %d  Funds: %d  Riders: %d"
                 % (s.tick_count, s.funds, len(s.riders))]
        for r in s.riders:
            lines.append("Rider %d at (%d, %d) state=%s orders=%s (%d)"
                         % (r.rider_id, r.x, r.y, STATES[r.state],
                            [o.id for o in r.orders], len(r.orders)))
        lines.append(self.render_map())
        return "\n".join(lines)

    def orders(self):
        orders = globalvar.get_value("orders", [])
        if not orders:
            return "No orders."
        lines = []
        for o in orders:
            tt = o.time_taken if o.time_taken is not None else "-"
            lines.append("Order %d start=%d restaurant=%s customer=%s "
                         "distance=%.1f time=%s rider=%s status=%s"
                         % (o.id, o.start_time, o.res_pos, o.cus_pos,
                            o.distance, tt, o.rider_id, o.status))
        return "\n".join(lines)

    def rider_logs(self):
        lines = []
        for r in self.system.riders:
            for e in r.log:
                lines.append("t=%d rider=%d pos=(%d, %d) event=%s order=%s"
                             % (e["time"], r.rider_id, e["x"], e["y"],
                                e["event"], e["order_id"]))
        return "\n".join(lines) if lines else "No rider events."
