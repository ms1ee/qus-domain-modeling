"""Winner recording, ordering, display grouping and CSV export."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from lottery_system.models import Prize, User

_LEVEL_PATTERN = re.compile(r"^\s*(First|Second|Third)\s+Prize\b", re.IGNORECASE)
_LEVEL_RANKS = {"first": 1, "second": 2, "third": 3}
_CUSTOM_RANK = 4


def prize_level_rank(prize_name: str) -> int:
    """Lower rank means higher level: First=1, Second=2, Third=3, others=4."""
    match = _LEVEL_PATTERN.match(prize_name or "")
    if match is None:
        return _CUSTOM_RANK
    return _LEVEL_RANKS[match.group(1).lower()]


@dataclass
class Winner:
    user: User
    prize: Prize
    won_at: datetime
    sequence: int

    @property
    def prize_name(self) -> str:
        return self.prize.name


class ResultManager:
    """Keeps the complete winner list in winning order."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        winner = Winner(
            user=user,
            prize=prize,
            won_at=datetime.now(),
            sequence=len(self._winners) + 1,
        )
        self._winners.append(winner)
        return winner

    def has_winners(self) -> bool:
        return bool(self._winners)

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    @staticmethod
    def _sorted_prizes(prizes: list[Prize]) -> list[Prize]:
        indexed = list(enumerate(prizes))
        indexed.sort(key=lambda item: (prize_level_rank(item[1].name), item[0]))
        return [prize for _, prize in indexed]

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Winners grouped by prize, levels ordered high to low, winning order within a prize."""
        result: dict[str, list[Winner]] = {}
        for prize in self._sorted_prizes(prizes):
            result[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export winners to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        if not self._winners:
            return False, "No winners to export."

        grouped = self.get_winners_by_prize(prizes)
        ordered: list[Winner] = []
        seen: set[int] = set()
        for winners in grouped.values():
            for winner in winners:
                ordered.append(winner)
                seen.add(id(winner))
        # Winners whose prize is not in the given list are still exported.
        for winner in self._winners:
            if id(winner) not in seen:
                ordered.append(winner)

        file_path = Path.cwd() / f"awards_result_{datetime.now():%Y%m%d}.txt"
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in ordered:
                    writer.writerow([
                        winner.user.name,
                        winner.user.department,
                        winner.prize_name,
                        winner.won_at.strftime("%Y-%m-%d %H:%M:%S"),
                    ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {file_path}"
