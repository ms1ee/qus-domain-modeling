"""Winner recording, grouped retrieval and CSV export."""

import csv
import os
from dataclasses import dataclass
from datetime import date

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    draw_order: int


class ResultManager:
    """Keeps the complete winner list and exports it."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    @property
    def winners(self) -> list[Winner]:
        """All winners in the order they were drawn."""
        return list(self._winners)

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner for the given prize."""
        winner = Winner(user=user, prize_name=prize.name, draw_order=len(self._winners) + 1)
        self._winners.append(winner)
        return winner

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name. Every given prize appears as a key."""
        result: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize_name in result:
                result[winner.prize_name].append(winner)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to <cwd>/awards_result_YYYYMMDD.txt in CSV format."""
        if not self._winners:
            return False, "No winners to export."

        grouped = self.get_winners_by_prize(prizes)
        ordered = [winner for prize in prizes for winner in grouped.get(prize.name, [])]

        file_name = f"awards_result_{date.today().strftime('%Y%m%d')}.txt"
        file_path = os.path.join(os.getcwd(), file_name)
        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize"])
                for winner in ordered:
                    writer.writerow([winner.user.name, winner.user.department, winner.prize_name])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {file_path}"
