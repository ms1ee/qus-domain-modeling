"""Command-line interface for the dispatch simulator."""
import globalvar
import system
import order as order_mod

NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


def parse_coords(parts):
    """Validate four integers in 0-800."""
    if len(parts) != 4:
        raise ValueError("Expected 4 integers: rx ry cx cy")
    try:
        vals = [int(p) for p in parts]
    except ValueError:
        raise ValueError("Coordinates must be integers")
    if any(v < 0 or v > 800 for v in vals):
        raise ValueError("Coordinates must be within 0-800")
    return vals


def draw_map(rider=None, order=None):
    grid = [["." for _ in range(8)] for _ in range(8)]
    for r in globalvar.get_value("riders", []):
        grid[min(r.y // 100, 7)][min(r.x // 100, 7)] = "R"
    if order:
        grid[order.res_pos[1] // 100][order.res_pos[0] // 100] = "S"
        grid[order.cus_pos[1] // 100][order.cus_pos[0] // 100] = "C"
    return "\n".join(" ".join(row) for row in grid)


def cmd_start(args):
    vals = parse_coords(args)
    o, r, recruited = order_mod.create_and_assign(vals[:2], vals[2:])
    dist = abs(r.x - o.res_pos[0]) + abs(r.y - o.res_pos[1]) + o.distance
    print("Restaurant grid: (%d,%d) Customer grid: (%d,%d)" % (
        o.res_pos[0] // 100, o.res_pos[1] // 100,
        o.cus_pos[0] // 100, o.cus_pos[1] // 100))
    print("New rider added:", recruited)
    print("Rider %d speed %d, est. time %d ticks" % (
        r.rider_id, r.speed, -(-dist // r.speed)))
    print(draw_map(order=o))


def cmd_status():
    print("Funds:", globalvar.get_value("funds"), "Tick:", globalvar.get_value("tick"))
    riders = globalvar.get_value("riders")
    print("Riders:", len(riders))
    for r in riders:
        print("  #%d (%d,%d) %s orders=%s" % (
            r.rider_id, r.x, r.y, NAMES[r.state], [o.id for o in r.orders]))
    print(draw_map())


def cmd_orders():
    for o in globalvar.get_value("orders"):
        print("Order %d start=%d rest=%s cust=%s dist=%d time=%s rider=%s %s" % (
            o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
            o.time_taken, o.rider_id, o.status))


def cmd_riders():
    for r in globalvar.get_value("riders"):
        for e in r.log:
            print("Rider %d t=%d (%d,%d) %s order=%s" % (
                r.rider_id, e["time"], e["x"], e["y"], e["event"], e["order_id"]))


def main():
    system.init_system()
    history = []
    aliases = {"s": "start", "st": "status", "o": "orders", "r": "riders", "q": "quit"}
    while globalvar.get_value("running"):
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            continue
        history.append(line)
        parts = line.split()
        cmd = aliases.get(parts[0].lower(), parts[0].lower())
        try:
            if cmd == "start":
                if len(parts) == 1:
                    parts += input("rx ry cx cy: ").split()
                cmd_start(parts[1:])
            elif cmd == "status":
                cmd_status()
            elif cmd == "orders":
                cmd_orders()
            elif cmd == "riders":
                cmd_riders()
            elif cmd == "history":
                print("\n".join(history))
            elif cmd in ("quit", "exit"):
                globalvar.set_value("running", False)
                continue
            else:
                print("Unknown command")
                continue
        except ValueError as e:
            print("Error:", e)
            continue
        system.tick()


if __name__ == "__main__":
    main()
