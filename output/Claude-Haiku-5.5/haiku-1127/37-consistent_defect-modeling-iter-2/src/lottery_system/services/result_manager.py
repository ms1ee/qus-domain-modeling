"""Winner recording, grouping, and CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A winning record: who won which prize, when, and in which order."""

    user: User
    prize: Prize
    winning_time: datetime
    winning_order: int


class ResultManager:
    """Stores winners and produces summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner. winning_order is the position within the same prize."""
        order = sum(1 for winner in self._winners if winner.prize.name == prize.name) + 1
        winner = Winner(user=user, prize=prize, winning_time=datetime.now(), winning_order=order)
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name (keys follow the given prize order)."""
        result: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize.name in result:
                result[winner.prize.name].append(winner)
        for winners in result.values():
            winners.sort(key=lambda item: item.winning_order)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export winners to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        if not self._winners:
            return False, "No winners to export."

        now = datetime.now()
        path = os.path.join(os.getcwd(), f"awards_result_{now:%Y%m%d}.txt")
        winners_by_prize = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize in sorted(prizes, key=lambda item: item.level):
                    for winner in winners_by_prize.get(prize.name, []):
                        writer.writerow([
                            winner.user.name,
                            winner.user.department,
                            winner.prize.name,
                            winner.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
