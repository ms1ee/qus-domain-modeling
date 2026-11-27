"""Command line entry point."""
import system
import display
import order as order_mod


def parse_start(text):
    """Parse four ints in 0-800; raise ValueError on bad input."""
    parts = text.replace(",", " ").replace("[", " ").replace("]", " ").split()
    if len(parts) != 4:
        raise ValueError("need exactly four integers")
    vals = [int(p) for p in parts]
    if any(v < 0 or v > 800 for v in vals):
        raise ValueError("coordinates must be within 0-800")
    return vals


def main():
    system.init_system()
    import globalvar
    history = []
    aliases = {"s": "status", "o": "orders", "r": "riders", "q": "quit",
               "t": "tick"}
    while globalvar.get_value("running"):
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            continue
        history.append(line)
        cmd, _, rest = line.partition(" ")
        cmd = aliases.get(cmd.lower(), cmd.lower())
        try:
            if cmd == "start":
                if not rest:
                    rest = input("restaurant_x restaurant_y customer_x "
                                 "customer_y: ")
                v = parse_start(rest)
                o, r, new = order_mod.create_order(*v)
                if r is None:
                    print("No rider available.")
                    continue
                print("Restaurant %s Customer %s new rider: %s" % (
                    o.res_pos, o.cus_pos, new))
                print(display.render_map(r, o))
                total = (abs(r.x - o.res_pos[0]) + abs(r.y - o.res_pos[1])
                         + o.distance)
                print("Rider %d speed %d est. time %d ticks" % (
                    r.rider_id, r.speed, -(-total // r.speed)))
            elif cmd == "tick":
                system.tick(int(rest) if rest else 1)
                print(display.render_map())
            elif cmd == "status":
                print(display.render_status())
                print(display.render_map())
            elif cmd == "orders":
                print(display.render_orders())
            elif cmd == "riders":
                print(display.render_riders())
            elif cmd == "history":
                print("\n".join(history))
            elif cmd in ("quit", "exit"):
                globalvar.set_value("running", False)
            else:
                print("Unknown command. Use start/tick/status/orders/"
                      "riders/quit.")
        except ValueError as e:
            print("Error: %s" % e)


if __name__ == "__main__":
    main()
