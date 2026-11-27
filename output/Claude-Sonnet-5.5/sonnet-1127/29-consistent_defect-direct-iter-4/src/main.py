"""Command-line entry point."""
import globalvar
from system import SystemManager
from order import OrderManager
from display import DisplayManager
from input_manager import InputManager
from path_planner import PathPlanner


def main():
    sysm = SystemManager()
    om, dm, im = OrderManager(), DisplayManager(), InputManager()
    print("Commands: start, status, orders, riders, tick, quit")
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        try:
            cmd, args = im.parse(line)
            if cmd == "start":
                text = " ".join(args) or input("res_x res_y cus_x cus_y: ")
                o, rider, rec = om.create_order(*im.parse_coords(text))
                print("Restaurant:", o.res_pos, "Customer:", o.cus_pos)
                print("New rider added:", rec)
                if rider:
                    path = PathPlanner.plan_multi(
                        [(rider.x, rider.y), o.res_pos, o.cus_pos])
                    dist = PathPlanner.length(path)
                    print("Rider %d speed %d, est. time %d ticks" % (
                        rider.rider_id, rider.speed,
                        -(-dist // rider.speed)))
                    print(dm.map(path))
                else:
                    print("No rider available.")
            elif cmd == "status":
                print(dm.status())
                print(dm.map())
            elif cmd == "orders":
                print(dm.orders())
            elif cmd == "riders":
                print(dm.riders_log())
            elif cmd == "tick":
                n = int(args[0]) if args else 1
                for _ in range(n):
                    sysm.tick()
                continue
            elif cmd == "quit":
                globalvar.set_value("running", False)
                sysm.save()
                break
            else:
                print("Unknown command.")
                continue
            sysm.tick()
        except ValueError as e:
            print("Error:", e)
        except Exception as e:  # recover gracefully
            print("Unexpected error:", e)


if __name__ == "__main__":
    main()
