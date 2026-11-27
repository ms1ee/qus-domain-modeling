"""Winner recording, grouping and CSV-style export."""

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize: Prize
    winning_order: int = 0


class ResultManager:
    """Maintains the winner list and exports it."""

    def __init__(self):
        self._winners: list[Winner] = []

    def add_winner(self, user, prize) -> Winner:
        winner = Winner(user, prize, len(self._winners) + 1)
        self._winners.append(winner)
        return winner

    def get_winners_by_prize(self, prizes) -> dict:
        grouped: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            grouped.setdefault(winner.prize.name, []).append(winner)
        return grouped

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        date_str = datetime.now().strftime("%Y%m%d")
        path = os.path.join(os.getcwd(), f"awards_result_{date_str}.txt")
        grouped = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize"])
                for winners in grouped.values():
                    for winner in winners:
                        writer.writerow(
                            [winner.user.name, winner.user.department, winner.prize.name]
                        )
        except OSError as error:
            return False, f"Export failed: {error}"
        return True, f"Winner list successfully exported to {path}"
