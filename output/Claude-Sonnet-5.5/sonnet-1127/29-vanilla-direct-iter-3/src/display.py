"""Display helpers."""
import globalvar

STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


def render_map(rider=None, order=None):
    """ASCII 8x8 map; route drawn for the rider's first order."""
    grid = [["." for _ in range(8)] for _ in range(8)]
    for r in globalvar.get_value("riders", []):
        grid[min(r.y // 100, 7)][min(r.x // 100, 7)] = "R"
    if rider is not None and rider.orders:
        o = rider.orders[0]
        pts = [(rider.x, rider.y), o.res_pos, o.cus_pos]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            for x in range(min(x1, x2) // 100, max(x1, x2) // 100 + 1):
                c = grid[min(y1 // 100, 7)][min(x, 7)]
                if c == ".":
                    grid[min(y1 // 100, 7)][min(x, 7)] = "#"
            for y in range(min(y1, y2) // 100, max(y1, y2) // 100 + 1):
                c = grid[min(y, 7)][min(x2 // 100, 7)]
                if c == ".":
                    grid[min(y, 7)][min(x2 // 100, 7)] = "#"
    for o in globalvar.get_value("orders", []):
        if o.status != "completed":
            rx, ry = o.res_pos[0] // 100, o.res_pos[1] // 100
            cx, cy = o.cus_pos[0] // 100, o.cus_pos[1] // 100
            grid[ry][rx] = "S"
            grid[cy][cx] = "C"
    return "\n".join(" ".join(row) for row in grid)


def status_text():
    lines = ["Time: %d  Funds: %d  Riders: %d" % (
        globalvar.get_value("time", 0), globalvar.get_value("funds", 0),
        len(globalvar.get_value("riders", [])))]
    for r in globalvar.get_value("riders", []):
        lines.append("Rider %d at (%d,%d) %s, orders: %s" % (
            r.rider_id, r.x, r.y, STATE_NAMES[r.state],
            [o.id for o in r.orders]))
    return "\n".join(lines)


def orders_text():
    lines = []
    for o in globalvar.get_value("orders", []):
        taken = (o.end_time - o.start_time) if o.end_time is not None else "-"
        lines.append("Order %d start=%d res=%s cus=%s dist=%d time=%s "
                     "rider=%s status=%s" % (
                         o.id, o.start_time, o.res_pos, o.cus_pos,
                         o.distance, taken, o.rider_id, o.status))
    return "\n".join(lines) or "No orders."


def riders_text():
    lines = []
    for r in globalvar.get_value("riders", []):
        for e in r.log:
            lines.append("Rider %d t=%d %s order=%s at (%d,%d)" % (
                r.rider_id, e["time"], e["event"], e["order_id"],
                e["x"], e["y"]))
    return "\n".join(lines) or "No riders."
