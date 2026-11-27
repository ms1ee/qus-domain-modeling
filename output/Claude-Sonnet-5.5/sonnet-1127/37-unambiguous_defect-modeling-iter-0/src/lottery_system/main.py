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
        users, dups = lm.validate_users(users)
        for d in dups:
            print(f"Duplicate name: {d.name} ({d.department})")
        if errs or dups:
            a = input("Remove invalid data and continue? (y = remove, n = terminate upload): ").strip().lower()
            if a != "y":
                continue
        if users:
            return users
        print("No valid users.")


def show_groups(lm, users):
    for g, n in lm.get_group_info(users).items():
        print(f"  {g}: {n}")


def configure_prizes(pm, users, lm):
    if input("Load preset prizes? (y/n): ").strip().lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").strip().lower() == "y":
        name = input("Prize name: ")
        try:
            q = int(input("Quantity: "))
            avoid = [g.strip() for g in input("Avoid groups (comma separated, blank none): ").split(",") if g.strip()]
            dr = input("Associated drawer (blank none): ").strip() or None
            pm.add_prize(name, q, avoid, dr)
        except ValueError as e:
            print("Invalid:", e)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity}")
    s = input("New order as numbers (blank keep): ").split()
    if s:
        try:
            ok = pm.reorder_prizes([int(x) for x in s])
        except ValueError:
            ok = False
        print("Reordered." if ok else "Invalid order, keeping original.")


def describe(p):
    d = f"Avoid groups: {', '.join(p.avoid_groups) or 'none'}"
    if p.associated_drawer:
        d += f"; Drawer: {p.associated_drawer}"
    return d


def run():
    lm_list = ListManager()
    users = load_users(lm_list)
    print("Groups:")
    show_groups(lm_list, users)
    pm = PrizeManager()
    configure_prizes(pm, users, lm_list)
    prizes = pm.get_prizes()
    lot = LotteryManager(users)
    rm = ResultManager()
    for idx, p in enumerate(prizes, 1):
        print(f"\n=== Round {idx}: {p.name} (quantity {p.quantity}) | {describe(p)} ===")
        round_winners = []
        n = 0
        while n < p.quantity:
            cmd = input("Enter to draw / pause / terminate: ").strip().lower()
            if cmd == "pause":
                print("Paused.")
                while input("Type 'continue' to resume: ").strip().lower() != "continue":
                    pass
                continue
            if cmd == "terminate":
                print("Round terminated.")
                break
            print(f"Currently drawing the {n + 1}th winner...")
            u = lot.draw_one(p)
            if u is None:
                print("No eligible participants left.")
                break
            n += 1
            rm.add_winner(u, p)
            round_winners.append(u)
            print(f"Congratulations {u.name} ({u.department}) for winning {p.name}")
        lot.record_round(p, round_winners)
        print(f"Round {idx} results:")
        for i, u in enumerate(round_winners, 1):
            print(f"  {i}. {u.name} ({u.department})")
    print("\n=== Final Winner List ===")
    for pname, ws in rm.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name}, {w.user.department}, {pname}")
    if input("Export results? (y/n): ").strip().lower() == "y":
        print(rm.export_to_csv(prizes)[1])


if __name__ == "__main__":
    run()
