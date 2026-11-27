"""Winner tracking, result grouping and CSV export."""

import csv
import os
import re
from dataclasses import dataclass
from datetime import date

from lottery_system.models import Prize, User

_LEVEL_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    sequence: int  # global winning order (1-based)


def prize_level(prize: Prize) -> int:
    """Return the level of a prize based on its name (1 = highest). Unlabeled prizes go last."""
    match = re.search(r"\b(first|second|third|fourth|fifth)\b", prize.name, re.IGNORECASE)
    if match:
        return _LEVEL_WORDS[match.group(1).lower()]
    return len(_LEVEL_WORDS) + 1


def sort_prizes_by_level(prizes: list[Prize]) -> list[Prize]:
    """Sort prizes from highest level to lowest; ties keep the lottery sequence order."""
    return sorted(prizes, key=prize_level)


class ResultManager:
    """Stores winners and produces result views and exports."""

    def __init__(self):
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        winner = Winner(user=user, prize_name=prize.name, sequence=len(self._winners) + 1)
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, in the order of the given prizes and winning time."""
        result: dict[str, list[Winner]] = {}
        for prize in prizes:
            result[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export winners to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        filename = f"awards_result_{date.today().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        sorted_prizes = sort_prizes_by_level(prizes)
        grouped = self.get_winners_by_prize(sorted_prizes)
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Prize Name", "Name", "Department", "Winning Order"])
                for prize in sorted_prizes:
                    for order, winner in enumerate(grouped.get(prize.name, []), start=1):
                        writer.writerow(
                            [prize.name, winner.user.name, winner.user.department, order]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
