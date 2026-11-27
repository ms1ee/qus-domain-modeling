"""Command-line entry point."""
from . import globalvar
from .system import SystemManager, init_system
from .order import OrderManager
from .display import DisplayManager
from .input_manager import InputManager


def main():
    init_system()
    disp = DisplayManager()
    inp = InputManager()
    print("Commands: start rx ry cx cy | status | orders | riders | "
          "tick [n] | quit")
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        try:
            cmd, args = inp.parse_command(line)
            if cmd is None:
                continue
            if cmd == "quit":
                break
            elif cmd == "start":
                if not args:
                    args = input("rx ry cx cy: ").split()
                v = inp.parse_coords(args)
                order, rider, added = OrderManager.create(v[:2], v[2:])
                print("Restaurant cell: (%d,%d) Customer cell: (%d,%d)" % (
                    order.res_pos[0] // 100, order.res_pos[1] // 100,
                    order.cus_pos[0] // 100, order.cus_pos[1] // 100))
                print("New rider added: %s" % added)
                if rider is None:
                    print("No rider available (insufficient funds).")
                else:
                    cells = (disp.route_cells(rider.pos, order.res_pos) +
                             disp.route_cells(order.res_pos, order.cus_pos))
                    total = 0
                    prev = rider.pos
                    for p in (order.res_pos, order.cus_pos):
                        total += abs(p[0] - prev[0]) + abs(p[1] - prev[1])
                        prev = p
                    print("Rider %d speed %d, estimated time %d ticks" % (
                        rider.rider_id, rider.speed,
                        -(-total // rider.speed)))
                    print(disp.render_map(route=cells,
                                          orders=[order], riders=[rider]))
                SystemManager.tick()
            elif cmd == "status":
                print(disp.status())
            elif cmd == "orders":
                print(disp.orders())
            elif cmd == "riders":
                print(disp.riders())
            elif cmd == "tick":
                n = int(args[0]) if args else 1
                for _ in range(n):
                    SystemManager.tick()
                print("Time: %d" % globalvar.get_value("time"))
            else:
                print("Unknown command: %s" % cmd)
        except ValueError as e:
            print("Error: %s" % e)
        except Exception as e:  # recover gracefully
            print("Unexpected error: %s" % e)
    globalvar.set_value("running", False)
    try:
        SystemManager.save()
    except OSError:
        pass


if __name__ == "__main__":
    main()
