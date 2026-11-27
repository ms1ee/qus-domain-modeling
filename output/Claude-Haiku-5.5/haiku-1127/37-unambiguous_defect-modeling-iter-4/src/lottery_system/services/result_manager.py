"""Winner tracking, grouping, sorting and CSV-style export."""

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
    prize: Prize
    winning_order: int = 0
    win_time: datetime = field(default_factory=datetime.now)


class ResultManager:
    """Stores winners and produces summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a new winner with the next global winning order."""
        winner = Winner(user=user, prize=prize, winning_order=len(self._winners) + 1)
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, keeping winning time order."""
        result: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize.name in result:
                result[winner.prize.name].append(winner)
        return result

    def get_sorted_winners(self, prizes: list[Prize]) -> list[Winner]:
        """Sort winners by prize level (high to low), then prize order, then winning order."""
        position = {prize.name: index for index, prize in enumerate(prizes)}
        fallback = len(position)
        return sorted(
            self._winners,
            key=lambda w: (-w.prize.level, position.get(w.prize.name, fallback), w.winning_order),
        )

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the sorted winner list to awards_result_YYYYMMDD.txt in the current directory."""
        if not self._winners:
            return False, "No winners to export."

        file_name = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), file_name)
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    ["Prize Level", "Prize Name", "Winning Order", "Name", "Department", "Win Time"]
                )
                for winner in self.get_sorted_winners(prizes):
                    writer.writerow(
                        [
                            winner.prize.level,
                            winner.prize.name,
                            winner.winning_order,
                            winner.user.name,
                            winner.user.department,
                            winner.win_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Result successfully exported to {path}"
