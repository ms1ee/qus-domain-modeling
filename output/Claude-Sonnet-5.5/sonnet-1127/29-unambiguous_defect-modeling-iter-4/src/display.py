"""ASCII display helpers."""
import globalvar
from path_planner import PathPlanner

STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


def _cell(v):
    return max(0, min(7, v // 100))


def render_map(rider=None, order=None):
    """Render 8x8 map. R rider, S restaurant, C customer, . empty, * route."""
    grid = [["." for _ in range(8)] for _ in range(8)]
    if rider is not None and order is not None:
        pts = PathPlanner.plan((rider.x, rider.y),
                               [order.res_pos, order.cus_pos])
        for a, b in zip(pts, pts[1:]):
            steps = max(abs(a[0] - b[0]), abs(a[1] - b[1])) // 50
            for i in range(steps + 1):
                x = a[0] + (b[0] - a[0]) * i // max(steps, 1)
                y = a[1] + (b[1] - a[1]) * i // max(steps, 1)
                grid[_cell(y)][_cell(x)] = "*"
    for o in globalvar.get_value("orders", []):
        if o.status != "completed":
            if o.status in ("pending", "assigned"):
                grid[_cell(o.res_pos[1])][_cell(o.res_pos[0])] = "S"
            grid[_cell(o.cus_pos[1])][_cell(o.cus_pos[0])] = "C"
    for r in globalvar.get_value("riders", []):
        grid[_cell(r.y)][_cell(r.x)] = "R"
    return "\n".join(" ".join(row) for row in reversed(grid))


def render_status():
    lines = ["Tick: %d  Funds: %d  Riders: %d" % (
        globalvar.get_value("tick", 0), globalvar.get_value("funds", 0),
        len(globalvar.get_value("riders", [])))]
    for r in globalvar.get_value("riders", []):
        lines.append("Rider %d at (%d,%d) %s speed=%d orders=%s" % (
            r.rider_id, r.x, r.y, STATE_NAMES[r.state], r.speed,
            [o.id for o in r.orders]))
    return "\n".join(lines)


def render_orders():
    orders = globalvar.get_value("orders", [])
    if not orders:
        return "No orders."
    return "\n".join(
        "Order %d start=%d rest=%s cust=%s dist=%d time=%s rider=%s [%s]" % (
            o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
            o.time_taken, o.rider_id, o.status) for o in orders)


def render_riders():
    lines = []
    for r in globalvar.get_value("riders", []):
        for e in r.log:
            lines.append("t=%d rider %d (%d,%d) %s order=%s" % (
                e["time"], r.rider_id, e["x"], e["y"], e["event"],
                e["order_id"]))
    return "\n".join(lines) or "No records."
