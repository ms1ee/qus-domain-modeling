"""Command-line entry point."""
from src import globalvar
from src.display import DisplayManager
from src.input_manager import InputManager, InputError
from src.order import OrderManager
from src.path_planner import PathPlanner
from src.system import SystemManager


def handle_start(args, im, om, sm, dm):
    """Process a start command."""
    coords = im.parse_coords(args if args else input(
        "Enter rx ry cx cy: ").split())
    order = om.create_order(coords)
    added = sm.recruit_if_possible()
    rider = om.assign(order)
    if rider is None:
        return "No rider available (funds %d)." % globalvar.get_value("funds")
    route = PathPlanner.full_route(
        [(rider.x, rider.y), order.res_pos, order.cus_pos])
    total = sum(PathPlanner.distance(a, b) for a, b in zip(route, route[1:]))
    ticks = -(-total // rider.speed)
    return "\n".join([
        "Restaurant grid: (%d,%d)  Customer grid: (%d,%d)" % (
            order.res_pos[0] // 100, order.res_pos[1] // 100,
            order.cus_pos[0] // 100, order.cus_pos[1] // 100),
        "New rider added: %s" % ("yes" if added else "no"),
        "Assigned rider %d, speed %d, estimated time %d ticks" % (
            rider.rider_id, rider.speed, ticks),
        dm.render_map(route=route, orders=[order])])


def main():
    """Run the interactive loop."""
    sm = SystemManager()
    sm.recruit_if_possible()
    im, om, dm = InputManager(), OrderManager(), DisplayManager()
    print("Commands: start, status, orders, riders, tick [n], history, quit")
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        try:
            cmd, args = im.parse_command(line)
            if cmd is None:
                continue
            if cmd == "start":
                print(handle_start(args, im, om, sm, dm))
            elif cmd == "status":
                print(dm.status())
            elif cmd == "orders":
                print(dm.orders())
            elif cmd == "riders":
                print(dm.riders_log())
            elif cmd == "history":
                print("\n".join(im.history))
            elif cmd == "tick":
                n = int(args[0]) if args else 1
                for _ in range(max(0, n)):
                    sm.tick()
                continue
            elif cmd == "quit":
                globalvar.set_value("running", False)
                continue
            else:
                print("Unknown command: %s" % cmd)
            sm.tick()
        except (InputError, ValueError) as e:
            print("Error: %s" % e)
    try:
        sm.save()
    except OSError:
        pass


if __name__ == "__main__":
    main()
