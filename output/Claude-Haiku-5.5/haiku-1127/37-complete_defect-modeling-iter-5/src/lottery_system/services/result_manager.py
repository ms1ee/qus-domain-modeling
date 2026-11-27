"""Winner recording, grouping and CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    winning_order: int
    win_time: datetime = field(default_factory=datetime.now)


class ResultManager:
    """Stores winners and produces summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner for a prize."""
        prize_name = prize.name if isinstance(prize, Prize) else str(prize)
        winner = Winner(
            user=user,
            prize_name=prize_name,
            winning_order=len(self._winners) + 1,
        )
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        """All winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, following the given prize order."""
        grouped: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize_name in grouped:
                grouped[winner.prize_name].append(winner)
        return grouped

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the complete winner list to current_dir/awards_result_YYYYMMDD.txt as CSV."""
        path = os.path.join(os.getcwd(), f"awards_result_{datetime.now():%Y%m%d}.txt")
        grouped = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize"])
                for prize in prizes:
                    for winner in grouped.get(prize.name, []):
                        writer.writerow([winner.user.name, winner.user.department, winner.prize_name])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
