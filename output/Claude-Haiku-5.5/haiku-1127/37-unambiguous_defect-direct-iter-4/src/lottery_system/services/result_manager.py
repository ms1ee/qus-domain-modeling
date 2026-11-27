"""Winner recording, grouping, sorting and CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import date

from lottery_system.models import Prize, User

ORDINAL_LEVELS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
}


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    order: int  # global winning time order (1-based)


def prize_level_key(prize: Prize, index: int) -> tuple[int, int]:
    """Sort key: higher prize level (First > Second > Third) first, then configured order."""
    words = prize.name.strip().split()
    first_word = words[0].lower() if words else ""
    level = ORDINAL_LEVELS.get(first_word, len(ORDINAL_LEVELS) + 1)
    return level, index


def sort_prizes_by_level(prizes: list[Prize]) -> list[Prize]:
    """Return prizes ordered from highest prize level to lowest."""
    indexed = list(enumerate(prizes))
    indexed.sort(key=lambda item: prize_level_key(item[1], item[0]))
    return [prize for _, prize in indexed]


class ResultManager:
    """Keeps the winner list and produces summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize | str) -> Winner:
        prize_name = prize if isinstance(prize, str) else prize.name
        winner = Winner(user=user, prize_name=prize_name, order=len(self._winners) + 1)
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        """All winners in winning time order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Map prize name to its winners (winning time order).

        The dictionary is ordered from highest prize level to lowest.
        """
        result: dict[str, list[Winner]] = {}
        for prize in sort_prizes_by_level(prizes):
            result[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the complete winner list to current_dir/awards_result_YYYYMMDD.txt."""
        filename = f"awards_result_{date.today():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        grouped = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Prize", "Name", "Department", "Winning Order"])
                for prize_name, winners in grouped.items():
                    for winner in winners:
                        writer.writerow(
                            [
                                prize_name,
                                winner.user.name,
                                winner.user.department,
                                winner.order,
                            ]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
