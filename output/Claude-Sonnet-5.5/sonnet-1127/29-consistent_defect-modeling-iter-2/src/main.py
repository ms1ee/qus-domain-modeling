"""Command line entry point."""

import globalvar
from system import SystemManager
from display import DisplayManager
from inputmanager import InputManager


def main():
    sysm = SystemManager()
    disp = DisplayManager()
    inp = InputManager()
    print("Commands: start, status, orders, riders, quit")
    while globalvar.get_value("running"):
        try:
            cmd = inp.parse_command(input("> "))
        except (EOFError, KeyboardInterrupt):
            break
        try:
            if cmd == "quit":
                break
            elif cmd == "start":
                vals = inp.parse_coordinates(
                    input("rx ry cx cy: "))
                order, rider, new = sysm.submit_order(*vals)
                print("Restaurant:", order.res_pos, "Customer:", order.cus_pos)
                print("New rider added:", bool(new))
                if rider:
                    print(disp.show_route(rider, order))
            elif cmd == "status":
                print(disp.show_status())
            elif cmd == "orders":
                print(disp.show_orders())
            elif cmd == "riders":
                print(disp.show_riders())
            else:
                print("Unknown command")
        except ValueError as e:
            print("Error:", e)
        except Exception as e:  # recover gracefully
            print("Unexpected error:", e)
        sysm.tick()
    try:
        sysm.save()
    except OSError:
        pass


if __name__ == "__main__":
    main()
