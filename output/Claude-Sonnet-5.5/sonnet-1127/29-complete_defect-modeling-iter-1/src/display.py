"""Display manager."""
import globalvar
from gridmap import GRID
from path_planner import PathPlanner

STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Status and ASCII map rendering."""

    def __init__(self, system):
        self.system = system
        self.planner = PathPlanner()

    def render_map(self, route=None):
        n = GRID.grid_dimension
        size = 2 * n + 1
        g = [["#"] * size for _ in range(size)]
        for i in range(n):
            for j in range(n):
                g[2 * j + 1][2 * i + 1] = "."
        if route:
            for cx, cy in route:
                g[2 * cy + 1][2 * cx + 1] = "*"
        for o in globalvar.get_value("orders", []):
            if o.status != "completed":
                if o.status in ("pending", "assigned", "picking_up"):
                    g[2 * GRID.cell_index(o.res_pos[1]) + 1][
                        2 * GRID.cell_index(o.res_pos[0]) + 1] = "S"
                g[2 * GRID.cell_index(o.cus_pos[1]) + 1][
                    2 * GRID.cell_index(o.cus_pos[0]) + 1] = "C"
        for r in globalvar.get_value("riders"):
            g[2 * GRID.cell_index(r.y) + 1][2 * GRID.cell_index(r.x) + 1] = "R"
        return "\n".join("".join(row) for row in g)

    def route_info(self, rider, order):
        pts = [(rider.x, rider.y), order.res_pos, order.cus_pos]
        dist = self.planner.length(pts)
        t = -(-dist // rider.speed)
        cells = self.planner.route_cells(pts)
        return (self.render_map(cells) + "\nRider %d speed %d, distance %d, "
                "estimated time %d ticks" % (rider.rider_id, rider.speed,
                                             dist, t))

    def status(self):
        riders = globalvar.get_value("riders")
        lines = ["Tick: %d  Funds: %d  Riders: %d" % (
            self.system.tick_count, self.system.funds, len(riders))]
        for r in riders:
            lines.append("Rider %d at (%d,%d) %s orders=%s" % (
                r.rider_id, r.x, r.y, STATE_NAMES[r.state],
                [o.id for o in r.orders]))
        lines.append(self.render_map())
        return "\n".join(lines)

    def orders(self):
        os_ = globalvar.get_value("orders")
        if not os_:
            return "No orders."
        lines = []
        for o in os_:
            lines.append("Order %d start=%s restaurant=%s customer=%s "
                         "distance=%d time_taken=%s rider=%s status=%s" % (
                             o.id, o.start_time, o.res_pos, o.cus_pos,
                             o.distance, o.time_taken, o.rider_id, o.status))
        return "\n".join(lines)

    def riders_log(self):
        lines = []
        for r in globalvar.get_value("riders"):
            for e in r.log:
                lines.append("t=%d rider %d (%d,%d) %s order=%s" % (
                    e["time"], r.rider_id, e["x"], e["y"], e["event"],
                    e["order_id"]))
        return "\n".join(lines) or "No rider records."
