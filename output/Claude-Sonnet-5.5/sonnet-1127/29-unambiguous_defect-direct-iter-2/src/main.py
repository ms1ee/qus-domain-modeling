"""Entry point: python src/main.py"""
import globalvar
import system
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager


def main():
    """Run the command loop."""
    system.init_system()
    history = []
    print("Commands: start(s) status(st) orders(o) riders(r) tick(t) "
          "history(h) quit(q)")
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        cmd = InputManager.command(line)
        if cmd:
            history.append(cmd)
        try:
            if cmd == "start":
                coords = InputManager.parse_coords(
                    input("Enter res_x res_y cus_x cus_y: "))
                order, rider, added = OrderManager.create(coords)
                if rider is None:
                    print("No rider available (insufficient funds).")
                else:
                    print("Restaurant:", order.res_pos, "Customer:",
                          order.cus_pos, "New rider added:", added)
                    print(DisplayManager.route_text(order, rider))
            elif cmd == "status":
                print(DisplayManager.status_text())
                print(DisplayManager.map_text())
            elif cmd == "orders":
                print(DisplayManager.orders_text())
            elif cmd == "riders":
                print(DisplayManager.riders_text())
            elif cmd == "tick":
                system.tick()
                continue
            elif cmd == "history":
                print("\n".join(history))
            elif cmd == "quit":
                globalvar.set_value("running", False)
            elif cmd:
                print("Unknown command.")
        except ValueError as e:
            print("Error:", e)
        except Exception as e:  # recover gracefully
            print("Unexpected error:", e)
        if globalvar.get_value("running"):
            system.tick()
    try:
        system.SystemManager.save()
    except OSError:
        pass


if __name__ == "__main__":
    main()
