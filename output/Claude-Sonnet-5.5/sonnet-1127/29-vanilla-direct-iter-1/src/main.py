"""Command-line entry point."""
import globalvar
import system
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from path_planner import PathPlanner

HELP = ("Commands: start, status(s), orders(o), riders(r), tick [n](t), "
        "help(h), quit/exit(q)")


def handle_start(im):
    try:
        coords = im.parse_coords(input("Enter rx ry cx cy: "))
    except ValueError as e:
        print("Error:", e)
        return
    order, rider, recruited = OrderManager.create_order(coords)
    print("Restaurant grid:", (order.res_pos[0] // 100, order.res_pos[1] // 100))
    print("Customer grid:", (order.cus_pos[0] // 100, order.cus_pos[1] // 100))
    print("New rider added:", recruited)
    if rider is None:
        print("No rider available; order pending.")
        return
    pts = [(rider.x, rider.y), order.res_pos, order.cus_pos]
    total = (abs(rider.x - pts[1][0]) + abs(rider.y - pts[1][1])
             + order.distance)
    print("Rider %d speed %d, estimated time %d ticks" % (
        rider.rider_id, rider.speed, -(-total // rider.speed)))
    print(DisplayManager.map_text(pts))


def main():
    system.init_system()
    im = InputManager()
    print(HELP)
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        cmd, args = im.parse_command(line)
        try:
            if cmd == "start":
                handle_start(im)
            elif cmd == "status":
                print(DisplayManager.status_text())
                print(DisplayManager.map_text())
            elif cmd == "orders":
                print(DisplayManager.orders_text())
            elif cmd == "riders":
                print(DisplayManager.riders_text())
            elif cmd == "tick":
                n = int(args[0]) if args else 1
                for _ in range(max(n, 0)):
                    system.tick()
                print("Time:", globalvar.get_value("time"))
            elif cmd == "help":
                print(HELP)
            elif cmd == "quit":
                globalvar.set_value("running", False)
                continue
            elif cmd:
                print("Unknown command. " + HELP)
                continue
            else:
                continue
        except ValueError:
            print("Error: invalid argument.")
            continue
        if cmd in ("start",):
            system.tick()
    try:
        system.save_state()
    except OSError:
        pass


if __name__ == "__main__":
    main()
