"""Command-line entry point."""
import json
import globalvar
import system
import display
from order_model import Order
import order as order_mod


def tick():
    globalvar.set_value("time", globalvar.get_value("time", 0) + 1)
    for r in globalvar.get_value("riders"):
        r.move()


def parse_coords(parts):
    if len(parts) != 4:
        raise ValueError("Need exactly four integers.")
    vals = [int(p) for p in parts]
    if any(v < 0 or v > 800 for v in vals):
        raise ValueError("Coordinates must be within 0-800.")
    return vals


def save(path="state.json"):
    data = {"funds": globalvar.get_value("funds"),
            "orders": [o.to_dict() for o in globalvar.get_value("orders")],
            "riders": [{"id": r.rider_id, "x": r.x, "y": r.y,
                        "state": r.state, "log": r.log}
                       for r in globalvar.get_value("riders")]}
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def main():
    system.init_system()
    while globalvar.get_value("running"):
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        parts = line.split()
        if not parts:
            tick()
            continue
        cmd = parts[0].lower()
        try:
            if cmd in ("quit", "exit", "q"):
                globalvar.set_value("running", False)
            elif cmd in ("start", "s"):
                v = parse_coords(parts[1:])
                o = Order(v[:2], v[2:])
                rider, hired = order_mod.dispatch(o)
                print("Restaurant:", o.res_pos, "Customer:", o.cus_pos)
                print("New rider added:", hired)
                if rider:
                    eta = (abs(rider.x - o.res_pos[0])
                           + abs(rider.y - o.res_pos[1]) + o.distance)
                    print("Rider %d speed %d, est. time %d ticks" % (
                        rider.rider_id, rider.speed,
                        -(-eta // rider.speed)))
                    print(display.render_map(rider))
                else:
                    print("No rider available (insufficient funds).")
                tick()
            elif cmd == "status":
                print(display.status_text())
                print(display.render_map())
            elif cmd == "orders":
                print(display.orders_text())
            elif cmd == "riders":
                print(display.riders_text())
            elif cmd == "tick":
                n = int(parts[1]) if len(parts) > 1 else 1
                for _ in range(n):
                    tick()
            else:
                print("Unknown command. Use start/status/orders/riders/"
                      "tick/quit.")
        except ValueError as e:
            print("Error:", e)
    try:
        save()
    except OSError:
        pass


if __name__ == "__main__":
    main()
