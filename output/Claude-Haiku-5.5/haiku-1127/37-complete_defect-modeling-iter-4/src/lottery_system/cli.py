from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager, LI_BIN
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


DRAWER_CHOICES = ["Chen Qixian", "Jin Duo", "Ma Jiaqi", "Li Bin"]


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _ask(prompt: str) -> str:
    return input(prompt).strip()


class LotteryCLI:
    """Command-line interaction for the lottery process."""

    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users = []
        self.result_manager = ResultManager()

    # ------------------------------------------------------------------ #
    # Entry
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        print("=" * 60)
        print("  Company Team Building - Smart Lottery System")
        print("=" * 60)
        users = self.setup_list()
        if users is None:
            print("Goodbye.")
            return
        self.users = users
        self.setup_prizes()
        print("Goodbye.")

    # ------------------------------------------------------------------ #
    # List management
    # ------------------------------------------------------------------ #
    def setup_list(self):
        while True:
            print("\n--- Participant List ---")
            print("1. Use built-in default team building list")
            print("2. Upload custom txt list (each line: Name,Department Group)")
            print("0. Exit")
            choice = _ask("Select: ")
            if choice == "0":
                return None
            if choice == "1":
                users, errors = self.list_manager.load_default_list()
            elif choice == "2":
                path = _ask("Enter txt file path: ")
                users, errors = self.list_manager.load_custom_list(path)
            else:
                print("Invalid option.")
                continue

            if errors:
                print(f"\nFound {len(errors)} invalid line(s):")
                for err in errors:
                    print(f"  - {err}")
                action = self._ask_option(
                    "[r] remove invalid data and continue / [t] terminate upload: ",
                    ["r", "t"],
                )
                if action == "t":
                    print("Upload terminated.")
                    continue

            valid, duplicates = self.list_manager.validate_users(users)
            if duplicates:
                print(f"\nFound {len(duplicates)} duplicate name(s):")
                for user in duplicates:
                    print(f"  - {user.name} ({user.department})")
                action = self._ask_option(
                    "[r] remove duplicates (keep first) and continue / [t] terminate upload: ",
                    ["r", "t"],
                )
                if action == "t":
                    print("Upload terminated.")
                    continue

            if not valid:
                print("No valid participants found. Please try again.")
                continue

            self._show_groups(valid)
            return valid

    def _show_groups(self, users) -> None:
        info = self.list_manager.get_group_info(users)
        print(f"\nLoaded {len(users)} participant(s) in {len(info)} group(s):")
        for idx, (dept, count) in enumerate(info.items(), start=1):
            print(f"  {idx}. {dept}: {count} people")

    # ------------------------------------------------------------------ #
    # Prize configuration
    # ------------------------------------------------------------------ #
    def setup_prizes(self) -> None:
        while True:
            print("\n--- Prize Configuration ---")
            print("1. Load default prize library")
            print("2. Add custom prize")
            print("3. View prizes")
            print("4. Set avoid groups for a prize")
            print("5. Reorder prizes (lottery sequence)")
            print("6. View participant groups")
            print("7. Start lottery")
            print("0. Exit")
            choice = _ask("Select: ")
            if choice == "0":
                return
            if choice == "1":
                for err in self.prize_manager.load_default_prizes():
                    print(f"Note: {err}")
                print("Default prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._view_prizes()
            elif choice == "4":
                self._set_avoid_groups()
            elif choice == "5":
                self._reorder_prizes()
            elif choice == "6":
                self._show_groups(self.users)
            elif choice == "7":
                if self.start_lottery():
                    return
            else:
                print("Invalid option.")

    def _add_custom_prize(self) -> None:
        name = _ask("Prize name: ")
        try:
            quantity = int(_ask("Quantity: "))
        except ValueError:
            print("Quantity must be an integer.")
            return
        groups = self._select_groups()
        print("Associated lottery person (suggestions: " + ", ".join(DRAWER_CHOICES) + ")")
        drawer = _ask("Enter name (leave blank for none): ")
        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer or None)
            print(f"Prize '{name.strip()}' added.")
        except ValueError as exc:
            print(f"Cannot add prize: {exc}")

    def _select_groups(self) -> list[str]:
        info = self.list_manager.get_group_info(self.users)
        groups = list(info.keys())
        if not groups:
            return []
        print("Available groups:")
        for idx, dept in enumerate(groups, start=1):
            print(f"  {idx}. {dept}")
        raw = _ask("Avoid groups (numbers separated by commas, blank for none): ")
        selected: list[str] = []
        for token in raw.replace(" ", "").split(","):
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups):
                dept = groups[int(token) - 1]
                if dept not in selected:
                    selected.append(dept)
            else:
                print(f"Ignored invalid group selection: {token}")
        return selected

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nCurrent prize sequence:")
        for idx, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
            drawer = prize.associated_drawer or "None"
            print(f"  {idx}. {prize.name} | Quantity: {prize.quantity} | "
                  f"Lottery person: {drawer} | Avoid groups: {avoid}")

    def _set_avoid_groups(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._view_prizes()
        try:
            idx = int(_ask("Prize number: "))
            prize = prizes[idx - 1]
        except (ValueError, IndexError):
            print("Invalid prize number.")
            return
        groups = self._select_groups()
        self.prize_manager.set_avoid_groups(prize.name, groups)
        print(f"Avoid groups for '{prize.name}' set to: {', '.join(groups) or 'None'}")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._view_prizes()
        raw = _ask("Enter new order as serial numbers (e.g. 2 1 3): ")
        tokens = raw.replace(",", " ").split()
        try:
            order = [int(t) for t in tokens]
        except ValueError:
            print("Serial numbers must be integers.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize sequence updated.")
            self._view_prizes()
        else:
            print("Invalid order: must contain every serial number exactly once.")

    # ------------------------------------------------------------------ #
    # Lottery process
    # ------------------------------------------------------------------ #
    def start_lottery(self) -> bool:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured. Please load or add prizes first.")
            return False
        if not self.users:
            print("No participants loaded.")
            return False

        self.result_manager = ResultManager()
        lottery = LotteryManager(self.users)

        print("\n" + "=" * 60)
        print("  LOTTERY START")
        print("=" * 60)
        for round_no, prize in enumerate(prizes, start=1):
            self._run_round(round_no, prize, lottery)

        self._show_summary(prizes)
        self._ask_export(prizes)
        return True

    def _run_round(self, round_no, prize, lottery: LotteryManager) -> None:
        print(f"\n--- Round {round_no}: {prize.name} ---")
        print(f"Quantity: {prize.quantity}")
        print(f"Rules: {lottery.describe_rule(prize)}")

        round_winners = []
        for draw_idx in range(1, prize.quantity + 1):
            command = self._before_draw()
            if command == "terminate":
                print("Current round terminated. Skipping remaining draws.")
                break

            print(f"Currently drawing the {ordinal(draw_idx)} winner...")
            user = lottery.draw_one(prize)
            if user is None:
                print("No eligible participants remain for this prize. Round ends.")
                break
            winner = self.result_manager.add_winner(user, prize)
            round_winners.append(winner)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        print(f"\nRound {round_no} results ({prize.name}):")
        if round_winners:
            for w in round_winners:
                print(f"  #{w.winning_order}: {w.name} ({w.department})")
        else:
            print("  No winners in this round.")

    def _before_draw(self) -> str:
        """Handles pause / continue / terminate commands before each draw.

        Returns 'next' to draw or 'terminate' to end the current round.
        """
        while True:
            cmd = _ask("Press Enter to draw next winner, or type 'pause' / 'terminate': ").lower()
            if cmd == "":
                return "next"
            if cmd == "terminate":
                return "terminate"
            if cmd == "pause":
                print("Lottery PAUSED. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    sub = _ask("> ").lower()
                    if sub == "continue":
                        print("Lottery resumed.")
                        return "next"
                    if sub == "terminate":
                        return "terminate"
                    print("Please type 'continue' or 'terminate'.")
            print("Unknown command. Use Enter, 'pause', or 'terminate'.")

    def _show_summary(self, prizes) -> None:
        print("\n" + "=" * 60)
        print("  FINAL WINNER LIST")
        print("=" * 60)
        winners = self.result_manager.get_winners()
        if not winners:
            print("No winners.")
            return
        by_prize = self.result_manager.get_winners_by_prize(prizes)
        for prize in prizes:
            print(f"\n{prize.name}:")
            items = by_prize.get(prize.name, [])
            if not items:
                print("  (no winners)")
            for w in items:
                print(f"  {w.name} ({w.department})")

    def _ask_export(self, prizes) -> None:
        choice = _ask("\nExport winner list to CSV file? (y/n): ").lower()
        if choice == "y":
            _, message = self.result_manager.export_to_csv(prizes)
            print(message)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _ask_option(self, prompt: str, options: list[str]) -> str:
        while True:
            value = _ask(prompt).lower()
            if value in options:
                return value
            print(f"Please enter one of: {', '.join(options)}")


def main() -> None:
    try:
        LotteryCLI().run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
