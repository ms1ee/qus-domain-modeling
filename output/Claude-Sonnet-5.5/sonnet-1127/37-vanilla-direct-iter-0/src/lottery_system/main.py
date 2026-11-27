from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    while True:
        c = input("Load list: 1) default 2) custom txt file: ").strip()
        if c == "1":
            users, errs = lm.load_default_list()
        elif c == "2":
            users, errs = lm.load_custom_list(input("Path: ").strip())
        else:
            continue
        for e in errs:
            print(e)
        if errs and input("Errors found. Remove invalid lines and continue? (y/n): ").lower() != "y":
            if input("Terminate upload and retry? (y/n): ").lower() == "y":
                continue
        valid, dups = lm.validate_users(users)
        for d in dups:
            print(f"Duplicate name removed: {d.name} ({d.department})")
        if valid:
            return valid
        print("No valid users.")


def setup_prizes(pm):
    if input("Load default prizes? (y/n): ").lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").lower() == "y":
        try:
            name = input("Name: ").strip()
            q = int(input("Quantity: "))
            avoid = [g.strip() for g in input("Avoid groups (comma separated): ").split(",") if g.strip()]
            drawer = input("Associated drawer (optional): ").strip() or None
            pm.add_prize(name, q, avoid, drawer)
        except ValueError as e:
            print("Invalid:", e)
    prizes = pm.get_prizes()
    for i, p in enumerate(prizes, 1):
        print(f"{i}. {p.name} x{p.quantity}")
    s = input("New order (space separated numbers, Enter to keep): ").split()
    if s:
        try:
            ok = pm.reorder_prizes([int(x) for x in s])
        except ValueError:
            ok = False
        print("Reordered." if ok else "Invalid order, keeping default.")


def run_round(lot, rm, prize):
    print(f"\n=== {prize.name} === {lot.describe(prize)}")
    got = []
    i = 1
    while i <= prize.quantity:
        cmd = input(f"Press Enter to draw winner {i} (pause/terminate): ").strip().lower()
        if cmd == "pause":
            while input("Paused. Type 'continue': ").strip().lower() != "continue":
                pass
            continue
        if cmd == "terminate":
            print("Round terminated.")
            break
        print(f"Currently drawing the {i}th winner...")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible candidates left.")
            break
        rm.add_winner(u, prize)
        got.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
        i += 1
    lot.finish_round(prize, got)
    print("Round results:", ", ".join(u.name for u in got) or "none")


def main():
    lm = ListManager()
    users = load_users(lm)
    for g, n in lm.get_group_info(users).items():
        print(f"{g}: {n}")
    pm = PrizeManager()
    setup_prizes(pm)
    lot, rm = LotteryManager(users), ResultManager()
    prizes = pm.get_prizes()
    for p in prizes:
        run_round(lot, rm, p)
    print("\n=== Final Winners ===")
    for pname, ws in rm.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name},{w.user.department},{pname}")
    print(rm.export_to_csv(prizes)[1])


if __name__ == "__main__":
    main()
