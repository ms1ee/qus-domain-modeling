"""Command-line entry point for the food delivery dispatch simulator."""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import globalvar  # noqa: E402
import system  # noqa: E402
from display import DisplayManager  # noqa: E402
from input_manager import InputManager  # noqa: E402
from order import OrderManager  # noqa: E402
from path_planner import PathPlanner  # noqa: E402
import persistence  # noqa: E402

HELP = """Commands:
  start [rx ry cx cy] (s)  create an order (restaurant + customer coords)
  status (st)              system funds and rider status
  orders (o)               all order details
  riders (r)               rider status change history
  map (m)                  show the ASCII map
  tick [n] (t)             advance simulation n ticks (default 1)
  save [file] / load [file] persist state as JSON (default state.json)
  history (hist)           show command history
  help (h)                 this help
  quit / exit (q)          exit
Each command also advances the simulation by one tick."""


def _route_for(rider, order, planner):
    """Planned route from the rider's queue end through the order."""
    start = (rider.x, rider.y)
    others = [o for o in rider.active_orders() if o is not order]
    if others:
        start = tuple(others[-1].cus_pos)
    return planner.plan_multi(start, [order.res_pos, order.cus_pos],
                              rider.speed)


def handle_start(args, im, om, dm, planner):
    if not args:
        raw = input("Enter restaurant_x restaurant_y customer_x customer_y: ")
        args = raw.replace(",", " ").replace("[", " ").replace("]", " ") \
            .split()
    try:
        rx, ry, cx, cy = im.validate_coordinates(args)
    except ValueError as exc:
        print("Error: %s" % exc)
        return
    result = om.create_order((rx, ry), (cx, cy))
    order, rider = result["order"], result["rider"]
    print("Order %d created." % order.id)
    print("Restaurant grid coordinates: (%d, %d)" % order.res_pos)
    print("Customer grid coordinates:   (%d, %d)" % order.cus_pos)
    if result["recruited"]:
        print("New rider added: Rider %d (funds now %s)" % (
            result["recruited"].rider_id, globalvar.get_value("funds")))
    else:
        print("No new rider added.")
    if rider is None:
        print("No rider available; order is pending.")
        return
    route = _route_for(rider, order, planner)
    print("Assigned to Rider %d (speed %d units/tick)" % (
        rider.rider_id, rider.speed))
    print("Route: " + " -> ".join("(%d,%d)" % p for p in route.points))
    print("Distance: %d units, estimated time: %d ticks" % (
        route.length, route.estimated_time))
    print(dm.render_map(route.points, [order]))


def main():
    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s %(message)s")
    system.init_system(system.load_config())
    im = InputManager()
    om = OrderManager()
    dm = DisplayManager()
    planner = PathPlanner()
    print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        try:
            cmd, args = im.parse_command(line)
            if not cmd:
                continue
            advance = True
            if cmd == "start":
                handle_start(args, im, om, dm, planner)
            elif cmd == "status":
                print(dm.status_text())
            elif cmd == "orders":
                print(dm.orders_text())
            elif cmd == "riders":
                print(dm.riders_text())
            elif cmd == "map":
                print(dm.render_map())
            elif cmd == "tick":
                n = int(args[0]) if args else 1
                system.advance_tick(n)
                advance = False
                print("Advanced to tick %s" % globalvar.get_value(
                    "current_tick"))
            elif cmd == "save":
                persistence.save_state(args[0] if args else "state.json")
                print("Saved.")
            elif cmd == "load":
                persistence.load_state(args[0] if args else "state.json")
                print("Loaded.")
            elif cmd == "history":
                for i, h in enumerate(im.command_history, 1):
                    print("%3d  %s" % (i, h))
            elif cmd == "help":
                print(HELP)
            elif cmd in ("quit", "exit"):
                globalvar.set_value("running", False)
                advance = False
            else:
                print("Unknown command '%s'. Type 'help'." % cmd)
                advance = False
            if advance:
                system.advance_tick(1)
        except Exception as exc:  # graceful recovery
            print("Error: %s" % exc)
            system.SystemManager(init=False).check_consistency()
    print("Goodbye.")


if __name__ == "__main__":
    main()
