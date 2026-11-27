"""Command-line entry point."""

import system
import globalvar
import order as order_mod
from display import DisplayManager
from input_manager import InputManager, InputError, parse_coords
from path_planner import PathPlanner


def handle_start(arg):
    """Create and dispatch an order."""
    coords = parse_coords(arg)
    o = order_mod.create_order(coords)
    new_rider = system.maybe_recruit(1)
    rider = order_mod.assign_order(o)
    if rider is None:
        return "No riders available."
    route = [(rider.x, rider.y), o.res_pos, o.cus_pos]
    length = PathPlanner.path_length(route)
    eta = -(-length // rider.speed)
    return "\n".join([
        "Order %d: restaurant grid %s, customer grid %s" % (
            o.id, (o.res_pos[0] // 100, o.res_pos[1] // 100),
            (o.cus_pos[0] // 100, o.cus_pos[1] // 100)),
        "New rider added: %s" % ("yes" if new_rider else "no"),
        "Assigned rider %d, speed %d, est. time %d ticks" % (
            rider.rider_id, rider.speed, eta),
        DisplayManager.map(route)])


def main():
    """Run the simulator."""
    system.init_system()
    im = InputManager()
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except EOFError:
            break
        try:
            cmd, arg = im.parse(line)
            ticks = 1
            if cmd == "start":
                print(handle_start(arg))
            elif cmd == "status":
                print(DisplayManager.status())
                print(DisplayManager.map())
            elif cmd == "orders":
                print(DisplayManager.orders())
            elif cmd == "riders":
                print(DisplayManager.riders_log())
            elif cmd == "tick":
                ticks = int(arg) if arg.strip() else 1
            elif cmd in ("quit", "exit"):
                globalvar.set_value("running", False)
                ticks = 0
            elif cmd == "":
                ticks = 0
            else:
                print("Unknown command. Use start/status/orders/riders/quit")
                ticks = 0
            for _ in range(ticks):
                system.tick()
        except (InputError, ValueError) as e:
            print("Error: %s" % e)
        except Exception as e:  # recover gracefully
            print("Unexpected error: %s" % e)


if __name__ == "__main__":
    main()
