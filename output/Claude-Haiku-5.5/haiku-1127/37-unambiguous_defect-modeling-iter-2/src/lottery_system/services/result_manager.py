"""Winner recording, grouping, sorting and CSV-style export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User


def prize_level(name: str) -> int:
    """Prize level for sorting: First=1 (highest), Second=2, Third=3, others last."""
    lowered = (name or "").strip().casefold()
    for keyword, level in (("first", 1), ("second", 2), ("third", 3)):
        if lowered.startswith(keyword):
            return level
    return 99


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize: Prize
    winning_order: int
    win_time: datetime

    @property
    def prize_name(self) -> str:
        return self.prize.name


class ResultManager:
    """Keeps the complete winner list of the lottery."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        winner = Winner(
            user=user,
            prize=prize,
            winning_order=len(self._winners) + 1,
            win_time=datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        """All winners in global winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Winners grouped by prize name, each list in winning order."""
        grouped: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            grouped.setdefault(winner.prize.name, []).append(winner)
        return grouped

    def get_sorted_winners(self, prizes: list[Prize]) -> list[Winner]:
        """Winners sorted by prize level (high to low), then prize order, then winning order."""
        index = {prize.name: pos for pos, prize in enumerate(prizes)}
        return sorted(
            self._winners,
            key=lambda w: (
                prize_level(w.prize.name),
                index.get(w.prize.name, len(index)),
                w.winning_order,
            ),
        )

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt as CSV."""
        now = datetime.now()
        path = os.path.join(os.getcwd(), f"awards_result_{now.strftime('%Y%m%d')}.txt")
        header = [
            "Prize Level",
            "Prize Name",
            "Winning Order",
            "Name",
            "Department",
            "Win Time",
        ]
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(header)
                for winner in self.get_sorted_winners(prizes):
                    level = prize_level(winner.prize.name)
                    writer.writerow(
                        [
                            level if level != 99 else "",
                            winner.prize.name,
                            winner.winning_order,
                            winner.user.name,
                            winner.user.department,
                            winner.win_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
