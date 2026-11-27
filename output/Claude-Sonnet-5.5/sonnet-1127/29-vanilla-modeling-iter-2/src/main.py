"""Command-line entry point."""
import globalvar
import system
from rider import Rider
from order_model import Order
from order import find_best_rider_for_order

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


def tick():
    globalvar.set_value("tick", globalvar.get_value("tick") + 1)
    for r in globalvar.get_value("riders"):
        r.move()


def start(args):
    if len(args) != 4:
        print("Usage: start rx ry cx cy")
        return
    try:
        v = [int(a) for a in args]
    except ValueError:
        print("Coordinates must be integers.")
        return
    if any(a < 0 or a > 800 for a in v):
        print("Coordinates must be within 0-800.")
        return
    order = Order((v[0], v[1]), (v[2], v[3]))
    riders = globalvar.get_value("riders")
    added = False
    funds = globalvar.get_value("funds")
    pending = sum(len(r.orders) for r in riders) + 1
    idle = sum(1 for r in riders if r.state == 0 and not r.orders)
    if funds >= 300 and pending > idle:
        cnt = globalvar.get_value("rider_id_counter") + 1
        globalvar.set_value("rider_id_counter", cnt)
        riders.append(Rider(cnt))
        globalvar.set_value("funds", funds - 300)
        added = True
    best = find_best_rider_for_order(order)
    if best is None:
        print("No rider available.")
        return
    best.orders.append(order)
    order.assign_to(best.rider_id)
    print("Restaurant cell:", order.res_pos, "Customer cell:", order.cus_pos)
    print("New rider added:", added, "| rider", best.rider_id)


def status():
    print("Funds:", globalvar.get_value("funds"))
    for r in globalvar.get_value("riders"):
        print("Rider %d at (%d,%d) %s orders=%s" % (
            r.rider_id, r.x, r.y, STATES[r.state],
            [o.id for o in r.orders]))


def orders():
    for o in globalvar.get_value("orders"):
        print("Order %d start=%s res=%s cus=%s dist=%.1f taken=%s rider=%s" % (
            o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
            o.time_taken, o.rider_id))


def riders_log():
    for r in globalvar.get_value("riders"):
        for e in r.log:
            print("Rider %d t=%s (%s,%s) %s order=%s" % (
                r.rider_id, e["time"], e["x"], e["y"], e["event"],
                e["order_id"]))


def main():
    system.init_system()
    history = []
    while globalvar.get_value("running"):
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            continue
        history.append(line)
        parts = line.split()
        cmd, args = parts[0].lower(), parts[1:]
        if cmd in ("quit", "exit"):
            globalvar.set_value("running", False)
        elif cmd == "start":
            start(args)
        elif cmd == "status":
            status()
        elif cmd == "orders":
            orders()
        elif cmd == "riders":
            riders_log()
        else:
            print("Unknown command.")
            continue
        if cmd in ("start", "status", "orders", "riders"):
            tick()


if __name__ == "__main__":
    main()
