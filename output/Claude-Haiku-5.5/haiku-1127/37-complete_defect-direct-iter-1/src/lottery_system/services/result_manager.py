"""Winner recording, grouping and CSV export."""

import csv
import os
from dataclasses import dataclass
from datetime import date

from lottery_system.models import User


@dataclass(frozen=True)
class Winner:
    """A winning participant together with the prize name they won."""

    user: User
    prize_name: str


class ResultManager:
    """Stores winners in winning order and produces reports."""

    def __init__(self):
        self._winners: list[Winner] = []

    def add_winner(self, user, prize):
        """Record that user won the given prize."""
        self._winners.append(Winner(user, prize.name))

    def winner_names(self) -> set[str]:
        """Return the set of names of everyone who has won so far."""
        return {winner.user.name for winner in self._winners}

    def all_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes) -> dict:
        """Map each prize name to the list of its winners."""
        grouped: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize_name in grouped:
                grouped[winner.prize_name].append(winner)
        return grouped

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        """Export the complete winner list as CSV into awards_result_YYYYMMDD.txt."""
        grouped = self.get_winners_by_prize(prizes)
        rows: list[list[str]] = []
        for prize in prizes:
            for winner in grouped.get(prize.name, []):
                rows.append([winner.user.name, winner.user.department, winner.prize_name])
        known = {prize.name for prize in prizes}
        for winner in self._winners:
            if winner.prize_name not in known:
                rows.append([winner.user.name, winner.user.department, winner.prize_name])

        if not rows:
            return False, "No winners to export."

        filename = f"awards_result_{date.today():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize"])
                writer.writerows(rows)
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
