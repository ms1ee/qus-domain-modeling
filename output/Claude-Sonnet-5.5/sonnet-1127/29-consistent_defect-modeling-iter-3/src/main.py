"""Command-line entry point."""
import math

import globalvar
from display import DisplayManager
from inputmanager import InputManager
from system import init_system

HELP = ("Commands: start (s), status (st), orders (o), riders (r), "
        "tick [n] (n), help, quit/exit (q)")


def do_start(sm, disp, im):
    try:
        vals = im.parse_coords(input("Enter rx ry cx cy: "))
    except ValueError as e:
        print("Error:", e)
        return
    order, rider, recruited = sm.submit_order(*vals)
    print("Restaurant grid: %s  Customer grid: %s" % (order.res_pos,
                                                     order.cus_pos))
    print("New rider added: %s" % ("yes" if recruited else "no"))
    if rider is None:
        print("No rider available yet; order %d queued." % order.id)
        return
    start = (rider.x, rider.y)
    route = [start] + sm.planner.plan_multi(start,
                                            [order.res_pos, order.cus_pos])
    total = sm.planner.length(start, route[1:])
    print("Order %d assigned to rider %d, speed %d, distance %d, "
          "est. time %d ticks" % (order.id, rider.rider_id, rider.speed,
                                  total, math.ceil(total / rider.speed)))
    print(disp.render_map(route))


def main():
    sm = init_system()
    disp = DisplayManager()
    im = InputManager()
    print("Food Delivery Dispatch System")
    print(HELP)
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        try:
            cmd, args = im.parse_command(line)
            if cmd is None:
                continue
            if cmd in ("quit", "exit"):
                break
            elif cmd == "start":
                do_start(sm, disp, im)
            elif cmd == "status":
                print(disp.status())
                print(disp.render_map())
            elif cmd == "orders":
                print(disp.orders())
            elif cmd == "riders":
                print(disp.rider_logs())
            elif cmd == "tick":
                n = int(args[0]) if args else 1
                sm.tick(max(1, n))
                print("Time:", globalvar.get_value("tick"))
                continue
            elif cmd == "help":
                print(HELP)
            else:
                print("Unknown command. " + HELP)
                continue
        except Exception as e:  # graceful recovery
            print("Error:", e)
            continue
        sm.tick()
    globalvar.set_value("running", False)
    try:
        sm.save()
    except OSError as e:
        print("Could not save state:", e)


if __name__ == "__main__":
    main()
