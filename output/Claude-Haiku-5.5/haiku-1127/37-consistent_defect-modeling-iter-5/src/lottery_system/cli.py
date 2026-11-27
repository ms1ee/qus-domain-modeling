"""Command-line interface: menus, list/prize configuration, lottery process control and results."""
from lottery_system.input_reader import InputReader
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager, describe_rules
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

DEFAULT_DRAW_INTERVAL = 1.5


def ordinal(number):
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryApp:
    def __init__(self, reader=None, draw_interval=DEFAULT_DRAW_INTERVAL):
        self.reader = reader if reader is not None else InputReader()
        self.draw_interval = draw_interval
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users = []
        self.last_results = None
        self.last_prizes = None

    # ------------------------------------------------------------------ main loop
    def run(self):
        self.reader.start()
        print("=== Company Team Building Smart Lottery System ===")
        try:
            while True:
                self._print_main_menu()
                choice = self.reader.read_line("Select an option: ")
                if choice == "1":
                    self._load_default_list()
                elif choice == "2":
                    self._upload_custom_list()
                elif choice == "3":
                    self._show_groups()
                elif choice == "4":
                    self._prize_menu()
                elif choice == "5":
                    self._start_lottery()
                elif choice == "6":
                    self._export_results()
                elif choice == "0":
                    break
                else:
                    print("Invalid option, please try again.")
        except EOFError:
            print("\nInput closed. Exiting.")
        print("Goodbye!")

    def _print_main_menu(self):
        print("\n----- Main Menu -----")
        print("1. Load built-in team building list")
        print("2. Upload custom participant list (txt)")
        print("3. View department groups and member counts")
        print("4. Prize configuration")
        print("5. Start lottery")
        print("6. Export winner list")
        print("0. Exit")

    # ------------------------------------------------------------ list management
    def _load_default_list(self):
        users, errors = self.list_manager.load_default_list()
        self._finalize_list(users, errors)

    def _upload_custom_list(self):
        path = self.reader.read_line("Enter the path of the txt file: ").strip().strip('"')
        if not path:
            print("Upload cancelled.")
            return
        users, errors = self.list_manager.load_custom_list(path)
        self._finalize_list(users, errors)

    def _finalize_list(self, users, errors):
        if errors:
            print(f"{len(errors)} problem(s) found in the list:")
            for error in errors:
                print(f"  {error}")

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print(f"{len(duplicates)} duplicate name(s) found:")
            for user in duplicates:
                print(f"  Duplicate: {user.name} ({user.department})")

        if not valid and not errors and not duplicates:
            print("The list contains no participants; nothing was loaded.")
            return

        if errors or duplicates:
            print("How do you want to handle the invalid data?")
            print("  1. remove     - discard invalid lines and duplicate names, keep the rest")
            print("  2. manual     - keep the rest and manually remove specific names")
            print("  3. terminate  - abort the upload")
            while True:
                choice = self.reader.read_line("Enter 1/2/3: ").strip().lower()
                if choice in ("1", "remove"):
                    break
                if choice in ("2", "manual"):
                    valid = self._manual_remove(valid)
                    break
                if choice in ("3", "terminate"):
                    print("Upload terminated; the participant list is unchanged.")
                    return
                print("Please enter 1, 2 or 3.")

        if not valid:
            print("No participants left after removal; nothing was loaded.")
            return

        self.users = valid
        print(f"Loaded {len(valid)} participants.")
        self._show_groups()

    def _manual_remove(self, users):
        current = list(users)
        print("Enter a name to remove, or press Enter to finish.")
        while True:
            name = self.reader.read_line("Remove name: ").strip()
            if not name:
                break
            before = len(current)
            current = [user for user in current if user.name != name]
            removed = before - len(current)
            if removed:
                print(f"Removed {removed} entry(ies) for {name}.")
            else:
                print("No participant with that name.")
        return current

    def _show_groups(self):
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Department groups:")
        for department, count in info.items():
            print(f"  {department}: {count} people")
        print(f"Total participants: {len(self.users)}")

    def _group_names(self):
        if not self.users:
            return []
        return list(self.list_manager.get_group_info(self.users).keys())

    def _parse_groups(self, text, groups):
        result = []
        for token in [t.strip() for t in text.split(",") if t.strip()]:
            if token.isdigit() and 1 <= int(token) <= len(groups):
                name = groups[int(token) - 1]
            else:
                name = token
            if name not in result:
                result.append(name)
        return result

    # ------------------------------------------------------------ prize configuration
    def _prize_menu(self):
        while True:
            self._print_prizes()
            print("\n----- Prize Configuration -----")
            print("1. Load preset prize library")
            print("2. Add custom prize")
            print("3. Set avoidance groups for a prize")
            print("4. Set associated lottery person for a prize")
            print("5. Reorder lottery sequence")
            print("0. Back")
            choice = self.reader.read_line("Select an option: ")
            if choice == "1":
                self._load_presets()
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._set_avoid_groups()
            elif choice == "4":
                self._set_drawer()
            elif choice == "5":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")

    def _print_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("\nNo prizes configured yet.")
            return
        print("\nCurrent lottery sequence:")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) or "none"
            drawer = prize.associated_drawer or "none"
            print(f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                  f"avoid groups: {avoid} | lottery person: {drawer}")

    def _load_presets(self):
        errors = self.prize_manager.load_default_prizes()
        if errors:
            for error in errors:
                print(error)
        else:
            print("Preset prizes loaded.")

    def _ask_positive_int(self, prompt):
        while True:
            text = self.reader.read_line(prompt).strip()
            try:
                value = int(text)
                if value > 0:
                    return value
            except ValueError:
                pass
            print("Please enter a positive integer.")

    def _add_custom_prize(self):
        name = self.reader.read_line("Prize name: ").strip()
        if not name:
            print("Prize creation cancelled.")
            return
        quantity = self._ask_positive_int("Quantity: ")
        drawer = self.reader.read_line("Associated lottery person (Enter to skip): ").strip() or None
        groups = self._group_names()
        avoid = []
        if groups:
            print("Department groups:")
            for index, group in enumerate(groups, start=1):
                print(f"  {index}. {group}")
            text = self.reader.read_line(
                "Avoidance groups (numbers or names, comma-separated; Enter to skip): ")
            avoid = self._parse_groups(text, groups)
        try:
            prize = self.prize_manager.add_prize(name, quantity, avoid, drawer)
            print(f"Prize added: {prize.name}")
        except ValueError as exc:
            print(f"Failed to add prize: {exc}")

    def _select_prize(self, prompt):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured yet.")
            return None
        text = self.reader.read_line(prompt).strip()
        if text.isdigit() and 1 <= int(text) <= len(prizes):
            return int(text) - 1
        print("Invalid prize number.")
        return None

    def _set_avoid_groups(self):
        index = self._select_prize("Select prize number: ")
        if index is None:
            return
        groups = self._group_names()
        if groups:
            print("Department groups:")
            for number, group in enumerate(groups, start=1):
                print(f"  {number}. {group}")
        text = self.reader.read_line(
            "Avoidance groups (numbers or names, comma-separated; Enter to clear): ")
        self.prize_manager.set_avoid_groups(index, self._parse_groups(text, groups))
        print("Avoidance groups updated.")

    def _set_drawer(self):
        index = self._select_prize("Select prize number: ")
        if index is None:
            return
        drawer = self.reader.read_line("Associated lottery person (Enter to clear): ").strip()
        self.prize_manager.set_associated_drawer(index, drawer or None)
        print("Associated lottery person updated.")

    def _reorder_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured yet.")
            return
        count = len(prizes)
        text = self.reader.read_line(
            f"Enter the new order as serial numbers separated by spaces (1-{count}): ")
        try:
            order = [int(token) for token in text.split()]
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery sequence updated.")
            self._print_prizes()
        else:
            print(f"Invalid order: each serial number from 1 to {count} must appear exactly once.")

    # ------------------------------------------------------------ lottery process
    def _start_lottery(self):
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return

        lottery = LotteryManager(self.users)
        results = ResultManager()
        print("\nLottery starting. During the draw you may type: pause / continue / terminate")
        for round_no, prize in enumerate(prizes, start=1):
            print(f"\n=== Round {round_no}: {prize.name} ===")
            print(f"Quantity: {prize.quantity}")
            print(f"Rules: {describe_rules(prize)}")
            round_winners = self._run_round(lottery, results, prize)
            print(f"--- Round {round_no} results ---")
            if not round_winners:
                print("  No winners in this round.")
            for winner in round_winners:
                print(f"  {winner.winning_order}. {winner.user.name} ({winner.user.department})")

        self.last_results = results
        self.last_prizes = prizes
        self._print_summary(results, prizes)

    def _run_round(self, lottery, results, prize):
        winners = []
        drawn = 0
        while drawn < prize.quantity:
            command = self.reader.poll(self.draw_interval)
            if command == "pause":
                if self._wait_while_paused() == "terminate":
                    print("Round terminated. Remaining draws for this prize are skipped.")
                    break
            elif command == "terminate":
                print("Round terminated. Remaining draws for this prize are skipped.")
                break
            elif command == "continue":
                print("Lottery is not paused.")

            print(f"Currently drawing the {ordinal(drawn + 1)} winner...")
            user = lottery.draw_one(prize)
            if user is None:
                print("No eligible participants remain for this prize; the round ends early.")
                break
            drawn += 1
            winner = results.add_winner(user, prize)
            winners.append(winner)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")
        return winners

    def _wait_while_paused(self):
        print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
        while True:
            command = self.reader.read_line("").strip().lower()
            if command == "continue":
                print("Lottery resumed.")
                return "continue"
            if command == "terminate":
                return "terminate"
            print("Type 'continue' or 'terminate'.")

    def _print_summary(self, results, prizes):
        print("\n=== Final winner list (prize level from high to low) ===")
        for prize_name, winners in results.get_winners_by_prize(prizes).items():
            print(f"{prize_name}:")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(f"  {winner.winning_order}. {winner.user.name} ({winner.user.department})")

    # ------------------------------------------------------------ export
    def _export_results(self):
        if self.last_results is None:
            print("No lottery has been run yet.")
            return
        _, message = self.last_results.export_to_csv(self.last_prizes)
        print(message)


def main():
    app = LotteryApp()
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
