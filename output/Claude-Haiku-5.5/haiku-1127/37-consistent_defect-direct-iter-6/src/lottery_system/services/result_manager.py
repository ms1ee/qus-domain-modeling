"""Winner recording, grouping by prize level, and CSV export."""

from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User

_UNRANKED_LEVEL = 99
_CSV_HEADER = ["Name", "Department", "Prize Name", "Winning Time"]


@dataclass
class Winner:
    """A recorded winning result."""

    user: User
    prize_name: str
    sequence: int
    won_at: datetime


def prize_level_rank(name: str) -> int:
    """Return the level rank of a prize (First=1, Second=2, Third=3)."""
    lowered = name.lower()
    for rank, keyword in enumerate(("first", "second", "third"), start=1):
        if keyword in lowered:
            return rank
    return _UNRANKED_LEVEL


class ResultManager:
    """Keeps the winner list and produces summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize | str) -> Winner:
        """Record a winner in winning order and return the record."""
        prize_name = prize.name if isinstance(prize, Prize) else str(prize)
        winner = Winner(
            user=user,
            prize_name=prize_name,
            sequence=len(self._winners) + 1,
            won_at=datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, ordered from high to low prize level.

        Within each prize, winners are in winning time order.
        """
        ordered = sorted(prizes, key=lambda p: prize_level_rank(p.name))
        result: dict[str, list[Winner]] = {}
        for prize in ordered:
            result[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        path = os.path.join(os.getcwd(), f"awards_result_{datetime.now():%Y%m%d}.txt")
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(_CSV_HEADER)
        grouped = self.get_winners_by_prize(prizes)
        for prize_name, winners in grouped.items():
            for winner in winners:
                writer.writerow(
                    [
                        winner.user.name,
                        winner.user.department,
                        prize_name,
                        f"{winner.won_at:%Y-%m-%d %H:%M:%S}",
                    ]
                )
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(buffer.getvalue())
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
