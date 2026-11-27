"""Command-line entry point."""
import globalvar
from system import init_system
from order import create_order, assign_order


def render_map(rider, order):
    """ASCII 16x16 map with the route."""
    g = [['#' if (i % 2 == 0 or j % 2 == 0) else '.' for j in range(16)]
         for i in range(16)]

    def cell(p):
        return min(15, p[1] // 50), min(15, p[0] // 50)
    r, c = cell(order.res_pos)
    g[r][c] = 'S'
    r, c = cell(order.cus_pos)
    g[r][c] = 'C'
    r, c = cell((rider.x, rider.y))
    g[r][c] = 'R'
    return "\n".join("".join(row) for row in g)


def tick():
    globalvar.set_value("tick", globalvar.get_value("tick") + 1)
    for r in globalvar.get_value("riders"):
        r.move()


def cmd_start():
    try:
        vals = [int(v) for v in input("rx ry cx cy: ").split()]
    except ValueError:
        print("Error: integers required")
        return
    if len(vals) != 4 or any(v < 0 or v > 1000 for v in vals):
        print("Error: need 4 integers in 0-1000")
        return
    order = create_order(*vals)
    rider, new = assign_order(order)
    print("Restaurant:", order.res_pos, "Customer:", order.cus_pos)
    print("New rider added:", new is not None)
    if rider:
        print("Rider", rider.rider_id, "speed", rider.speed,
              "est. time", (abs(rider.x - order.res_pos[0])
                            + abs(rider.y - order.res_pos[1])
                            + order.distance) / rider.speed)
        print(render_map(rider, order))


def main():
    init_system()
    names = {0: "idle", 1: "picking up", 2: "delivering"}
    while globalvar.get_value("running"):
        try:
            cmd = input("> ").strip().lower()
        except EOFError:
            break
        if cmd in ("quit", "exit", "q"):
            globalvar.set_value("running", False)
            continue
        if cmd in ("start", "s"):
            cmd_start()
        elif cmd == "status":
            print("Funds:", globalvar.get_value("funds"))
            for r in globalvar.get_value("riders"):
                print(r.rider_id, (r.x, r.y), names[r.state],
                      [o.id for o in r.orders])
        elif cmd == "orders":
            for o in globalvar.get_value("orders"):
                print(o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
                      o.time_taken, o.rider_id, o.status)
        elif cmd == "riders":
            for r in globalvar.get_value("riders"):
                for e in r.log:
                    print(r.rider_id, e)
        elif cmd:
            print("Unknown command")
        tick()


if __name__ == "__main__":
    main()
