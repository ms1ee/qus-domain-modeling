"""Entry point of the Food Delivery Order Dispatch System simulator."""

import logging
import sys

import globalvar
from display import DisplayManager
from input_manager import InputManager
from system import init_system

try:  # command history / line editing where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None


def main(argv=None):
    """Run the interactive main loop. Each iteration is one simulation tick."""
    argv = sys.argv[1:] if argv is None else argv
    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    config_path = argv[0] if argv else "config.json"
    system = init_system(config_path)
    display = DisplayManager()
    im = InputManager(system, display)
    print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
    while globalvar.get_value("running", False):
        try:
            line = input("[t=%d] > " % system.tick)
        except (EOFError, KeyboardInterrupt):
            print()
            system.stop()
            break
        out = im.handle(line)
        if out:
            print(out)
        if system.running:
            system.advance(1)
    if system.config.get("autosave"):
        try:
            print("State saved to %s" % system.save_state())
        except OSError as exc:
            print("Could not save state: %s" % exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
