"""Command-line interface."""
import json
import globalvar
from system import init_system
from order import find_best_rider_for_order
from order_model import Order

NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


def tick():
    """Advance simulated time one tick."""
    globalvar.set_value("time", globalvar.get_value("time") + 1)
    for r in globalvar.get_value("riders"):
        r.move()


def render(route=None):
    """ASCII map."""
    grid = [["." for _ in range(8)] for _ in range(8)]
    for o in globalvar.get_value("orders"):
        if o.status != "completed":
            grid[o.res_pos[1] // 100][o.res_pos[0] // 100] = "R"
            grid[o.cus_pos[1] // 100][o.cus_pos[0] // 100] = "C"
    for r in globalvar.get_value("riders"):
        gx, gy = min(7, r.x // 100), min(7, r.y // 100)
        grid[gy][gx] = "B"
    return "\n".join(" ".join(row) for row in reversed(grid))


def handle(cmd):
    """Process a command; return False on quit."""
    cmd = cmd.strip().lower()
    if cmd in ("quit", "exit", "q"):
        globalvar.set_value("running", False)
        return False
    if cmd in ("status", "s"):
        print("Funds:", globalvar.get_value("funds"))
        for r in globalvar.get_value("riders"):
            print(r.rider_id, (r.x, r.y), NAMES[r.state],
                  [o.id for o in r.orders])
        print(render())
    elif cmd == "orders":
        for o in globalvar.get_value("orders"):
            t = (o.end_time - o.start_time) if o.end_time is not None else "-"
            print(o.id, o.start_time, o.res_pos, o.cus_pos, o.distance, t,
                  o.rider_id)
    elif cmd == "riders":
        for r in globalvar.get_value("riders"):
            for e in r.log:
                print(r.rider_id, e)
    elif cmd == "save":
        data = {"funds": globalvar.get_value("funds"),
                "riders": [{"id": r.rider_id, "x": r.x, "y": r.y}
                           for r in globalvar.get_value("riders")],
                "orders": [{"id": o.id, "res": o.res_pos, "cus": o.cus_pos,
                            "status": o.status}
                           for o in globalvar.get_value("orders")]}
        with open("state.json", "w") as f:
            json.dump(data, f)
        print("saved")
    elif cmd in ("start", "st"):
        raw = input("Enter rx ry cx cy: ").replace(",", " ").split()
        try:
            v = [int(a) for a in raw]
        except ValueError:
            print("Error: integers required")
            return True
        if len(v) != 4 or any(a < 0 or a > 800 for a in v):
            print("Error: need 4 integers in 0-800")
            return True
        before = len(globalvar.get_value("riders"))
        o = Order((v[0], v[1]), (v[2], v[3]))
        r = find_best_rider_for_order(o)
        if r is None:
            print("No rider available")
            return True
        r.orders.append(o)
        o.assign_to(r.rider_id)
        print("Restaurant:", o.res_pos, "Customer:", o.cus_pos)
        print("New rider added:", len(globalvar.get_value("riders")) > before)
        print("Rider", r.rider_id, "speed", r.speed, "ETA ticks",
              (abs(r.x - o.res_pos[0]) + abs(r.y - o.res_pos[1])
               + o.distance) // r.speed + 1)
        print(render())
    elif cmd:
        print("Unknown command. Use start/status/orders/riders/quit")
    return True


def main():
    """Run the simulator."""
    init_system()
    while globalvar.get_value("running"):
        try:
            cmd = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        try:
            if not handle(cmd):
                break
        except Exception as exc:  # recover gracefully
            print("Error:", exc)
        tick()


if __name__ == "__main__":
    main()
