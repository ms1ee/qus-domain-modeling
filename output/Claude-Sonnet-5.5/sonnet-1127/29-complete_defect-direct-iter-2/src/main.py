"""Command-line entry point."""
import json
import globalvar
from system import init_system, SystemManager
from order import OrderManager
from display import DisplayManager
from input_manager import InputManager
from path_planner import PathPlanner


def save(path="state.json"):
    data = {"funds": globalvar.get_value("funds"),
            "tick": globalvar.get_value("tick"),
            "riders": [{"id": r.rider_id, "x": r.x, "y": r.y, "state": r.state,
                        "log": r.log} for r in globalvar.get_value("riders")],
            "orders": [o.to_dict() for o in globalvar.get_value("orders")]}
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        print("Could not save state:", e)


def main():
    init_system()
    sysm, om, disp, im = SystemManager(), OrderManager(), DisplayManager(), InputManager()
    while globalvar.get_value("running"):
        try:
            cmd = im.parse_command(input("> "))
        except EOFError:
            break
        try:
            if cmd == "quit":
                globalvar.set_value("running", False)
            elif cmd == "start":
                coords = im.parse_coords(input("restaurant_x restaurant_y customer_x customer_y: "))
                added = None
                if not globalvar.get_value("riders") or all(
                        r.state != 0 for r in globalvar.get_value("riders")):
                    added = sysm.recruit()
                order, rider = om.create_order(coords)
                if rider is None:
                    print("No rider available (insufficient funds).")
                    continue
                print("Restaurant grid:", (order.res_pos[0] // 100, order.res_pos[1] // 100),
                      "Customer grid:", (order.cus_pos[0] // 100, order.cus_pos[1] // 100))
                print("New rider added:", bool(added))
                route = PathPlanner.route([(rider.x, rider.y), order.res_pos, order.cus_pos])
                n = 0
                while order.status != "completed" and n < 2000:
                    sysm.tick()
                    n += 1
                print(disp.render_map(route, [order]))
                print("Rider %d speed=%d time=%d ticks" % (rider.rider_id, rider.speed, n))
            elif cmd == "tick":
                sysm.tick()
                print(disp.status())
            elif cmd == "status":
                print(disp.status())
                print(disp.render_map(None, globalvar.get_value("orders")))
            elif cmd == "orders":
                print(disp.orders())
            elif cmd == "riders":
                print(disp.riders())
            elif cmd:
                print("Unknown command. Use start/status/orders/riders/tick/quit.")
        except ValueError as e:
            print("Error:", e)
        except EOFError:
            break
        except Exception as e:  # recover gracefully
            print("Unexpected error:", e)
    save()


if __name__ == "__main__":
    main()
