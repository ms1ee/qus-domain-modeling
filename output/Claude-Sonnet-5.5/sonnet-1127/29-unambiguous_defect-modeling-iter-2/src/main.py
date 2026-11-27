"""Command-line entry point."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import globalvar  # noqa: E402
import system  # noqa: E402
from order_model import Order  # noqa: E402
from order import assign_order  # noqa: E402
from pathplanner import PathPlanner  # noqa: E402
from display import DisplayManager  # noqa: E402
from inputmgr import InputManager  # noqa: E402

HELP = ("Commands: start(s), status(st), orders(o), riders(r), "
        "history, help(h), quit/exit(q)")


def do_start(im):
    line = input("Enter restaurant_x restaurant_y customer_x customer_y: ")
    try:
        c = im.parse_coords(line)
    except ValueError as e:
        print("Error:", e)
        return
    order = Order((c[0], c[1]), (c[2], c[3]))
    rider, new = assign_order(order)
    if rider is None:
        print("Error: no rider available and insufficient funds.")
        return
    print("Restaurant grid: %s  Customer grid: %s" % (
        order.res_pos, order.cus_pos))
    print("New rider added: %s (rider %d)" % ("yes" if new else "no",
                                             rider.rider_id))
    pts = [rider.pos, order.res_pos, order.cus_pos]
    route = PathPlanner.waypoints(pts)
    dist = PathPlanner.distance(pts[0], pts[1]) + order.distance
    print("Speed: %d  Estimated time: %d ticks" % (
        rider.speed, math.ceil(dist / rider.speed)))
    print(DisplayManager.render_map(route, [rider], order.res_pos,
                                    order.cus_pos))


def main():
    system.init_system()
    im = InputManager()
    print(HELP)
    while globalvar.get_value("running"):
        try:
            cmd = im.parse_command(input("> "))
        except (EOFError, KeyboardInterrupt):
            break
        try:
            if cmd == "quit":
                globalvar.set_value("running", False)
                continue
            elif cmd == "start":
                do_start(im)
            elif cmd == "status":
                print(DisplayManager.status())
            elif cmd == "orders":
                print(DisplayManager.orders())
            elif cmd == "riders":
                print(DisplayManager.riders())
            elif cmd == "history":
                print("\n".join(im.history))
            elif cmd == "help":
                print(HELP)
            elif cmd:
                print("Unknown command. " + HELP)
        except Exception as e:  # graceful recovery
            print("Error:", e)
        system.tick()
    try:
        system.save_state("state.json")
    except OSError:
        pass
    print("Bye.")


if __name__ == "__main__":
    main()
