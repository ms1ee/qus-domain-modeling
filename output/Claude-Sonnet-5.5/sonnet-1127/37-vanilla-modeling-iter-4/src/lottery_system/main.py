from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def load_list(lm):
    choice = ask("1) default list  2) custom txt list: ")
    if choice == "2":
        users, errors = lm.load_custom_list(ask("Path: "))
        if errors:
            print("Problems found:")
            for e in errors:
                print("  ", e)
            if ask("Terminate upload? (y/n): ").lower() == "y":
                return []
            print("Invalid lines removed.")
    else:
        users, _ = lm.load_default_list()
    users, dups = lm.validate_users(users)
    for d in dups:
        print(f"Duplicate removed: {d.name} ({d.department})")
    return users


def show_groups(lm, users):
    for g, c in lm.get_group_info(users).items():
        print(f"  {g}: {c}")


def config_prizes(pm):
    if ask("Load preset prizes? (y/n): ").lower() == "y":
        pm.load_default_prizes()
    while ask("Add custom prize? (y/n): ").lower() == "y":
        name = ask("Name: ")
        try:
            qty = int(ask("Quantity: "))
        except ValueError:
            print("Invalid quantity")
            continue
        avoid = [g.strip() for g in ask("Avoid groups (comma separated): ").split(",") if g.strip()]
        drawer = ask("Drawer (blank for none): ") or None
        pm.add_prize(name, qty, avoid, drawer)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")
    o = ask("New order (e.g. 3 1 2, blank to keep): ")
    if o:
        if not pm.reorder_prizes(o.replace(",", " ").split()):
            print("Invalid order, keeping original.")


def run_round(engine, rm, prize):
    print(f"\n=== {prize.name} | quantity {prize.quantity} | {prize.rule_description()} ===")
    won = []
    for i in range(1, prize.quantity + 1):
        cmd = ask(f"[Enter]=draw, pause, terminate: ").lower()
        if cmd == "pause":
            while True:
                c = ask("Paused. Type 'continue' or 'terminate': ").lower()
                if c in ("continue", "terminate"):
                    cmd = c
                    break
        if cmd == "terminate":
            print("Round terminated.")
            break
        print(f"Currently drawing the {i}th winner...")
        w = engine.draw_one(prize)
        if w is None:
            print("No eligible participants left.")
            break
        rm.add_winner(w, prize)
        won.append(w)
        print(f"Congratulations {w.name} ({w.department}) for winning {prize.name}")
    engine.end_round(prize, won)
    print("Round results:")
    for w in won:
        print(f"  {w.name} ({w.department})")


def main():
    lm = ListManager()
    users = load_list(lm)
    if not users:
        print("No participants loaded.")
        return
    show_groups(lm, users)
    pm = PrizeManager()
    config_prizes(pm)
    prizes = pm.get_prizes()
    if not prizes:
        print("No prizes configured.")
        return
    engine = LotteryManager(users)
    rm = ResultManager()
    for p in prizes:
        run_round(engine, rm, p)
    print("\n=== Final winners ===")
    for n, ws in rm.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name}, {w.user.department}, {n}")
    ok, msg = rm.export_to_csv(prizes)
    print(msg)


if __name__ == "__main__":
    main()
