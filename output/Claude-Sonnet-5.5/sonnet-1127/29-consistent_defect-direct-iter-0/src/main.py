"""Command-line entry point."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import globalvar
from system import init_system
from order import OrderManager
from display import DisplayManager
from input_manager import InputManager
from pathplanner import PathPlanner


def save_state(path="state.json"):
    data = {"funds": globalvar.get_value("funds"),
            "riders": [{"id": r.rider_id, "x": r.x, "y": r.y,
                        "state": r.state} for r in globalvar.get_value("riders")],
            "orders": [o.to_dict() for o in globalvar.get_value("orders")]}
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def tick():
    globalvar.set_value("time", globalvar.get_value("time") + 1)
    for r in globalvar.get_value("riders"):
        r.move()


def main():
    init_system()
    disp, inp, om = DisplayManager(), InputManager(), OrderManager()
    history = []
    print("Commands: start, status, orders, riders, tick [n], history, quit")
    while globalvar.get_value("running"):
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        history.append(line)
        cmd, _, rest = line.partition(" ")
        cmd = cmd.lower()
        try:
            if cmd in ("quit", "exit", "q"):
                globalvar.set_value("running", False)
            elif cmd == "start":
                if not rest:
                    rest = input("Enter rx ry cx cy: ")
                vals = inp.parse_coords(rest)
                order, rider, new = om.create_order(vals[:2], vals[2:])
                print("Restaurant cell:", order.res_pos,
                      "Customer cell:", order.cus_pos)
                print("New rider added:", new)
                path = PathPlanner().plan(
                    (rider.x, rider.y), [order.res_pos, order.cus_pos])
                total = sum(abs(a[0] - b[0]) + abs(a[1] - b[1])
                            for a, b in zip(path, path[1:]))
                print("Speed %d, est. time %d ticks" % (
                    rider.speed, -(-total // rider.speed)))
                print(disp.map(path=path))
                tick()
            elif cmd == "tick":
                for _ in range(int(rest) if rest else 1):
                    tick()
                print("Time:", globalvar.get_value("time"))
            elif cmd == "status":
                print(disp.status())
                print(disp.map())
            elif cmd == "orders":
                print(disp.orders())
            elif cmd == "riders":
                print(disp.riders_log())
            elif cmd == "history":
                print("\n".join(history))
            else:
                print("Unknown command")
        except ValueError as e:
            print("Error:", e)
        except Exception as e:  # recover gracefully
            print("Unexpected error:", e)
        save_state()


if __name__ == "__main__":
    main()
