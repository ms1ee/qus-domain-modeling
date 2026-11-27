"""Entry point."""
import globalvar
import system
from display import DisplayManager
from inputmanager import InputManager
from order import assign_order
from order_model import Order


def main():
    """Run the command loop; each iteration is one tick."""
    system.init_system()
    disp = DisplayManager()
    inp = InputManager()
    print("Commands: start rx ry cx cy | status | orders | riders | quit")
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except EOFError:
            break
        try:
            cmd, args = inp.parse_command(line)
            if cmd is None:
                continue
            if cmd == "start":
                v = inp.parse_coords(args)
                o = Order((v[0], v[1]), (v[2], v[3]))
                rider, added = assign_order(o)
                if rider is None:
                    print("No rider available (insufficient funds).")
                else:
                    print("Restaurant %s Customer %s New rider: %s" % (
                        o.res_pos, o.cus_pos, added))
                    print(disp.route(rider, o))
            elif cmd == "status":
                print(disp.status())
            elif cmd == "orders":
                print(disp.orders())
            elif cmd == "riders":
                print(disp.riders_log())
            elif cmd == "quit":
                globalvar.set_value("running", False)
            else:
                print("Unknown command.")
        except ValueError as e:
            print("Error:", e)
        except Exception as e:  # recover
            print("Unexpected error:", e)
        system.tick()
    system.save_state()


if __name__ == "__main__":
    main()
