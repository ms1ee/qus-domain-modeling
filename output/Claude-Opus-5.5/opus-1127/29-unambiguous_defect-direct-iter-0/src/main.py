"""Command-line entry point of the food delivery dispatch simulator."""

import argparse
import logging
import sys

import globalvar
from system import init_system
from order import OrderManager
from display import DisplayManager
from input_manager import InputManager, HELP_TEXT

logger = logging.getLogger("dispatch")

NO_TICK_COMMANDS = {"help", "history", "quit", "", "tick"}


def setup_logging(debug=False, log_file=None):
    """Configure logging output."""
    level = logging.DEBUG if debug else logging.WARNING
    kwargs = {"level": level,
              "format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}
    if log_file:
        kwargs["filename"] = log_file
    logging.basicConfig(**kwargs)


def handle_command(cmd, args, system, orders, display, inputs):
    """Execute one command. Returns text to print."""
    if cmd == "start":
        if not args:
            args = [inputs.read_line(
                "Enter restaurant_x restaurant_y customer_x customer_y: ")]
        coords, err = inputs.validate_coordinates(args)
        if err:
            return "Error: " + err
        result = orders.create_order(coords)
        return display.format_start_result(result, system)
    if cmd == "status":
        return display.format_status(system, len(orders.pending))
    if cmd == "orders":
        return display.format_orders(orders.orders)
    if cmd == "riders":
        return display.format_rider_logs(system.riders)
    if cmd == "map":
        return display.render_map(system.riders, orders.orders)
    if cmd == "tick":
        n, err = inputs.parse_tick_count(args)
        if err:
            return "Error: " + err
        for _ in range(n):
            system.advance_tick()
            orders.process_pending()
        return "Advanced %d tick(s); now tick %d." % (n, system.time)
    if cmd == "history":
        return "\n".join("%3d  %s" % (i + 1, h)
                         for i, h in enumerate(inputs.history)) or "(empty)"
    if cmd == "help":
        return HELP_TEXT
    if cmd == "quit":
        globalvar.set_value("running", False)
        path = system.save_state()
        return "Goodbye." + (" State saved to %s." % path if path else "")
    if cmd == "":
        return ""
    return "Unknown command '%s'. Type 'help' for commands." % cmd


def main(argv=None):
    """Run the interactive main loop. Each iteration is one tick."""
    parser = argparse.ArgumentParser(description="Food delivery dispatch")
    parser.add_argument("--debug", action="store_true", help="debug logging")
    parser.add_argument("--log", help="log file path")
    opts = parser.parse_args(argv)
    setup_logging(opts.debug, opts.log)

    globalvar._init()
    system = init_system()
    orders = OrderManager(system)
    display = DisplayManager()
    inputs = InputManager()
    print("Food Delivery Dispatch Simulator - type 'help' for commands.")
    while globalvar.get_value("running"):
        try:
            line = inputs.read_command()
        except (EOFError, KeyboardInterrupt):
            print()
            line = "quit"
        except ValueError as exc:
            print("Error: %s" % exc)
            continue
        cmd, args = inputs.parse_command(line)
        try:
            output = handle_command(cmd, args, system, orders, display,
                                    inputs)
        except (EOFError, KeyboardInterrupt):
            output = "Input cancelled."
        except Exception as exc:  # graceful recovery
            logger.exception("Command failed")
            output = "Error: %s (state recovered)" % exc
            system.check_consistency()
        if output:
            print(output)
        if cmd not in NO_TICK_COMMANDS and globalvar.get_value("running"):
            try:
                system.advance_tick()
                orders.process_pending()
            except Exception:
                logger.exception("Tick failed")
                system.check_consistency()
    return 0


if __name__ == "__main__":
    sys.exit(main())
