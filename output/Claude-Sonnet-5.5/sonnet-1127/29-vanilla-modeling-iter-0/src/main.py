"""Command-line entry point."""
import globalvar
import system
from order_model import Order
from order import assign_order


def main():
    system.init_system()
    while globalvar.get_value("running"):
        try:
            line = input("> ").strip().split()
        except EOFError:
            break
        if not line:
            continue
        cmd = line[0].lower()
        if cmd in ("quit", "exit"):
            globalvar.set_value("running", False)
        elif cmd == "start":
            try:
                v = [int(a) for a in line[1:]]
                if len(v) != 4 or any(not 0 <= a <= 800 for a in v):
                    raise ValueError
            except ValueError:
                print("Enter four integers in range 0-800.")
                continue
            o = Order(v[:2], v[2:], globalvar.get_value("tick", 0))
            r = assign_order(o)
            print("Order", o.id, o.res_pos, o.cus_pos,
                  "rider", r.rider_id if r else None)
        elif cmd == "status":
            print("Funds:", globalvar.get_value("funds"))
            for r in globalvar.get_value("riders"):
                print(r.rider_id, (r.x, r.y), r.state, len(r.orders))
        else:
            print("Unknown command")
            continue
        globalvar.set_value("tick", globalvar.get_value("tick", 0) + 1)
        for r in globalvar.get_value("riders"):
            r.move()


if __name__ == "__main__":
    main()
