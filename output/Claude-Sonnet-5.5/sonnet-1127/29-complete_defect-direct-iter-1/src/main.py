"""Command line entry point."""

import logging
import globalvar
from system import init_system, SystemManager, ORDER_FEE
from order import OrderManager
from display import DisplayManager
from input_manager import InputManager

try:
    import readline  # noqa: F401
except ImportError:
    pass

HELP = ("Commands: start [rx ry cx cy] (st), status (s), orders (o), "
        "riders (r), tick [n] (t), run, save [file], help (h), quit (q)")


def handle_start(args, sm, om, dm, im):
    if not args.strip():
        args = input("Enter restaurant_x restaurant_y customer_x "
                     "customer_y: ")
    coords = im.parse_coords(args)
    sm.add_funds(ORDER_FEE)
    added = sm.check_recruit()
    order = om.create_order(coords)
    rider = om.assign(order)
    print("Restaurant grid: (%d,%d)  Customer grid: (%d,%d)" % (
        order.res_pos[0] // 100, order.res_pos[1] // 100,
        order.cus_pos[0] // 100, order.cus_pos[1] // 100))
    print("New rider added: %s" % ("yes" if added else "no"))
    if rider is None:
        print("No rider available; order %d is pending." % order.id)
        return
    pts, dist, t = dm.route_info(rider, order)
    print("Order %d assigned to rider %d (speed %d, distance %d, "
          "estimated time %d ticks)" % (order.id, rider.rider_id,
                                        rider.speed, dist, t))
    print(dm.render_map(pts))


def main():
    logging.basicConfig(level=logging.WARNING)
    init_system()
    sm, om, dm, im = SystemManager(), OrderManager(), DisplayManager(), \
        InputManager()
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
            if cmd == "quit":
                globalvar.set_value("running", False)
            elif cmd == "help":
                print(HELP)
            elif cmd == "start":
                handle_start(args, sm, om, dm, im)
            elif cmd == "status":
                print(dm.status())
            elif cmd == "orders":
                print(dm.orders())
            elif cmd == "riders":
                print(dm.riders())
            elif cmd == "tick":
                n = int(args) if args.strip() else 1
                for _ in range(max(0, n)):
                    om.assign_pending()
                    sm.tick()
                print(dm.status())
            elif cmd == "run":
                guard = 0
                while guard < 10000:
                    om.assign_pending()
                    if not sm.busy():
                        break
                    sm.tick()
                    guard += 1
                print(dm.status())
            elif cmd == "save":
                sm.save(args.strip() or "state.json")
                print("Saved.")
            else:
                print("Unknown command '%s'. Type help." % cmd)
        except ValueError as e:
            print("Error: %s" % e)
        except Exception as e:  # recover gracefully
            logging.exception("unexpected error")
            print("Unexpected error: %s" % e)
    print("Bye.")


if __name__ == "__main__":
    main()
