"""Command-line entry point."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import globalvar  # noqa: E402
from system import init_system, SystemManager  # noqa: E402
from order import OrderManager  # noqa: E402
from display import DisplayManager  # noqa: E402
from input_manager import InputManager  # noqa: E402
from path_planner import PathPlanner  # noqa: E402

try:
    import readline  # noqa: F401
except ImportError:
    pass


def save_state(path="state.json"):
    data = {"funds": globalvar.get_value("funds"),
            "time": globalvar.get_value("time"),
            "riders": [{"id": r.rider_id, "x": r.x, "y": r.y,
                        "speed": r.speed, "state": r.state,
                        "orders": [o.id for o in r.orders]}
                       for r in globalvar.get_value("riders")],
            "orders": [o.to_dict() for o in globalvar.get_value("orders")]}
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        print("Could not save state:", e)


def do_start():
    try:
        coords = InputManager.parse_coords(
            input("Enter restaurant_x restaurant_y customer_x customer_y: "))
    except ValueError as e:
        print("Error:", e)
        return
    order = OrderManager.create(coords)
    hired = SystemManager.maybe_recruit()
    rider = OrderManager.assign(order)
    if rider is None:
        print("No rider available; order pending.")
    print("Restaurant grid:", order.res_pos, "Customer grid:", order.cus_pos)
    print("New rider added:", hired)
    if rider:
        route = PathPlanner.route((rider.x, rider.y), order.res_pos,
                                  order.cus_pos)
        dist = sum(abs(b[0] - a[0]) + abs(b[1] - a[1])
                   for a, b in zip(route, route[1:]))
        print("Rider %d speed %d, est. time %d ticks" % (
            rider.rider_id, rider.speed, -(-dist // rider.speed)))
        print(DisplayManager.map_text([rider], [order], route))


def main():
    init_system()
    print("Commands: start, status, orders, riders, quit/exit, (enter = tick)")
    while globalvar.get_value("running"):
        try:
            cmd = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        try:
            if cmd in ("quit", "exit", "q"):
                break
            elif cmd in ("start", "s"):
                do_start()
            elif cmd == "status":
                print(DisplayManager.status_text())
                print(DisplayManager.map_text(
                    globalvar.get_value("riders"),
                    [o for o in globalvar.get_value("orders")
                     if o.status != "completed"]))
            elif cmd == "orders":
                print(DisplayManager.orders_text())
            elif cmd == "riders":
                print(DisplayManager.riders_text())
            elif cmd and cmd != "tick":
                print("Unknown command.")
                continue
        except Exception as e:  # recovery
            print("Error:", e)
            continue
        SystemManager.tick()
    globalvar.set_value("running", False)
    save_state()


if __name__ == "__main__":
    main()
