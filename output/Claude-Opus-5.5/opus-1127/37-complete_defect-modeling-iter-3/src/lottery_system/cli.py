"""Command-line interface."""

from __future__ import annotations

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


class LotteryCLI:
    def __init__(self, input_func=input, output_func=print):
        self.input = input_func
        self.print = output_func
        self.event_name = "Company Team Building Event"
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery_done = False

    def ask(self, prompt: str) -> str:
        try:
            return self.input(prompt).strip()
        except EOFError:
            return "0"

    # ------------------------------------------------------------- list
    def _accept_list(self, users, errors):
        valid, duplicates = self.list_manager.validate_users(users)
        if errors or duplicates:
            self.print("Validation issues detected:")
            for e in errors:
                self.print("  " + e)
            for d in duplicates:
                self.print(f"  Duplicate Name: {d.name} ({d.department})")
            choice = self.ask("Type 'r' to remove invalid data and continue, 't' to terminate upload: ").lower()
            if choice != "r":
                self.print("Upload terminated.")
                return
        if not valid:
            self.print("No valid participants loaded.")
            return
        self.users = valid
        self.print(f"Loaded {len(valid)} valid participants.")

    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        self._accept_list(users, errors)

    def load_custom(self):
        path = self.ask("Enter txt file path: ")
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors and errors[0].startswith(("File not found", "Unable")):
            self.print(errors[0])
            return
        self._accept_list(users, errors)

    def view_groups(self):
        if not self.users:
            self.print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        self.print("Department groups:")
        for g, c in info.items():
            self.print(f"  {g}: {c} people")

    # ------------------------------------------------------------- prizes
    def load_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            self.print(e)
        self.print("Preset prizes loaded.")

    def add_prize(self):
        name = self.ask("Prize name: ")
        qty = self.ask("Quantity: ")
        groups_info = list(self.list_manager.get_group_info(self.users).keys())
        if groups_info:
            self.print("Available groups: " + ", ".join(f"{i}.{g}" for i, g in enumerate(groups_info, 1)))
        raw = self.ask("Avoidance groups (numbers or names, comma separated, blank for none): ")
        groups = []
        for item in raw.replace("，", ",").split(","):
            item = item.strip()
            if not item:
                continue
            if item.isdigit() and 1 <= int(item) <= len(groups_info):
                groups.append(groups_info[int(item) - 1])
            else:
                groups.append(item)
        drawer = self.ask("Associated lottery person (blank for none): ")
        try:
            p = self.prize_manager.add_prize(name, qty, groups, drawer or None)
            self.print(f"Prize added: {p.name} x{p.quantity}")
        except ValueError as exc:
            self.print(f"Error: {exc}")

    def view_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            self.print(f"  {i}. {p.name} x{p.quantity} | {p.rule_description}")

    def reorder(self):
        self.view_prizes()
        raw = self.ask("Enter new order as serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace("，", ",").replace(" ", ",").split(",") if x]
        except ValueError:
            self.print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            self.print("Prize order updated.")
            self.view_prizes()
        else:
            self.print("Invalid order.")

    # ------------------------------------------------------------- lottery
    def start_lottery(self):
        if not self.users:
            self.print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.print("Please configure prizes first.")
            return
        manager = LotteryManager(self.users)
        for w in self.result_manager.winners:
            manager.winner_names.add(w.user.name)
        for rnd, prize in enumerate(prizes, 1):
            self.print("=" * 50)
            self.print(f"Round {rnd}: {prize.name} | Quantity: {prize.quantity}")
            self.print(f"Rules: {manager.describe_rules(prize)}")
            state = {"terminated": False}

            def control(i, state=state):
                while True:
                    cmd = self.ask(f"[Enter]=draw {ordinal(i)} winner, 'pause', 'terminate': ").lower()
                    if cmd == "pause":
                        self.print("Lottery paused. Type 'continue' to resume.")
                        while True:
                            c = self.ask("> ").lower()
                            if c == "continue":
                                self.print("Lottery resumed.")
                                break
                            if c in ("terminate", "0"):
                                state["terminated"] = True
                                return "terminate"
                        continue
                    if cmd in ("terminate", "0"):
                        state["terminated"] = True
                        return "terminate"
                    return "draw"

            def on_draw(i, user, prize=prize):
                self.print(f"Currently drawing the {ordinal(i)} winner...")
                if user is None:
                    self.print("No eligible participants remain for this prize.")
                    return
                if manager.fallback_applied:
                    self.print("(Fallback rule applied: Cheng Ru Group protection)")
                self.result_manager.add_winner(user, prize)
                self.print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

            winners = manager.run_round(prize, control, on_draw)
            if state["terminated"]:
                self.print("Current round terminated and skipped.")
            self.print(f"Round {rnd} results:")
            if not winners:
                self.print("  (no winners)")
            for i, w in enumerate(winners, 1):
                self.print(f"  {i}. {w.name} ({w.department})")
        self.lottery_done = True
        self.show_results()

    def show_results(self):
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        self.print("=" * 50)
        self.print("Complete winner list:")
        if not self.result_manager.winners:
            self.print("  (no winners yet)")
            return
        for prize_name, winners in grouped.items():
            for w in winners:
                self.print(f"  {w.user.name}, {w.user.department}, {prize_name}")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        self.print(msg)

    # ------------------------------------------------------------- main
    def run(self):
        actions = {
            "1": self.load_default, "2": self.load_custom, "3": self.view_groups,
            "4": self.load_prizes, "5": self.add_prize, "6": self.view_prizes,
            "7": self.reorder, "8": self.start_lottery, "9": self.show_results,
            "10": self.export,
        }
        self.print(f"Welcome to the {self.event_name} Smart Lottery System")
        while True:
            self.print(
                "\n1. Load default list\n2. Upload custom list\n3. View groups\n"
                "4. Load preset prizes\n5. Add custom prize\n6. View prizes\n"
                "7. Reorder prizes\n8. Start lottery\n9. View winner list\n"
                "10. Export results\n0. Exit"
            )
            choice = self.ask("Select: ")
            if choice == "0":
                self.print("Goodbye!")
                return
            action = actions.get(choice)
            if action:
                action()
            else:
                self.print("Invalid option.")


def main():
    LotteryCLI().run()


if __name__ == "__main__":
    main()
