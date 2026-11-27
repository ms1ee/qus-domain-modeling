"""Command-line entry point."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import globalvar  # noqa: E402
from system import SystemManager  # noqa: E402
from display import DisplayManager  # noqa: E402
from input_manager import InputManager  # noqa: E402


def main():
    system = SystemManager()
    display = DisplayManager()
    inp = InputManager()
    print("Food Delivery Dispatch. Commands: start, status, orders, riders, quit")
    while globalvar.get_value("running"):
        try:
            cmd = inp.parse_command(input("> "))
        except (EOFError, KeyboardInterrupt):
            break
        try:
            if cmd == "quit":
                globalvar.set_value("running", False)
                break
            elif cmd == "start":
                c = inp.parse_coordinates(input("restaurant_x restaurant_y customer_x customer_y: "))
                o, rider, hired = system.create_order((c[0], c[1]), (c[2], c[3]))
                print("Restaurant grid: %s, Customer grid: %s" % (o.res_pos, o.cus_pos))
                print("New rider added: %s" % hired)
                if rider:
                    print(display.route_text(rider, o))
                else:
                    print("No rider available; order pending.")
            elif cmd == "status":
                print(display.status_text(system))
            elif cmd == "orders":
                print(display.orders_text(system))
            elif cmd == "riders":
                print(display.riders_text(system))
            else:
                print("Unknown command.")
        except ValueError as e:
            print("Error: %s" % e)
        except Exception as e:  # recover gracefully
            print("Unexpected error: %s" % e)
        system.step()
    try:
        system.save()
    except OSError:
        pass


if __name__ == "__main__":
    main()
