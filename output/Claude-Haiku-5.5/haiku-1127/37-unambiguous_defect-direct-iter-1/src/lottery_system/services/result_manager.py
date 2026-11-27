"""Winner recording, grouping, and export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import date

from lottery_system.models import Prize, User


@dataclass(frozen=True)
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    sequence: int


def _level_rank(prize_name: str) -> int:
    """Lower rank means higher prize level. Unrecognized names rank last."""
    lowered = prize_name.lower()
    for rank, keyword in enumerate(("first", "second", "third"), start=1):
        if keyword in lowered:
            return rank
    return 99


class ResultManager:
    """Keeps the complete list of winners for the current lottery."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._sequence = 0

    def add_winner(self, user: User, prize: Prize) -> None:
        self._sequence += 1
        self._winners.append(Winner(user=user, prize_name=prize.name, sequence=self._sequence))

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize, ordered by prize level (high to low),
        then by winning time within the same prize."""
        indexed = list(enumerate(prizes))
        indexed.sort(key=lambda item: (_level_rank(item[1].name), item[0]))
        result: dict[str, list[Winner]] = {}
        for _, prize in indexed:
            result[prize.name] = sorted(
                (winner for winner in self._winners if winner.prize_name == prize.name),
                key=lambda winner: winner.sequence,
            )
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        grouped = self.get_winners_by_prize(prizes)
        filename = f"awards_result_{date.today():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Prize Name", "Name", "Department", "Winning Order"])
                for prize_name, winners in grouped.items():
                    for order, winner in enumerate(winners, start=1):
                        writer.writerow(
                            [prize_name, winner.user.name, winner.user.department, order]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
