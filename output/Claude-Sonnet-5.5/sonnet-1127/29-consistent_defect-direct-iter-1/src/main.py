"""Command-line entry point."""
from src import globalvar, system
from src.order_model import Order
from src.order import find_best_rider_for_order
from src.rider import Rider


def recruit_if_needed():
    """Hire a rider when funds and demand allow. Returns True if hired."""
    riders = globalvar.get_value("riders")
    pending = sum(1 for o in globalvar.get_value("orders")
                  if o.status == "pending")
    idle = sum(1 for r in riders if r.state == 0 and not r.orders)
    funds = globalvar.get_value("funds")
    if funds >= 300 and pending > idle:
        rid = globalvar.get_value("rider_id_counter") + 1
        globalvar.set_value("rider_id_counter", rid)
        riders.append(Rider(rid))
        globalvar.set_value("funds", funds - 500)
        return True
    return False


def tick():
    """Advance simulation by one tick."""
    globalvar.set_value("time", globalvar.get_value("time") + 1)
    for r in globalvar.get_value("riders"):
        r.move()


def cmd_start(args):
    """Create an order from four integers."""
    try:
        v = [int(a) for a in args]
    except ValueError:
        print("Coordinates must be integers.")
        return
    if len(v) != 4 or any(not 0 <= n <= 1000 for n in v):
        print("Usage: start rx ry cx cy (0-1000)")
        return
    order = Order((v[0], v[1]), (v[2], v[3]))
    globalvar.get_value("orders").append(order)
    hired = recruit_if_needed()
    rider = find_best_rider_for_order(order)
    if rider is None:
        print("No rider available.")
        return
    rider.orders.append(order)
    order.assign_to(rider.rider_id)
    print("Order %d: restaurant %s customer %s" % (
        order.id, order.res_pos, order.cus_pos))
    print("New rider added:", hired)
    print("Assigned rider %d speed %d" % (rider.rider_id, rider.speed))
    print("Estimated ticks:", -(-(abs(rider.x - order.res_pos[0])
          + abs(rider.y - order.res_pos[1]) + order.distance) // rider.speed))


def cmd_status():
    """Print system status."""
    print("Funds:", globalvar.get_value("funds"),
          "Time:", globalvar.get_value("time"))
    names = {0: "idle", 1: "picking up", 2: "delivering"}
    for r in globalvar.get_value("riders"):
        print("Rider %d at (%d,%d) %s orders=%s" % (
            r.rider_id, r.x, r.y, names[r.state], [o.id for o in r.orders]))
    grid = [["." for _ in range(16)] for _ in range(16)]
    for r in globalvar.get_value("riders"):
        grid[min(15, r.y // 50)][min(15, r.x // 50)] = "R"
    for row in grid:
        print("".join(row))


def cmd_orders():
    """Print orders."""
    for o in globalvar.get_value("orders"):
        taken = (o.end_time - o.start_time) if o.end_time is not None else "-"
        print("Order %d start=%d from=%s to=%s dist=%d time=%s rider=%s %s" % (
            o.id, o.start_time, o.res_pos, o.cus_pos, o.distance, taken,
            o.rider_id, o.status))


def cmd_riders():
    """Print rider logs."""
    for r in globalvar.get_value("riders"):
        for e in r.log:
            print("Rider %d t=%d %s pos=%s order=%s" % (
                r.rider_id, e["time"], e["event"], e["pos"], e["order_id"]))


def main():
    """Run the command loop; each command is one tick."""
    system.init_system()
    while globalvar.get_value("running"):
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        parts = line.split()
        if not parts:
            tick()
            continue
        c = parts[0].lower()
        if c == "start":
            cmd_start(parts[1:])
        elif c == "status":
            cmd_status()
        elif c == "orders":
            cmd_orders()
        elif c == "riders":
            cmd_riders()
        elif c in ("quit", "exit"):
            globalvar.set_value("running", False)
            continue
        else:
            print("Unknown command.")
        tick()


if __name__ == "__main__":
    main()
