"""Command-line entry point."""
import globalvar
import system
from system import SystemManager
from order import OrderManager
from display import DisplayManager
from input_manager import InputManager


def main():
    globalvar._init()
    system.init_system()
    history = []
    print("Commands: start(s), status(st), orders(o), riders(r), quit(q)")
    while globalvar.get_value("running"):
        try:
            cmd = InputManager.parse_command(input("> "))
        except (EOFError, KeyboardInterrupt):
            break
        history.append(cmd)
        try:
            if cmd == "start":
                coords = InputManager.parse_coords(
                    input("Enter rx ry cx cy: "))
                order, rider, added = OrderManager.create_order(coords)
                if rider is None:
                    print("No rider available.")
                else:
                    print("Restaurant %s, customer %s, new rider added: %s"
                          % (order.res_pos, order.cus_pos, added))
                    print(DisplayManager.route(order, rider))
            elif cmd == "status":
                print(DisplayManager.status())
            elif cmd == "orders":
                print(DisplayManager.orders())
            elif cmd == "riders":
                print(DisplayManager.riders())
            elif cmd == "quit":
                globalvar.set_value("running", False)
            elif cmd:
                print("Unknown command.")
        except ValueError as e:
            print("Error:", e)
        except Exception as e:  # recover gracefully
            print("Unexpected error:", e)
        SystemManager.tick()
    try:
        SystemManager.save()
    except OSError:
        pass


if __name__ == "__main__":
    main()
