"""Command-line entry point."""
import globalvar
import system

HELP = "Commands: start, status, orders, riders, tick [n], help, quit/exit"


def parse_coords(text):
    """Parse four integers in 0-1000."""
    parts = text.replace(",", " ").replace("[", " ").replace("]", " ").split()
    if len(parts) != 4:
        raise ValueError("need exactly four integers")
    vals = [int(p) for p in parts]
    for v in vals:
        if not 0 <= v <= 1000:
            raise ValueError("coordinates must be within 0-1000")
    return vals


def render_map(points_route=None):
    """ASCII map of 16x16."""
    g = [["#" if (i % 2 == 0 or j % 2 == 0) else "." for j in range(16)]
         for i in range(16)]
    for o in globalvar.get_value("orders"):
        if o.status != "completed":
            rx, ry = o.res_pos
            cx, cy = o.cus_pos
            g[min(15, ry // 50)][min(15, rx // 50)] = "S"
            g[min(15, cy // 50)][min(15, cx // 50)] = "C"
    for r in globalvar.get_value("riders"):
        g[min(15, r.y // 50)][min(15, r.x // 50)] = "R"
    return "\n".join("".join(row) for row in g)


def show_status():
    print("Time:", globalvar.get_value("time"),
          "Funds:", globalvar.get_value("funds"))
    riders = globalvar.get_value("riders")
    print("Riders:", len(riders))
    names = {0: "idle", 1: "picking up", 2: "delivering"}
    for r in riders:
        print("  #%d at (%d,%d) %s orders=%s" % (
            r.rider_id, r.x, r.y, names[r.state], [o.id for o in r.orders]))
    print(render_map())


def show_orders():
    for o in globalvar.get_value("orders"):
        t = (o.end_time - o.start_time) if o.end_time is not None else "-"
        print("Order %d start=%s from=%s to=%s dist=%d time=%s rider=%s %s" % (
            o.id, o.start_time, o.res_pos, o.cus_pos, o.distance, t,
            o.rider_id, o.status))


def show_riders():
    for r in globalvar.get_value("riders"):
        print("Rider", r.rider_id)
        for e in r.log:
            print("  t=%s (%s,%s) %s order=%s" % (
                e["time"], e["x"], e["y"], e["event"], e["order_id"]))


def main():
    system.init_system()
    print(HELP)
    while globalvar.get_value("running"):
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        parts = line.split(None, 1)
        if not parts:
            system.tick()
            continue
        cmd = parts[0].lower()
        try:
            if cmd in ("quit", "exit", "q"):
                break
            elif cmd in ("start", "s"):
                text = parts[1] if len(parts) > 1 else input(
                    "Enter restaurant x y customer x y: ")
                order, rider, rec = system.submit_order(parse_coords(text))
                print("Restaurant:", order.res_pos, "Customer:", order.cus_pos)
                print("New rider added:", rec)
                print("Assigned rider:", rider.rider_id if rider else None,
                      "speed:", rider.speed if rider else "-")
                if rider:
                    print("Estimated time:", (abs(rider.x - order.res_pos[0])
                          + abs(rider.y - order.res_pos[1]) + order.distance)
                          // rider.speed + 1, "ticks")
                print(render_map())
            elif cmd == "status":
                show_status()
            elif cmd == "orders":
                show_orders()
            elif cmd == "riders":
                show_riders()
            elif cmd == "tick":
                n = int(parts[1]) if len(parts) > 1 else 1
                for _ in range(n):
                    system.tick()
                show_status()
            elif cmd == "help":
                print(HELP)
            else:
                print("Unknown command. " + HELP)
        except ValueError as e:
            print("Error:", e)
        except Exception as e:  # recover gracefully
            print("Unexpected error:", e)
    print("Bye.")


if __name__ == "__main__":
    main()
