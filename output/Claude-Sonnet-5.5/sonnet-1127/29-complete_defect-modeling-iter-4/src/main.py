"""Command-line entry point."""

import math

try:
    from src import globalvar
    from src.system import init_system
    from src.display import DisplayManager
    from src.input_manager import InputManager
except ImportError:  # pragma: no cover
    import globalvar
    from system import init_system
    from display import DisplayManager
    from input_manager import InputManager


def handle_start(system, display, inp, args):
    """Process the start command."""
    if not args:
        args = input("Enter rx ry cx cy: ").split()
    coords = inp.parse_coords(args)
    pre = (coords[0], coords[1])
    order, rider, new_rider = system.submit_order(coords)
    out = ["Restaurant grid: (%d,%d)  Customer grid: (%d,%d)" % (
        pre[0] // 100 if pre[0] < 800 else 7, pre[1] // 100 if pre[1] < 800 else 7,
        order.cus_pos[0] // 100, order.cus_pos[1] // 100),
        "New rider added: %s" % ("yes (#%d)" % new_rider.rider_id
                                 if new_rider else "no")]
    if rider is None:
        out.append("No rider available; order %d pending." % order.id)
        return "\n".join(out)
    route = system.planner.plan((rider.x, rider.y), order.res_pos)
    route += system.planner.plan(order.res_pos, order.cus_pos)[1:]
    dist = sum(system.planner.distance(a, b) for a, b in zip(route, route[1:]))
    out.append("Order %d assigned to rider %d, speed %d, est. time %d ticks"
               % (order.id, rider.rider_id, rider.speed,
                  math.ceil(dist / rider.speed)))
    out.append(display.render_map(globalvar.get_value("riders"), [order],
                                  route))
    return "\n".join(out)


def main():
    """Run the interactive loop."""
    system = init_system()
    display = DisplayManager()
    inp = InputManager()
    print("Food Delivery Dispatch. Commands: start, status, orders, riders, quit")
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        cmd, args = inp.parse_command(line)
        if cmd is None:
            continue
        try:
            if cmd == "start":
                print(handle_start(system, display, inp, args))
            elif cmd == "status":
                print(display.status(globalvar.get_value("riders")))
                print(display.render_map(globalvar.get_value("riders"),
                                         globalvar.get_value("orders")))
            elif cmd == "orders":
                print(display.orders(globalvar.get_value("orders")))
            elif cmd == "riders":
                print(display.riders_log(globalvar.get_value("riders")))
            elif cmd == "history":
                print("\n".join(inp.command_history))
            elif cmd == "quit":
                globalvar.set_value("running", False)
                break
            else:
                print("Unknown command.")
        except ValueError as e:
            print("Error: %s" % e)
        except Exception as e:  # recover gracefully
            print("Unexpected error: %s" % e)
        system.tick()
    try:
        system.save()
    except OSError:
        pass


if __name__ == "__main__":
    main()
