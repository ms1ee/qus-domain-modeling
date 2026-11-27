"""Command-line interface."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import globalvar
import system
from order_model import Order
from order import find_best_rider_for_order


def show_map():
    grid = [["." for _ in range(8)] for _ in range(8)]
    for o in globalvar.get_value("orders"):
        if o.status != "completed":
            grid[o.res_pos[1] // 100][o.res_pos[0] // 100] = "S"
            grid[o.cus_pos[1] // 100][o.cus_pos[0] // 100] = "C"
    for r in globalvar.get_value("riders"):
        grid[min(r.y // 100, 7)][min(r.x // 100, 7)] = "R"
    for row in reversed(grid):
        print(" ".join(row))


def cmd_start(args):
    if len(args) != 4:
        print("Usage: start x1 y1 x2 y2")
        return
    try:
        v = [int(a) for a in args]
    except ValueError:
        print("Coordinates must be integers.")
        return
    if any(n < 0 or n > 800 for n in v):
        print("Coordinates must be within 0-800.")
        return
    o = Order(v[:2], v[2:])
    pending = [x for x in globalvar.get_value("orders") if x.status == "pending"]
    idle = [r for r in globalvar.get_value("riders") if r.state == 0 and not r.orders]
    added = False
    if globalvar.get_value("funds") >= 300 and len(pending) + 1 > len(idle):
        system.create_rider()
        added = True
    rider = find_best_rider_for_order(o)
    globalvar.get_value("orders").append(o)
    if rider is None:
        print("No rider available.")
        return
    o.assign_to(rider.rider_id)
    rider.orders.append(o)
    print("Restaurant grid:", o.res_pos, "Customer grid:", o.cus_pos)
    print("New rider added:", added, "Assigned rider:", rider.rider_id)
    print("Speed:", rider.speed, "Est. ticks:",
          (abs(rider.x - o.res_pos[0]) + abs(rider.y - o.res_pos[1]) + o.distance)
          // rider.speed)


def cmd_status():
    print("Funds:", globalvar.get_value("funds"))
    names = ["idle", "picking up", "delivering"]
    for r in globalvar.get_value("riders"):
        print("Rider %d (%d,%d) %s orders=%s" % (
            r.rider_id, r.x, r.y, names[r.state], [o.id for o in r.orders]))
    show_map()


def cmd_orders():
    for o in globalvar.get_value("orders"):
        t = None if o.finish_time is None else o.finish_time - o.start_time
        print("Order %d start=%d res=%s cus=%s dist=%d time=%s rider=%s %s" % (
            o.id, o.start_time, o.res_pos, o.cus_pos, o.distance, t,
            o.rider_id, o.status))


def cmd_riders():
    for r in globalvar.get_value("riders"):
        for e in r.log:
            print("Rider %d t=%d %s order=%s at (%d,%d)" % (
                r.rider_id, e["time"], e["event"], e["order_id"], e["x"], e["y"]))


def save():
    data = {"funds": globalvar.get_value("funds"),
            "riders": [{"id": r.rider_id, "x": r.x, "y": r.y, "state": r.state}
                       for r in globalvar.get_value("riders")],
            "orders": [{"id": o.id, "res": o.res_pos, "cus": o.cus_pos,
                        "status": o.status}
                       for o in globalvar.get_value("orders")]}
    try:
        with open("state.json", "w") as f:
            json.dump(data, f)
    except OSError:
        pass


def main():
    system.init_system()
    while globalvar.get_value("running"):
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        parts = line.split()
        if not parts:
            system.tick()
            continue
        c = parts[0].lower()
        try:
            if c == "start":
                cmd_start(parts[1:])
            elif c == "status":
                cmd_status()
            elif c == "orders":
                cmd_orders()
            elif c == "riders":
                cmd_riders()
            elif c in ("quit", "exit"):
                globalvar.set_value("running", False)
            else:
                print("Unknown command.")
        except Exception as e:
            print("Error:", e)
        system.tick()
    save()


if __name__ == "__main__":
    main()
