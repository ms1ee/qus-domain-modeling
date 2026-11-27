"""Command-line entry point of the food delivery dispatch simulator."""

import logging
import sys

import globalvar
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from system import SystemManager

HELP = """Commands (shortcut in brackets):
  start [rx ry cx cy] (s)  create an order (coordinates 0-800)
  status (st)              funds and rider states
  orders (o)               all orders
  riders (r)               rider status change log
  map (m)                  show the ASCII map
  tick [n] (t)             advance the simulation n ticks
  save                     save state to JSON
  history (hist)           command history; '!!' repeats, '!n' runs n-th
  help (h, ?)              this help
  quit / exit (q, x)       leave the program
Every command line also advances the simulation by one tick."""


def handle(cmd, args, sysm, om, dm, im):
    """Execute one command. Returns True if a tick should follow."""
    if cmd == "start":
        text = args or im.read("Enter restaurant_x restaurant_y "
                               "customer_x customer_y: ")
        coords = im.parse_coordinates(text)
        result = om.place_order(coords)
        dm.show_assignment(result)
    elif cmd == "status":
        dm.show_status()
    elif cmd == "orders":
        dm.show_orders()
        stats = om.statistics()
        print(f"Completed: {stats['completed']}  "
              f"Avg time: {stats['avg_time']}  "
              f"Avg efficiency: {stats['avg_efficiency']}")
    elif cmd == "riders":
        dm.show_rider_logs()
    elif cmd == "map":
        dm.show_map()
    elif cmd == "tick":
        n = im.parse_tick_count(args)
        sysm.tick(n)
        print(f"Advanced {n} tick(s); time is now {sysm.time}.")
        return False
    elif cmd == "save":
        print(f"State saved to {sysm.save_state()}")
    elif cmd == "history":
        for i, h in enumerate(im.history, 1):
            print(f"{i:>3}  {h}")
    elif cmd == "help":
        print(HELP)
    elif cmd in ("quit", "exit"):
        sysm.stop()
        return False
    return True


def main(argv=None):
    """Run the interactive main loop."""
    argv = sys.argv[1:] if argv is None else argv
    level = logging.DEBUG if "--debug" in argv else logging.WARNING
    logging.basicConfig(level=level,
                        format="%(levelname)s %(name)s: %(message)s")
    sysm = SystemManager()
    om = OrderManager()
    dm = DisplayManager()
    im = InputManager()
    print("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)")
    print("Type 'help' for commands.")
    while globalvar.get_value("running", False):
        try:
            line = im.read(f"[t={sysm.time}] dispatch> ")
        except (EOFError, KeyboardInterrupt):
            print()
            sysm.stop()
            break
        try:
            cmd, args = im.parse(line)
        except ValueError as exc:
            print(f"Error: {exc}")
            continue
        if cmd is None:
            sysm.tick()
            continue
        try:
            if handle(cmd, args, sysm, om, dm, im):
                sysm.tick()
        except (EOFError, KeyboardInterrupt):
            print()
            sysm.stop()
        except ValueError as exc:
            print(f"Error: {exc}")
        except Exception as exc:  # recovery
            logging.exception("Unexpected error")
            print(f"Unexpected error: {exc}. Recovering...")
            for fix in sysm.check_consistency():
                print(f"  fixed: {fix}")
    try:
        sysm.save_state()
    except OSError as exc:
        print(f"Could not save state: {exc}")
    print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
