"""Command-line entry point."""
import json
import system
import globalvar
import order as order_mod
import display


def parse_coords(text):
    """Parse four integers in 0-800."""
    parts = text.replace(",", " ").replace("[", " ").replace("]", " ").split()
    if len(parts) != 4:
        raise ValueError("Enter exactly four integers.")
    try:
        vals = [int(p) for p in parts]
    except ValueError:
        raise ValueError("Coordinates must be integers.")
    if any(v < 0 or v > 800 for v in vals):
        raise ValueError("Coordinates must be within 0-800.")
    return vals


def save(path="state.json"):
    """Persist state to JSON."""
    data = {"funds": globalvar.get_value("funds"),
            "riders": [{"id": r.rider_id, "x": r.x, "y": r.y,
                        "state": r.state} for r in globalvar.get_value("riders")],
            "orders": [{"id": o.id, "res": o.res_pos, "cus": o.cus_pos,
                        "status": o.status, "rider": o.rider_id}
                       for o in globalvar.get_value("orders")]}
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except OSError:
        pass


def do_start():
    """Handle order input."""
    vals = parse_coords(input("Enter rx ry cx cy: "))
    before = len(globalvar.get_value("riders"))
    order, rider = order_mod.create_and_assign(vals[:2], vals[2:])
    added = len(globalvar.get_value("riders")) > before
    print("Restaurant grid:", order.res_pos[0] // 100, order.res_pos[1] // 100,
          "Customer grid:", order.cus_pos[0] // 100, order.cus_pos[1] // 100)
    print("New rider added:", added)
    route = rider.planner.path([(rider.x, rider.y), order.res_pos,
                                order.cus_pos], rider.speed)
    for _ in range(1000):
        if order.status == "completed":
            break
        system.tick()
    system.check_recruit()
    print(display.render_map([rider], [order], route))
    print("Rider %d speed=%d time=%s" % (rider.rider_id, rider.speed,
                                         order.time_taken))


def main():
    """Run the main loop."""
    system.init_system()
    history = []
    while globalvar.get_value("running"):
        try:
            cmd = input("> ").strip().lower()
        except EOFError:
            break
        if not cmd:
            continue
        history.append(cmd)
        try:
            if cmd in ("quit", "exit", "q"):
                globalvar.set_value("running", False)
            elif cmd in ("start", "s"):
                do_start()
            elif cmd == "status":
                print(display.status_text())
            elif cmd in ("orders", "o"):
                print(display.orders_text())
            elif cmd in ("riders", "r"):
                print(display.riders_text())
            elif cmd == "history":
                print("\n".join(history))
            else:
                print("Unknown command.")
        except ValueError as e:
            print("Error:", e)
        except Exception as e:  # recover gracefully
            print("Unexpected error:", e)
    save()


if __name__ == "__main__":
    main()
