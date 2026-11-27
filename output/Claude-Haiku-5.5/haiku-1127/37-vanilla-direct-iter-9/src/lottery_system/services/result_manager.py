"""Winner tracking, summary grouping and CSV export."""
import csv
import os
import re
from dataclasses import dataclass
from datetime import date, datetime

from lottery_system.config import CSV_HEADER, RESULT_FILE_PREFIX
from lottery_system.models import Prize, User

_LEVEL_WORDS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
}
_UNKNOWN_LEVEL = 1000


def prize_level_rank(name: str) -> int:
    """Lower rank means higher prize level. Unknown levels rank last."""
    match = re.match(r"\s*([A-Za-z]+)\b", name or "")
    if match:
        return _LEVEL_WORDS.get(match.group(1).lower(), _UNKNOWN_LEVEL)
    return _UNKNOWN_LEVEL


def _sort_prizes(prizes: list[Prize]) -> list[Prize]:
    indexed = list(enumerate(prizes))
    indexed.sort(key=lambda item: (prize_level_rank(item[1].name), item[0]))
    return [prize for _, prize in indexed]


@dataclass(frozen=True)
class Winner:
    user: User
    prize_name: str
    sequence: int
    timestamp: datetime


class ResultManager:
    """Stores winners in winning order and produces summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        prize_name = prize.name if isinstance(prize, Prize) else str(prize)
        winner = Winner(user, prize_name, len(self._winners) + 1, datetime.now())
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, ordered by prize level (high to low),
        and by winning order within each prize."""
        result: dict[str, list[Winner]] = {}
        for prize in _sort_prizes(prizes):
            winners = [w for w in self._winners if w.prize_name == prize.name]
            winners.sort(key=lambda w: w.sequence)
            result[prize.name] = winners
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt as CSV."""
        path = os.path.join(os.getcwd(), f"{RESULT_FILE_PREFIX}{date.today():%Y%m%d}.txt")
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(CSV_HEADER)
                for prize_name, winners in grouped.items():
                    for winner in winners:
                        writer.writerow([
                            winner.user.name,
                            winner.user.department,
                            prize_name,
                            winner.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
