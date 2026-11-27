"""Winner tracking, grouping and CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A winning record linking a participant to a prize."""

    user: User
    prize: Prize
    order: int
    win_time: datetime = field(default_factory=datetime.now)

    @property
    def prize_name(self) -> str:
        return self.prize.name


class ResultManager:
    """Maintains the winner list and produces result views and exports."""

    EXPORT_PREFIX = "awards_result_"

    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._won_names: set[str] = set()

    def has_won(self, user: User) -> bool:
        return user.name in self._won_names

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner. A person can never win twice."""
        if self.has_won(user):
            raise ValueError(f"{user.name} has already won a prize.")
        winner = Winner(user=user, prize=prize, order=len(self._winners) + 1)
        self._winners.append(winner)
        self._won_names.add(user.name)
        return winner

    def get_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, following the given prize order."""
        result: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            result.setdefault(winner.prize_name, []).append(winner)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the complete winner list to awards_result_YYYYMMDD.txt in CSV format."""
        if not self._winners:
            return False, "No winners to export; nothing was exported."

        by_prize = self.get_winners_by_prize(prizes)
        file_name = f"{self.EXPORT_PREFIX}{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), file_name)
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize"])
                for winners in by_prize.values():
                    for winner in winners:
                        writer.writerow([winner.user.name, winner.user.department, winner.prize_name])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
