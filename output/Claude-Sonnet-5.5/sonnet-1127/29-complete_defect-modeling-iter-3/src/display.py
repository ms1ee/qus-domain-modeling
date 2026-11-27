"""Display helpers."""
import globalvar

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


def render_map(riders=(), orders=(), route=()):
    """Render an 8x8 ASCII map."""
    g = [["." for _ in range(8)] for _ in range(8)]
    for p in route:
        cx, cy = min(p[0] // 100, 7), min(p[1] // 100, 7)
        g[cy][cx] = "#"
    for o in orders:
        g[o.res_pos[1] // 100][o.res_pos[0] // 100] = "S"
        g[o.cus_pos[1] // 100][o.cus_pos[0] // 100] = "C"
    for r in riders:
        g[min(r.y // 100, 7)][min(r.x // 100, 7)] = "R"
    return "\n".join(" ".join(row) for row in reversed(g))


def status_text():
    """Return system status text."""
    riders = globalvar.get_value("riders")
    lines = ["Time: %s  Funds: %s  Riders: %d" % (
        globalvar.get_value("time"), globalvar.get_value("funds"),
        len(riders))]
    for r in riders:
        lines.append("Rider %d at (%d,%d) %s orders=%s" % (
            r.rider_id, r.x, r.y, STATES[r.state],
            [o.id for o in r.orders]))
    return "\n".join(lines)


def orders_text():
    """Return order details."""
    lines = []
    for o in globalvar.get_value("orders"):
        lines.append("Order %d start=%s res=%s cus=%s dist=%s time=%s rider=%s %s"
                     % (o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
                        o.time_taken, o.rider_id, o.status))
    return "\n".join(lines) or "No orders."


def riders_text():
    """Return rider event logs."""
    lines = []
    for r in globalvar.get_value("riders"):
        for e in r.log:
            lines.append("Rider %d t=%s (%s,%s) %s order=%s" % (
                r.rider_id, e["time"], e["x"], e["y"], e["event"],
                e["order_id"]))
    return "\n".join(lines) or "No riders."
