"""Winner recording, prize-level sorting and txt export."""
from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass, field
from datetime import datetime

from lottery_system.models import Prize, User

_LEVEL_KEYWORDS: tuple[tuple[str, int], ...] = (
    ("first", 1),
    ("second", 2),
    ("third", 3),
)
_LEVEL_LABELS: dict[int, str] = {1: "First", 2: "Second", 3: "Third"}
_OTHER_LEVEL = len(_LEVEL_KEYWORDS) + 1

EXPORT_HEADER: list[str] = [
    "Prize Level",
    "Prize Name",
    "Name",
    "Department",
    "Winning Order",
    "Win Time",
]


def prize_level(prize_name: str) -> int:
    """Return the level rank of a prize (1 = highest). Unknown levels rank last."""
    lowered = prize_name.casefold()
    for keyword, rank in _LEVEL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            return rank
    return _OTHER_LEVEL


def sort_prizes_by_level(prizes) -> list[Prize]:
    """Sort prizes from high level to low level, keeping sequence for ties."""
    return sorted(prizes, key=lambda prize: prize_level(prize.name))


@dataclass
class Winner:
    """A single winning record."""

    user: User
    prize: Prize
    winning_order: int
    win_time: datetime = field(default_factory=datetime.now)

    @property
    def prize_name(self) -> str:
        return self.prize.name


class ResultManager:
    """Maintains the winner list and produces summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        winner = Winner(user=user, prize=prize, winning_order=len(self._winners) + 1)
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes) -> dict:
        """Map prize name to its winners (winning order), prizes sorted high to low."""
        ordered = sort_prizes_by_level(prizes)
        result: dict[str, list[Winner]] = {prize.name: [] for prize in ordered}
        for winner in self._winners:
            if winner.prize.name in result:
                result[winner.prize.name].append(winner)
        return result

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        """Export all winners to ``awards_result_YYYYMMDD.txt`` in the current directory."""
        file_name = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), file_name)
        grouped = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(EXPORT_HEADER)
                for prize_name, winners in grouped.items():
                    level_label = _LEVEL_LABELS.get(prize_level(prize_name), "Other")
                    for winner in winners:
                        writer.writerow([
                            level_label,
                            prize_name,
                            winner.user.name,
                            winner.user.department,
                            winner.winning_order,
                            winner.win_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
