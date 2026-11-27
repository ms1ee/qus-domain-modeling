"""Command-line entry point."""
import globalvar
from system import init_system, SystemManager
from order import OrderManager
from display import DisplayManager
from input_manager import InputManager, InputError
from path_planner import PathPlanner


def handle_start(args):
    coords = InputManager.parse_coords(args)
    order, added, rider = OrderManager.create_order(coords)
    out = ["Restaurant grid: (%d,%d)  Customer grid: (%d,%d)" % (
        order.res_pos[0] // 100, order.res_pos[1] // 100,
        order.cus_pos[0] // 100, order.cus_pos[1] // 100),
        "New rider added: %s" % ("yes" if added else "no")]
    if rider is None:
        out.append("No rider available.")
    else:
        route = PathPlanner.plan_multi((rider.x, rider.y),
                                       [order.res_pos, order.cus_pos])
        dist = sum(PathPlanner.distance(a, b)
                   for a, b in zip(route, route[1:]))
        out.append("Rider %d speed %d, estimated time %d ticks" % (
            rider.rider_id, rider.speed, -(-dist // rider.speed)))
        out.append(DisplayManager.render_map([rider], [order], route))
    return "\n".join(out)


def main():
    init_system()
    im = InputManager()
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except EOFError:
            break
        try:
            cmd, args = im.parse(line)
            if cmd == "quit":
                globalvar.set_value("running", False)
                continue
            if cmd == "start":
                print(handle_start(args))
            elif cmd == "status":
                print(DisplayManager.status())
            elif cmd == "orders":
                print(DisplayManager.orders())
            elif cmd == "riders":
                print(DisplayManager.riders_log())
            elif cmd == "history":
                print("\n".join(im.history))
            elif cmd == "tick":
                n = int(args[0]) if args and args[0].isdigit() else 1
                for _ in range(n):
                    SystemManager.tick()
                print("Time: %s" % globalvar.get_value("time"))
                continue
        except InputError as e:
            print("Error: %s" % e)
        except Exception as e:  # recovery
            print("Unexpected error: %s" % e)
        SystemManager.tick()
    try:
        SystemManager.save()
    except OSError:
        pass


if __name__ == "__main__":
    main()
