"""Command-line interaction for the lottery system."""

from lottery_system.models import Prize
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import (
    CHENG_RU_GROUP,
    FALLBACK_DRAWER,
    SPECIAL_DRAWER,
    TRACKED_DRAWERS,
    LotteryManager,
)
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ordinal(n: int) -> str:
    """Return the English ordinal representation of n (1 -> 1st)."""
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryCLI:
    """Interactive command-line controller for the whole lottery process."""

    def __init__(self, input_func=input, output_func=print):
        self._input = input_func
        self._print = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.lottery: LotteryManager | None = None
        self.users = []
        self.lottery_done = False

    # ------------------------------------------------------------------ helpers
    def ask(self, prompt: str) -> str:
        return self._input(prompt).strip()

    def say(self, message: str = "") -> None:
        self._print(message)

    # --------------------------------------------------------------- entry point
    def run(self) -> None:
        self.say("=== Company Team Building Smart Lottery System ===")
        if not self.setup_participants():
            self.say("Exiting the system.")
            return
        self.main_menu()
        self.say("Goodbye!")

    # ------------------------------------------------------- list management
    def setup_participants(self) -> bool:
        while True:
            self.say("\n-- Participant List --")
            self.say("1. Load built-in default team building list")
            self.say("2. Upload custom txt list (format: Name,Department Group per line)")
            self.say("0. Exit")
            choice = self.ask("Select an option: ")

            if choice == "0":
                return False
            if choice == "1":
                users, errors = self.list_manager.load_default_list()
            elif choice == "2":
                path = self.ask("Enter the txt file path: ")
                users, errors = self.list_manager.load_custom_list(path)
            else:
                self.say("Invalid option, please try again.")
                continue

            if errors:
                self.say(f"Found {len(errors)} invalid entr{'y' if len(errors) == 1 else 'ies'}:")
                for error in errors:
                    self.say(f"  {error}")
                action = self.ask(
                    "Type 'remove' to discard invalid data and continue, "
                    "or 'terminate' to abandon this upload: "
                ).lower()
                if action != "remove":
                    self.say("Upload terminated.")
                    continue

            valid_users, duplicates = self.list_manager.validate_users(users)
            if duplicates:
                self.say(f"Found {len(duplicates)} duplicate name(s):")
                for user in duplicates:
                    self.say(f"  {user.name} ({user.department})")
                action = self.ask(
                    "Type 'remove' to drop duplicates and continue, "
                    "or 'terminate' to abandon this upload: "
                ).lower()
                if action != "remove":
                    self.say("Upload terminated.")
                    continue

            if not valid_users:
                self.say("No valid participants remain. Please load another list.")
                continue

            self.users = valid_users
            self.say("Participant list loaded successfully.")
            self.show_groups()
            return True

    def show_groups(self) -> None:
        info = self.list_manager.get_group_info(self.users)
        self.say(f"\nValid participants: {len(self.users)}")
        self.say("Department groups:")
        for department, count in info.items():
            self.say(f"  {department}: {count} people")

    def group_names(self) -> list[str]:
        return list(self.list_manager.get_group_info(self.users).keys())

    # --------------------------------------------------------- main menu
    def main_menu(self) -> None:
        while True:
            self.say("\n-- Main Menu --")
            self.say("1. Load default prize library")
            self.say("2. Add custom prize")
            self.say("3. View prizes")
            self.say("4. Reorder prizes")
            self.say("5. View department groups")
            self.say("6. Start lottery")
            self.say("0. Exit")
            choice = self.ask("Select an option: ")

            if choice == "0":
                return
            if choice == "1":
                self.load_default_prizes()
            elif choice == "2":
                self.add_custom_prize()
            elif choice == "3":
                self.view_prizes()
            elif choice == "4":
                self.reorder_prizes()
            elif choice == "5":
                self.show_groups()
            elif choice == "6":
                self.start_lottery()
            else:
                self.say("Invalid option, please try again.")

    # ------------------------------------------------------ prize configuration
    def load_default_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        if errors:
            self.say("Some default prizes could not be loaded:")
            for error in errors:
                self.say(f"  {error}")
        else:
            self.say("Default prize library loaded.")

    def _ask_positive_int(self, prompt: str) -> int:
        while True:
            raw = self.ask(prompt)
            try:
                value = int(raw)
            except ValueError:
                value = 0
            if value > 0:
                return value
            self.say("Please enter a positive integer.")

    def _ask_avoid_groups(self, groups: list[str]) -> list[str]:
        if not groups:
            return []
        while True:
            self.say("Department groups available to avoid:")
            for index, group in enumerate(groups, start=1):
                self.say(f"  {index}. {group}")
            raw = self.ask("Enter numbers or names separated by commas (blank for none): ")
            if not raw:
                return []
            selected: list[str] = []
            invalid: list[str] = []
            tokens = [t.strip() for t in raw.split(",") if t.strip()]
            for token in tokens:
                match = None
                if token.isdigit() and 1 <= int(token) <= len(groups):
                    match = groups[int(token) - 1]
                else:
                    for group in groups:
                        if group.lower() == token.lower():
                            match = group
                            break
                if match is None:
                    invalid.append(token)
                elif match not in selected:
                    selected.append(match)
            if invalid:
                self.say(f"Unknown group(s): {', '.join(invalid)}. Please try again.")
                continue
            return selected

    def add_custom_prize(self) -> None:
        name = self.ask("Prize name: ")
        if not name:
            self.say("Prize name must not be empty.")
            return
        quantity = self._ask_positive_int("Quantity: ")
        avoid_groups = self._ask_avoid_groups(self.group_names())
        drawer = self.ask("Associated lottery person (leave blank for none): ") or None
        try:
            self.prize_manager.add_prize(name, quantity, avoid_groups, drawer)
        except ValueError as error:
            self.say(f"Failed to add prize: {error}")
        else:
            self.say("Prize added successfully.")

    def view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.say("No prizes configured.")
            return
        self.say("Prize list (in lottery order):")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) or "None"
            drawer = prize.associated_drawer or "None"
            self.say(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Avoid groups: {avoid} | Associated person: {drawer}"
            )

    def reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.say("No prizes configured.")
            return
        self.view_prizes()
        raw = self.ask("Enter new order as serial numbers separated by spaces or commas (e.g. 2 1 3): ")
        try:
            order = [int(token) for token in raw.replace(",", " ").split()]
        except ValueError:
            order = None
        if order is None or not self.prize_manager.reorder_prizes(order):
            self.say("Invalid order. Each serial number must appear exactly once.")
        else:
            self.say("Prize order updated.")

    # ------------------------------------------------------- lottery process
    def describe_rule(self, prize: Prize) -> str:
        if prize.associated_drawer == SPECIAL_DRAWER:
            return (
                "Previous winners are excluded. Special rule for "
                f"{SPECIAL_DRAWER}: group avoidance is not applied."
            )
        parts = ["Previous winners are excluded"]
        if prize.avoid_groups:
            parts.append(f"members of avoided groups ({', '.join(prize.avoid_groups)}) are excluded")
        if prize.associated_drawer == FALLBACK_DRAWER:
            parts.append(
                f"fallback protection: if neither of the last two {TRACKED_DRAWERS[0]}/"
                f"{TRACKED_DRAWERS[1]} draws included {CHENG_RU_GROUP} members, "
                f"only {CHENG_RU_GROUP} members are eligible"
            )
        if prize.associated_drawer:
            parts.append(f"associated lottery person: {prize.associated_drawer}")
        return "; ".join(parts)

    def wait_for_draw_command(self) -> bool:
        """Return True to draw the next winner, False to terminate the round."""
        while True:
            command = self.ask("[Enter] draw next | 'pause' | 'terminate': ").lower()
            if command == "":
                return True
            if command == "terminate":
                return False
            if command == "pause":
                self.say("Lottery paused. Type 'continue' to resume or 'terminate' to skip this round.")
                while True:
                    resume = self.ask("(paused) ").lower()
                    if resume == "continue":
                        self.say("Lottery resumed.")
                        return True
                    if resume == "terminate":
                        return False
                    self.say("Type 'continue' or 'terminate'.")
            if command == "continue":
                self.say("Lottery is not paused.")
                continue
            self.say("Unknown command.")

    def run_round(self, round_no: int, prize: Prize) -> None:
        self.say(f"\n--- Round {round_no}: {prize.name} ---")
        self.say(f"Quantity: {prize.quantity}")
        self.say(f"Rule: {self.describe_rule(prize)}")

        round_winners = []
        for index in range(1, prize.quantity + 1):
            if not self.wait_for_draw_command():
                self.say("Round terminated and skipped.")
                break
            self.say(f"Currently drawing the {ordinal(index)} winner...")
            user = self.lottery.draw(prize)
            if user is None:
                self.say("No eligible participants remain for this prize. Round ends.")
                break
            winner = self.result_manager.add_winner(user, prize)
            round_winners.append(winner)
            self.say(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        self.say(f"Round {round_no} results:")
        if not round_winners:
            self.say("  (no winners)")
        for position, winner in enumerate(round_winners, start=1):
            self.say(f"  {position}. {winner.user.name} ({winner.user.department})")

    def start_lottery(self) -> None:
        if self.lottery_done:
            self.say("The lottery has already been completed in this session.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.say("No prizes configured. Please load or add prizes first.")
            return

        self.lottery = LotteryManager(self.users)
        self.say("\n=== Lottery started ===")
        for round_no, prize in enumerate(prizes, start=1):
            self.run_round(round_no, prize)
        self.lottery_done = True
        self.say("\n=== Lottery finished ===")
        self.show_final_results(prizes)
        self.offer_export(prizes)

    def show_final_results(self, prizes: list[Prize]) -> None:
        grouped = self.result_manager.get_winners_by_prize(prizes)
        self.say("\n=== Complete Winner List ===")
        self.say("Name | Department | Prize")
        total = 0
        for winners in grouped.values():
            for winner in winners:
                total += 1
                self.say(f"{winner.user.name} | {winner.user.department} | {winner.prize.name}")
        if total == 0:
            self.say("(no winners)")

    def offer_export(self, prizes: list[Prize]) -> None:
        answer = self.ask("Export the winner list to a file? (y/n): ").lower()
        if answer in ("y", "yes"):
            _, message = self.result_manager.export_to_csv(prizes)
            self.say(message)


def main(input_func=input, output_func=print) -> None:
    cli = LotteryCLI(input_func, output_func)
    try:
        cli.run()
    except (EOFError, KeyboardInterrupt):
        output_func("\nInput closed. Exiting.")
