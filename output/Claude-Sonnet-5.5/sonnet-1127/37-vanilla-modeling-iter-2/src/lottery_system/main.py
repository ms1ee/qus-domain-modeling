from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_list(lm):
    c = input("1) default list  2) custom txt file: ").strip()
    if c == "1":
        users, errs = lm.load_default_list()
    else:
        users, errs = lm.load_custom_list(input("Path: ").strip())
    for e in errs:
        print("  ", e)
    valid, dups = lm.validate_users(users)
    for d in dups:
        print(f"   Duplicate name: {d.name} ({d.department})")
    if errs or dups:
        if input("Remove invalid data and continue? (y = remove, n = terminate): ").strip().lower() != "y":
            print("Upload terminated.")
            return None
    print(f"Loaded {len(valid)} participants.")
    return valid


def show_groups(lm, users):
    if not users:
        print("No list loaded.")
        return
    for g, n in lm.get_group_info(users).items():
        print(f"  {g}: {n}")


def prize_menu(pm):
    while True:
        prizes = pm.get_prizes()
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")
        c = input("a) add  d) load presets  r) reorder  b) back: ").strip().lower()
        if c == "a":
            name = input("Name: ").strip()
            try:
                q = int(input("Quantity: "))
                avoid = [x.strip() for x in input("Avoid groups (comma separated): ").split(",") if x.strip()]
                drawer = input("Lottery person (optional): ").strip() or None
                pm.add_prize(name, q, avoid, drawer)
            except ValueError as e:
                print("Invalid:", e)
        elif c == "d":
            pm.load_default_prizes()
        elif c == "r":
            try:
                order = [int(x) for x in input("New order (e.g. 2,1,3): ").replace(" ", "").split(",")]
            except ValueError:
                order = []
            print("Reordered." if pm.reorder_prizes(order) else "Invalid order.")
        elif c == "b":
            return


def run_lottery(users, pm, rm):
    lot = LotteryManager(users)
    for idx, prize in enumerate(pm.get_prizes(), 1):
        print(f"\n=== Round {idx}: {prize.name} | quantity {prize.quantity} ===")
        print("Rules:", lot.describe_rules(prize))
        won = []
        n = 0
        while n < prize.quantity:
            cmd = input(f"Enter to draw winner {n + 1} (pause/terminate): ").strip().lower()
            if cmd == "pause":
                print("Paused.")
                while True:
                    c2 = input("Type 'continue' or 'terminate': ").strip().lower()
                    if c2 in ("continue", "terminate"):
                        cmd = c2
                        break
                if cmd == "terminate":
                    print("Round terminated.")
                    break
                continue
            if cmd == "terminate":
                print("Round terminated.")
                break
            print(f"Currently drawing the {n + 1}th winner...")
            u = lot.draw_one(prize)
            if u is None:
                print("No eligible participants left.")
                break
            rm.add_winner(u, prize)
            won.append(u)
            n += 1
            print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
        lot.finish_round(prize, won)
        print("Round results:")
        for i, u in enumerate(won, 1):
            print(f"  {i}. {u.name} ({u.department})")


def summary(pm, rm):
    ordered = list(reversed(pm.get_prizes()))
    for pname, ws in rm.get_winners_by_prize(ordered).items():
        print(pname)
        for w in ws:
            print(f"  {w.user.name} ({w.user.department})  {w.time:%H:%M:%S}")
    return ordered


def main():
    lm = ListManager()
    pm = PrizeManager()
    rm = ResultManager()
    users = []
    while True:
        print("\n1 Load list  2 View groups  3 Prizes  4 Start lottery  5 Export  0 Exit")
        c = input("> ").strip()
        if c == "1":
            r = load_list(lm)
            if r is not None:
                users = r
        elif c == "2":
            show_groups(lm, users)
        elif c == "3":
            prize_menu(pm)
        elif c == "4":
            if not users or not pm.get_prizes():
                print("Load a list and configure prizes first.")
                continue
            rm = ResultManager()
            run_lottery(users, pm, rm)
            print("\n=== Final winners ===")
            summary(pm, rm)
        elif c == "5":
            print(rm.export_to_csv(list(reversed(pm.get_prizes())))[1])
        elif c == "0":
            break


if __name__ == "__main__":
    main()
