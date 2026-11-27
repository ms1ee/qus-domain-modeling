"""Command-line interaction for the team building lottery system."""

from __future__ import annotations

from lottery_system.models import CHEN_QIXIAN, JIN_DUO, LI_BIN, MA_JIAQI, CHENG_RU_GROUP, Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

DRAWER_OPTIONS = [CHEN_QIXIAN, JIN_DUO, MA_JIAQI, LI_BIN]

MENU = """
========== Team Building Lottery ==========
 1. Load built-in default participant list
 2. Upload custom participant txt list
 3. View department groups
 4. Load preset prizes
 5. Add custom prize
 6. View prize sequence
 7. Reorder prize sequence
 8. Start lottery
 9. View winner summary
10. Export winner list
 0. Exit
"""


def _ordinal(number: int) -> str:
    if 11 <= number % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotterySystemCLI:
    """Interactive console application."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.result_manager = ResultManager()
        self.lottery_manager: LotteryManager | None = None
        self.lottery_done = False

    # ------------------------------------------------------------------ helpers
    def _ask(self, prompt: str) -> str:
        return input(prompt).strip()

    def run(self) -> None:
        print("Welcome to the Team Building Smart Lottery System.")
        while True:
            print(MENU)
            choice = self._ask("Select an option: ")
            if choice == "0":
                print("Goodbye!")
                return
            handlers = {
                "1": self._load_default_list,
                "2": self._upload_custom_list,
                "3": self._view_groups,
                "4": self._load_preset_prizes,
                "5": self._add_custom_prize,
                "6": self._view_prizes,
                "7": self._reorder_prizes,
                "8": self._start_lottery,
                "9": self._show_summary,
                "10": self._export_winners,
            }
            handler = handlers.get(choice)
            if handler is None:
                print("Invalid option, please try again.")
                continue
            handler()

    # ------------------------------------------------------------ list handling
    def _load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        for error in errors:
            print(error)
        valid, duplicates = self.list_manager.validate_users(users)
        for user in duplicates:
            print(f"Duplicate ignored: {user.name} ({user.department})")
        self.users = valid
        print(f"Built-in list loaded: {len(self.users)} participants.")

    def _upload_custom_list(self) -> None:
        path = self._ask("Enter txt file path (leave empty to cancel): ")
        if not path:
            return
        users, errors = self.list_manager.load_custom_list(path)
        if errors:
            print(f"Found {len(errors)} problem(s):")
            for error in errors:
                print(f"  {error}")
            answer = self._ask("Remove invalid data and continue? (y/n): ").lower()
            if answer != "y":
                print("Upload terminated.")
                return
        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print("Duplicate names found:")
            for user in duplicates:
                print(f"  {user.name} ({user.department})")
            answer = self._ask("Remove duplicates (keep first occurrence) and continue? (y/n): ").lower()
            if answer != "y":
                print("Upload terminated.")
                return
        if not valid:
            print("No valid participants found. Upload failed.")
            return
        self.users = valid
        print(f"Custom list loaded: {len(self.users)} participants.")

    def _view_groups(self) -> None:
        if not self.users:
            print("No participant list loaded yet.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Department groups:")
        for group, count in info.items():
            print(f"  {group}: {count} people")
        print(f"Total: {len(self.users)} people in {len(info)} groups.")

    # ------------------------------------------------------------ prize handling
    def _load_preset_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        for error in errors:
            print(error)
        print("Preset prizes loaded.")

    def _select_drawer(self) -> str | None:
        print("Associated lottery person:")
        print("  0. None")
        for index, drawer in enumerate(DRAWER_OPTIONS, 1):
            print(f"  {index}. {drawer}")
        raw = self._ask("Select by number or type a name (blank for none): ")
        if not raw or raw == "0":
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(DRAWER_OPTIONS):
            return DRAWER_OPTIONS[int(raw) - 1]
        return raw

    def _select_avoid_groups(self) -> list[str]:
        groups = self.list_manager.get_group_info(self.users)
        if not groups:
            print("No department groups available (load a participant list first). No avoidance groups set.")
            return []
        names = list(groups.keys())
        print("Available department groups:")
        for index, name in enumerate(names, 1):
            print(f"  {index}. {name} ({groups[name]} people)")
        raw = self._ask("Select avoidance groups by number or name, comma separated (blank for none): ")
        selected: list[str] = []
        for token in [part.strip() for part in raw.split(",") if part.strip()]:
            if token.isdigit() and 1 <= int(token) <= len(names):
                group = names[int(token) - 1]
            else:
                matches = [name for name in names if name.lower() == token.lower()]
                if not matches:
                    print(f"Warning: unknown group '{token}' ignored.")
                    continue
                group = matches[0]
            if group not in selected:
                selected.append(group)
        return selected

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        if not name:
            print("Prize name cannot be empty.")
            return
        raw_quantity = self._ask("Quantity: ")
        if not raw_quantity.isdigit() or int(raw_quantity) < 1:
            print("Quantity must be a positive integer.")
            return
        avoid_groups = self._select_avoid_groups()
        drawer = self._select_drawer()
        try:
            self.prize_manager.add_prize(name, int(raw_quantity), avoid_groups, drawer)
        except ValueError as exc:
            print(f"Cannot add prize: {exc}")
            return
        print(f"Prize '{name}' added.")

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("Prize sequence:")
        for index, prize in enumerate(prizes, 1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
            drawer = prize.associated_drawer or "None"
            print(
                f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                f"drawer: {drawer} | avoid groups: {avoid}"
            )

    def _reorder_prizes(self) -> None:
        self._view_prizes()
        if not self.prize_manager.get_prizes():
            return
        raw = self._ask("Enter new order as serial numbers separated by spaces (e.g. 2 1 3), blank to skip: ")
        if not raw:
            return
        try:
            order = [int(token) for token in raw.split()]
        except ValueError:
            print("Invalid input: please enter integers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize sequence updated.")
        else:
            print("Invalid order: every serial number must appear exactly once.")

    # ------------------------------------------------------------ lottery flow
    def _rule_description(self, prize: Prize) -> str:
        if prize.associated_drawer == LI_BIN:
            return "Previous winners are excluded (avoidance groups not applied)."
        if self.lottery_manager and self.lottery_manager.is_fallback_active(prize):
            return (
                f"Cheng Ru group protection active: only {CHENG_RU_GROUP} members "
                "are eligible; previous winners are excluded."
            )
        description = "Previous winners are excluded"
        if prize.avoid_groups:
            description += f"; avoided groups: {', '.join(prize.avoid_groups)}"
        return description + "."

    def _confirm_next(self, order: int) -> bool:
        """Handle pause/continue/terminate. Returns False if the current round should end."""
        while True:
            command = self._ask(f"Press Enter to draw winner #{order} (or 'pause' / 'terminate'): ").lower()
            if command == "":
                return True
            if command == "terminate":
                return False
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    control = self._ask("(paused) > ").lower()
                    if control == "continue":
                        return True
                    if control == "terminate":
                        return False
                    print("Unknown command. Use 'continue' or 'terminate'.")
            print("Unknown command. Use Enter, 'pause' or 'terminate'.")

    def _run_round(self, index: int, total: int, prize: Prize) -> None:
        assert self.lottery_manager is not None
        print("=" * 60)
        print(f"Round {index}/{total}: {prize.name}")
        print(f"Quantity: {prize.quantity}")
        print(f"Rule: {self._rule_description(prize)}")
        print(f"Eligible participants: {self.lottery_manager.count_eligible(prize)}")

        winners: list[User] = []
        for order in range(1, prize.quantity + 1):
            if not self._confirm_next(order):
                print("Round terminated; remaining winners for this prize are skipped.")
                break
            print(f"Currently drawing the {_ordinal(order)} winner...")
            user = self.lottery_manager.draw_one(prize)
            if user is None:
                print("No eligible participants remain for this prize.")
                break
            self.result_manager.add_winner(user, prize)
            winners.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        self.lottery_manager.end_round(prize, winners)
        print(f"Round finished: {len(winners)}/{prize.quantity} winner(s) drawn.")
        if winners:
            print("Round results:")
            for position, user in enumerate(winners, 1):
                print(f"  {position}. {user.name} ({user.department})")

    def _start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured. Load preset prizes or add custom prizes first.")
            return
        if self.lottery_done:
            answer = self._ask("A lottery has already run. Start over and discard previous results? (y/n): ").lower()
            if answer != "y":
                return
            self.result_manager = ResultManager()
        self.lottery_manager = LotteryManager(self.users)
        for index, prize in enumerate(prizes, 1):
            self._run_round(index, len(prizes), prize)
        self.lottery_done = True
        print("=" * 60)
        print("Lottery process completed.")
        self._show_summary()

    def _show_summary(self) -> None:
        prizes = self.prize_manager.get_prizes()
        grouped = self.result_manager.get_winners_by_prize(prizes)
        total = sum(len(winners) for winners in grouped.values())
        if total == 0:
            print("No winners yet.")
            return
        print("Winner summary (by prize level, then winning order):")
        for prize_name, winners in grouped.items():
            if not winners:
                continue
            print(f"[{prize_name}]")
            for winner in winners:
                print(
                    f"  {winner.winning_order}. {winner.user.name} "
                    f"({winner.user.department}) - {winner.prize.name}"
                )
        print(f"Total winners: {total}")

    def _export_winners(self) -> None:
        prizes = self.prize_manager.get_prizes()
        success, message = self.result_manager.export_to_csv(prizes)
        print(message)


def main() -> int:
    try:
        LotterySystemCLI().run()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting the lottery system.")
    return 0
