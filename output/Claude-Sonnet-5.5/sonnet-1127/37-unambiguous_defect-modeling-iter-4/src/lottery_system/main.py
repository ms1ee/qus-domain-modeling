from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    while True:
        c = input("1) Default list  2) Custom txt list: ").strip()
        if c == "1":
            users, errors = lm.load_default_list()
        elif c == "2":
            users, errors = lm.load_custom_list(input("Path: ").strip())
        else:
            continue
        for e in errors:
            print("  !", e)
        valid, dups = lm.validate_users(users)
        for d in dups:
            print(f"  ! Duplicate name: {d.name}")
        if errors or dups:
            a = input("Remove invalid data and continue? (y=continue / n=terminate): ").strip().lower()
            if a != "y":
                if c == "2":
                    continue
                return []
        return valid


def control(i):
    cmd = input(f"[Drawing winner #{i}] Enter to draw (pause/terminate): ").strip().lower()
    if cmd == "terminate":
        return "terminate"
    if cmd == "pause":
        while input("Paused. Type 'continue': ").strip().lower() != "continue":
            pass
    return None


def run():
    lm = ListManager()
    users = load_users(lm)
    if not users:
        print("No valid participants.")
        return
    print("Groups:")
    for g, n in lm.get_group_info(users).items():
        print(f"  {g}: {n}")
    pm = PrizeManager()
    pm.load_default_prizes()
    while True:
        print("Prizes:")
        for i, p in enumerate(pm.get_prizes(), 1):
            print(f"  {i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")
        c = input("a=add prize, o=reorder, s=start: ").strip().lower()
        if c == "a":
            try:
                name = input("Name: ").strip()
                q = int(input("Quantity: "))
                av = [x.strip() for x in input("Avoid groups (comma separated): ").split(",") if x.strip()]
                dr = input("Drawer (optional): ").strip() or None
                pm.add_prize(name, q, av, dr)
            except ValueError as e:
                print("Invalid:", e)
        elif c == "o":
            try:
                order = [int(x) for x in input("New order (e.g. 2 1 3): ").split()]
            except ValueError:
                order = []
            print("Reordered." if pm.reorder_prizes(order) else "Invalid order.")
        elif c == "s":
            break
    lot = LotteryManager(users)
    rm = ResultManager()

    def on_win(i, u):
        if u:
            print(f"Congratulations {u.name} ({u.department}) for winning {cur.name}")
        else:
            print(f"Currently drawing the {i}th winner")

    for n, cur in enumerate(pm.get_prizes(), 1):
        print(f"\n=== Round {n}: {cur.name} x{cur.quantity} | {lot.describe_rules(cur)}")
        won = lot.draw_round(cur, rm, control, on_win)
        print(f"Round {n} results:")
        for k, u in enumerate(won, 1):
            print(f"  {k}. {u.name} ({u.department})")
    prizes = list(reversed(pm.get_prizes()))
    print("\n=== Final winners ===")
    for name, ws in rm.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name}, {w.user.department}, {name}")
    ok, msg = rm.export_to_csv(prizes)
    print(msg)


if __name__ == "__main__":
    run()
