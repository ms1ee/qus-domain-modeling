"""Winner recording, grouping and CSV export."""

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User, normalize


@dataclass
class Winner:
    """A winning record: who won which prize."""

    user: User
    prize: Prize


class ResultManager:
    """Keeps the winner list and exports it."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._winner_keys: set[str] = set()

    def add_winner(self, user: User, prize: Prize) -> bool:
        """Record a winner. Returns False if this person already won."""
        key = normalize(user.name)
        if key in self._winner_keys:
            return False
        self._winner_keys.add(key)
        self._winners.append(Winner(user, prize))
        return True

    def get_all_winners(self) -> list[Winner]:
        """All winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Map each prize name to its winners (in winning order)."""
        result: dict[str, list[Winner]] = {}
        for prize in prizes:
            result[prize.name] = [w for w in self._winners if w.prize.name == prize.name]
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to awards_result_YYYYMMDD.txt in the current
        directory, formatted as CSV. Returns (success, message)."""
        today = datetime.now().strftime("%Y%m%d")
        path = os.path.join(os.getcwd(), f"awards_result_{today}.txt")
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["Name", "Department", "Prize"])
                for prize in prizes:
                    for winner in grouped.get(prize.name, []):
                        writer.writerow([winner.user.name, winner.user.department, prize.name])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
