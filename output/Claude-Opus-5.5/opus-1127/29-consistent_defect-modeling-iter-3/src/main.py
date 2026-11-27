"""Command-line entry point for the food delivery dispatch simulator."""

import argparse
import logging
import sys

import system
from display import DisplayManager
from input_manager import InputManager

try:  # command history / line editing where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

HELP = """Commands (shortcut in brackets):
  start [rx ry cx cy] (n)  create an order and assign it
  status (s)               funds and riders snapshot
  orders (o)               all order details
  riders (r)               rider status-change history
  map (m)                  ASCII map
  tick [N] (t)             advance N ticks (default 1)
  run                      advance until all assigned orders are delivered
  save [file] / load [file] persist / restore state (JSON)
  history                  show command history (!! repeats, !N runs entry N)
  help (h)                 this help
  quit / exit (q)          leave"""


def handle(cmd, args, mgr, display, inp, read=input):
    """Execute one command. Returns output text."""
    if cmd == "help":
        return HELP
    if cmd in ("quit", "exit"):
        mgr.running = False
        return "Bye."
    if cmd == "status":
        return display.format_status(mgr)
    if cmd == "orders":
        return display.format_orders(mgr.orders)
    if cmd == "riders":
        return display.format_rider_logs(mgr.riders)
    if cmd == "map":
        return display.render_map(mgr.riders, mgr.orders,
                                  [r.planned_route() for r in mgr.riders])
    if cmd == "history":
        return "\n".join("%d: %s" % (i + 1, c)
                         for i, c in enumerate(inp.command_history))
    if cmd == "tick":
        n = int(args[0]) if args else 1
        if n < 0 or n > 100000:
            raise ValueError("tick count must be between 0 and 100000")
        mgr.advance(n)
        return "Advanced to tick %d." % mgr.current_tick
    if cmd == "run":
        steps = 0
        while not mgr.all_delivered() and steps < 100000:
            mgr.advance(1)
            steps += 1
        return "Ran %d ticks; now tick %d." % (steps, mgr.current_tick)
    if cmd == "save":
        return "Saved to %s" % mgr.save_state(args[0] if args else None)
    if cmd == "load":
        return "Loaded from %s" % mgr.load_state(args[0] if args else None)
    if cmd == "start":
        text = " ".join(args) if args else read(
            "Enter restaurant_x restaurant_y customer_x customer_y: ")
        rx, ry, cx, cy = inp.parse_coordinates(text)
        res = mgr.order_manager.create_order(rx, ry, cx, cy)
        order, rider = res["order"], res["rider"]
        out = ["Order #%d: restaurant grid %s, customer grid %s" % (
            order.id, tuple(order.res_pos), tuple(order.cus_pos))]
        if res["recruited"] is not None:
            out.append("New rider added: Rider %d (funds now %d)" % (
                res["recruited"].rider_id, mgr.funds))
        else:
            out.append("No new rider added (funds %d)" % mgr.funds)
        if rider is None:
            out.append("No rider available; order remains pending.")
        else:
            route = res["route"]
            out.append(display.format_route_info(rider, route))
            out.append(display.render_map([rider], rider.active_orders, [route]))
        return "\n".join(out)
    return ""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", help="JSON configuration file")
    parser.add_argument("--debug", action="store_true", help="debug logging")
    opts = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if opts.debug else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    mgr = system.init_system(opts.config)
    display = DisplayManager()
    inp = InputManager(0, mgr.config.get("map_size"))
    print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
    while mgr.running:
        try:
            line = input("[t=%d] > " % mgr.current_tick)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        try:
            cmd, args = inp.parse_command(line)
            if cmd:
                out = handle(cmd, args, mgr, display, inp)
                if out:
                    print(out)
        except ValueError as exc:
            print("Error: %s" % exc)
        except Exception as exc:  # recovery
            logging.exception("Unexpected error")
            print("Unexpected error: %s. Recovering..." % exc)
            fixes = mgr.check_consistency()
            if fixes:
                print("Repaired: " + "; ".join(fixes))
        if mgr.running:
            mgr.advance(1)  # each loop iteration is one tick
    return 0


if __name__ == "__main__":
    sys.exit(main())
