from .services.list_manager import ListManager
from .services.prize_manager import PrizeManager
from .services.lottery_manager import LotteryManager
from .services.result_manager import ResultManager


def load_users(lm: ListManager):
    while True:
        c = input("Load list: 1) default 2) custom txt file: ").strip()
        if c == "1":
            users, errors = lm.load_default_list()
        elif c == "2":
            users, errors = lm.load_custom_list(input("Path: ").strip())
        else:
            continue
        for e in errors:
            print(e)
        if errors and c == "2":
            a = input("Errors found. (r)emove invalid and continue / (t)erminate: ").strip().lower()
            if a.startswith("t"):
                continue
        valid, dups = lm.validate_users(users)
        for d in dups:
            print(f"Duplicate name removed: {d.name} ({d.department})")
        if valid:
            return valid
        print("No valid users.")


def configure_prizes(pm: PrizeManager, groups):
    if input("Load default prizes? (y/n): ").strip().lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").strip().lower() == "y":
        name = input("Prize name: ").strip()
        try:
            qty = int(input("Quantity: "))
        except ValueError:
            print("Invalid quantity")
            continue
        avoid = [g.strip() for g in input("Avoid groups (comma separated, optional): ").split(",") if g.strip()]
        drawer = input("Associated drawer (optional): ").strip() or None
        try:
            pm.add_prize(name, qty, avoid, drawer)
        except ValueError as e:
            print(e)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")
    s = input("New order (space-separated numbers, empty to keep): ").split()
    if s:
        try:
            if not pm.reorder_prizes([int(x) for x in s]):
                print("Invalid order, keeping default.")
        except ValueError:
            print("Invalid order, keeping default.")


def run_round(prize, lot: LotteryManager, rm: ResultManager):
    print(f"\n=== {prize.name} | quantity {prize.quantity} ===")
    rule = []
    if prize.associated_drawer:
        rule.append(f"drawer: {prize.associated_drawer}")
    if prize.avoid_groups:
        rule.append("avoid: " + ", ".join(prize.avoid_groups))
    print("Rules: " + ("; ".join(rule) if rule else "none"))
    won = []
    i = 1
    while i <= prize.quantity:
        cmd = input("Enter to draw (pause / terminate): ").strip().lower()
        if cmd == "terminate":
            print("Round terminated.")
            break
        if cmd == "pause":
            while input("Paused. Type 'continue': ").strip().lower() != "continue":
                pass
            continue
        print(f"Currently drawing the {i}th winner...")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible candidates left.")
            break
        rm.add_winner(u, prize)
        won.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
        i += 1
    lot.finish_round(prize, won)
    print("Round results: " + (", ".join(u.name for u in won) or "none"))


def main():
    lm = ListManager()
    users = load_users(lm)
    info = lm.get_group_info(users)
    for g, n in info.items():
        print(f"{g}: {n}")
    pm = PrizeManager()
    configure_prizes(pm, info)
    lot = LotteryManager(users)
    rm = ResultManager()
    prizes = pm.get_prizes()
    for p in prizes:
        run_round(p, lot, rm)
    print("\n=== Final winners ===")
    for name, ws in rm.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name} ({w.user.department}) - {name}")
    if input("Export results? (y/n): ").strip().lower() == "y":
        print(rm.export_to_csv(prizes)[1])


if __name__ == "__main__":
    main()
