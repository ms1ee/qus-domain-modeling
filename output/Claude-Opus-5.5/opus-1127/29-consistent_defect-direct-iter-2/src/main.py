"""Command-line entry point for the food delivery dispatch simulator."""

import math

import globalvar
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from path_planner import PathPlanner
from system_manager import SystemManager

HELP = ("Commands: start(s), status(st), orders(o), riders(r), "
        "history, help(h), quit(q)/exit")


def main():
    sm = SystemManager("config.json")
    om = OrderManager()
    dm = DisplayManager()
    im = InputManager()
    print("Food Delivery Dispatch Simulator. " + HELP)
    while globalvar.get_value("running"):
        try:
            text = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        cmd = im.parse_command(text)
        try:
            if cmd is None:
                print("Unknown command. " + HELP)
            elif cmd == "help":
                print(HELP)
            elif cmd == "history":
                print("\n".join(im.history))
            elif cmd == "quit":
                globalvar.set_value("running", False)
            elif cmd == "start":
                raw = input("Enter restaurant_x restaurant_y customer_x customer_y: ")
                coords = im.parse_coords(raw)
                order, rider, recruited = om.create_order(coords)
                print("Restaurant grid: %s  Customer grid: %s" % (order.res_grid, order.cus_grid))
                print("New rider added: %s" % ("yes" if recruited else "no"))
                if rider is None:
                    print("No rider available; order pending.")
                    continue
                route = PathPlanner.plan_multi((rider.x, rider.y),
                                               [order.res_pos, order.cus_pos])
                length = PathPlanner.route_length(route)
                print("Assigned rider %d speed=%d estimated time=%d ticks" % (
                    rider.rider_id, rider.speed, math.ceil(length / rider.speed)))
                print(dm.render(route=route, orders=[order]))
                ticks = sm.run_until_complete(order)
                print("Order %d completed in %d ticks." % (order.id, ticks))
            elif cmd == "status":
                print(dm.status())
            elif cmd == "orders":
                print(dm.orders())
            elif cmd == "riders":
                print(dm.riders())
        except ValueError as exc:
            print("Input error: %s" % exc)
        except Exception as exc:
            print("Error: %s" % exc)
    sm.save()
    print("Goodbye.")


if __name__ == "__main__":
    main()
