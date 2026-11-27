"""Display and map visualization."""
import globalvar

STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Renders status and maps."""

    def render_map(self, route=None, order=None):
        grid = [["." for _ in range(16)] for _ in range(16)]
        for i in range(16):
            for j in range(16):
                if i % 2 == 0 or j % 2 == 0:
                    grid[j][i] = "#"

        def cell(p):
            return min(p[0] // 50, 15), min(p[1] // 50, 15)

        for p in route or []:
            cx, cy = cell(p)
            grid[cy][cx] = "*"
        orders = [order] if order else [
            o for o in globalvar.get_value("orders", [])
            if o.status != "completed"]
        for o in orders:
            sx, sy = cell(o.res_pos)
            grid[sy][sx] = "S"
            cx, cy = cell(o.cus_pos)
            grid[cy][cx] = "C"
        for r in globalvar.get_value("riders", []):
            cx, cy = cell((r.x, r.y))
            grid[cy][cx] = "R"
        return "\n".join("".join(row) for row in grid)

    def status(self):
        riders = globalvar.get_value("riders", [])
        lines = ["Tick: %d  Funds: %d  Riders: %d" % (
            globalvar.get_value("tick", 0), globalvar.get_value("funds"),
            len(riders))]
        for r in riders:
            lines.append("Rider %d at (%d,%d) %s, orders: %s" % (
                r.rider_id, r.x, r.y, STATE_NAMES[r.state],
                [o.id for o in r.orders]))
        return "\n".join(lines)

    def orders(self):
        lines = []
        for o in globalvar.get_value("orders", []):
            lines.append(
                "Order %d start=%d res=%s cus=%s dist=%d time=%s rider=%s [%s]"
                % (o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
                   o.time_taken, o.rider_id, o.status))
        return "\n".join(lines) or "No orders."

    def riders_log(self):
        lines = []
        for r in globalvar.get_value("riders", []):
            for h in r.history:
                lines.append("Rider %d t=%d (%d,%d) state=%d order=%s %s" % (
                    r.rider_id, h["time"], h["x"], h["y"], h["state"],
                    h["order_id"], h["event"]))
        return "\n".join(lines) or "No riders."
