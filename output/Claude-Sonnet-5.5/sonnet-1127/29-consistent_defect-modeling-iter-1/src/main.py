"""Command-line entry point."""
import globalvar
from system import SystemManager

try:
    import readline  # noqa: F401  (command history)
except ImportError:
    pass


def main():
    sm = SystemManager()
    print("Food Delivery Dispatch. Commands: start, status, orders, riders,"
          " map, tick [n], run, quit")
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        try:
            cmd, args = sm.input.parse_command(line)
            if cmd is None:
                if line.strip():
                    print("Unknown command. Type 'help'.")
            elif cmd == "start":
                text = " ".join(args) or input(
                    "Enter rx ry cx cy: ")
                print(sm.start_order(sm.input.parse_coords(text)))
            elif cmd == "status":
                print(sm.display.status())
            elif cmd == "orders":
                print(sm.display.orders())
            elif cmd == "riders":
                print(sm.display.riders_log())
            elif cmd == "map":
                print(sm.display.render_map())
            elif cmd == "tick":
                n = int(args[0]) if args else 1
                for _ in range(max(n, 0)):
                    sm.tick()
                print(sm.display.status())
            elif cmd == "run":
                guard = 0
                while sm.busy() and guard < 10000:
                    sm.tick()
                    guard += 1
                print(sm.display.status())
            elif cmd == "help":
                print("start [rx ry cx cy], status, orders, riders, map,"
                      " tick [n], run, quit")
            elif cmd == "quit":
                globalvar.set_value("running", False)
        except ValueError as e:
            print("Error:", e)
        except Exception as e:  # recover gracefully
            print("Unexpected error:", e)
    try:
        sm.save()
    except OSError:
        pass


if __name__ == "__main__":
    main()
