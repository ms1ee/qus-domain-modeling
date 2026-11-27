from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager


class LotterySystemCLI:
    """Command-line interface for the team building lottery."""

    def __init__(self, input_func=input, output_func=print):
        self._input = input_func
        self._print = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery_manager = None

    def ask(self, prompt: str) -> str:
        return self._input(prompt).strip()

    def out(self, message: str = "") -> None:
        self._print(message)

    def run(self) -> None:
        self.out("=== Company Team Building Smart Lottery System ===")
        while True:
            self.out("\n--- Main Menu ---")
            self.out("1. Load participant list")
            self.out("2. View department groups")
            self.out("3. Prize configuration")
            self.out("4. Start lottery")
            self.out("5. Results (view / export)")
            self.out("0. Exit")
            choice = self.ask("Select an option: ")
            if choice == "1":
                self.load_list()
            elif choice == "2":
                self.show_groups()
            elif choice == "3":
                self.prize_menu()
            elif choice == "4":
                self.start_lottery()
            elif choice == "5":
                self.results_menu()
            elif choice == "0":
                self.out("Goodbye!")
                return
            else:
                self.out("Invalid option, please try again.")

    # ----- participant list -----

    def load_list(self) -> None:
        self.out("Select list source:")
        self.out("1. Built-in default team building list")
        self.out("2. Upload custom txt list (format per line: Name,Department Group)")
        self.out("0. Cancel")
        source = self.ask("Option: ")
        if source == "1":
            users, errors = self.list_manager.load_default_list()
        elif source == "2":
            path = self.ask("Path to txt file: ")
            users, errors = self.list_manager.load_custom_list(path)
        else:
            return

        if errors:
            self.out(f"Found {len(errors)} invalid entr{'y' if len(errors) == 1 else 'ies'}:")
            for error in errors:
                self.out(f"  {error}")
            answer = self.ask("Enter 'r' to remove invalid data and continue, 'q' to terminate upload: ").lower()
            if answer != "r":
                self.out("Upload terminated. Current list unchanged.")
                return

        valid_users, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            self.out(f"Found {len(duplicates)} duplicate name(s):")
            for user in duplicates:
                self.out(f"  {user.name} ({user.department})")
            answer = self.ask(
                "Enter 'r' to remove duplicates (keep first occurrence), 'q' to terminate upload: "
            ).lower()
            if answer != "r":
                self.out("Upload terminated. Current list unchanged.")
                return

        if not valid_users:
            self.out("No valid participants found. Current list unchanged.")
            return

        self.users = valid_users
        self.out(f"Loaded {len(self.users)} participants.")

    def show_groups(self) -> None:
        if not self.users:
            self.out("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        self.out("Department groups:")
        for department, count in info.items():
            self.out(f"  {department}: {count} people")

    # ----- prizes -----

    def prize_menu(self) -> None:
        while True:
            self.out("\n--- Prize Configuration ---")
            self.out("1. Load default prize library")
            self.out("2. Add custom prize")
            self.out("3. Show prizes")
            self.out("4. Reorder lottery sequence")
            self.out("0. Back")
            choice = self.ask("Option: ")
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        self.out(f"  {error}")
                else:
                    self.out("Default prize library loaded.")
            elif choice == "2":
                self.add_custom_prize()
            elif choice == "3":
                self.show_prizes()
            elif choice == "4":
                self.reorder_prizes()
            elif choice == "0":
                return
            else:
                self.out("Invalid option.")

    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.out("No prizes configured.")
            return
        self.out("Lottery sequence:")
        for idx, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
            self.out(
                f"  {idx}. {prize.name} | Quantity: {prize.quantity} | "
                f"Lottery person: {prize.associated_drawer or 'None'} | Avoid groups: {avoid}"
            )

    def add_custom_prize(self) -> None:
        name = self.ask("Prize name: ")
        quantity_text = self.ask("Quantity: ")
        try:
            quantity = int(quantity_text)
        except ValueError:
            self.out("Error: quantity must be an integer.")
            return
        if self.users:
            known = ", ".join(self.list_manager.get_group_info(self.users).keys())
            self.out(f"Known groups: {known}")
        avoid_text = self.ask("Avoidance groups (comma-separated, blank for none): ")
        avoid = [g.strip() for g in avoid_text.split(",") if g.strip()]
        drawer = self.ask("Associated lottery person (blank for none): ") or None
        try:
            self.prize_manager.add_prize(name, quantity, avoid, drawer)
        except ValueError as exc:
            self.out(f"Error: {exc}")
            return
        self.out(f"Prize '{name.strip()}' added.")

    def reorder_prizes(self) -> None:
        if not self.prize_manager.get_prizes():
            self.out("No prizes configured.")
            return
        self.show_prizes()
        text = self.ask("Enter new order as serial numbers (e.g. 2 1 3), blank to cancel: ")
        if not text:
            return
        try:
            order = [int(token) for token in text.replace(",", " ").split()]
        except ValueError:
            self.out("Error: serial numbers must be integers.")
            return
        if self.prize_manager.reorder_prizes(order):
            self.out("Lottery sequence updated.")
        else:
            self.out("Error: invalid order. Each position must be used exactly once.")

    # ----- lottery -----

    def start_lottery(self) -> None:
        if not self.users:
            self.out("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.out("Please configure prizes first.")
            return
        if self.lottery_manager and self.lottery_manager.result_manager.get_winners():
            answer = self.ask("A previous session has results. Starting a new session clears them. Continue? (y/n): ")
            if answer.lower() != "y":
                return

        self.lottery_manager = LotteryManager(self.users)
        self.out(
            f"Lottery started with {len(self.users)} participants and {len(prizes)} round(s)."
        )
        self.out("Commands during a draw: [Enter] draw, 'pause', 'terminate'.")
        for prize in prizes:
            self.lottery_manager.run_round(prize, self._input, self._print)

        self.out("\n=== Lottery finished: final winner list ===")
        self.show_winners(prizes)

    def show_winners(self, prizes) -> None:
        if not self.lottery_manager:
            self.out("No lottery results yet.")
            return
        winners = self.lottery_manager.result_manager.get_sorted_winners(prizes)
        if not winners:
            self.out("No winners recorded.")
            return
        for winner in winners:
            self.out(
                f"{winner.prize_name}: {winner.user.name} ({winner.user.department}) "
                f"[{winner.timestamp}]"
            )

    def results_menu(self) -> None:
        if not self.lottery_manager:
            self.out("No lottery results yet.")
            return
        while True:
            self.out("\n--- Results ---")
            self.out("1. Show winner list")
            self.out("2. Export winner list to txt (CSV format)")
            self.out("0. Back")
            choice = self.ask("Option: ")
            prizes = self.prize_manager.get_prizes()
            if choice == "1":
                self.show_winners(prizes)
            elif choice == "2":
                _, message = self.lottery_manager.result_manager.export_to_csv(prizes)
                self.out(message)
            elif choice == "0":
                return
            else:
                self.out("Invalid option.")


def main() -> None:
    cli = LotterySystemCLI()
    try:
        cli.run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
