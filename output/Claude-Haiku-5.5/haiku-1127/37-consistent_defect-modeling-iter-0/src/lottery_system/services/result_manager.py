"""Winner recording, ordered summaries and CSV/txt export."""

import csv
import os
import re
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User

_LEVEL_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
_UNKNOWN_LEVEL = 99


def prize_level(prize: Prize) -> int:
    """Derive prize level from its name (First=1 is highest). Unknown levels sort last."""
    for word in re.findall(r"[a-zA-Z]+", prize.name.lower()):
        if word in _LEVEL_WORDS:
            return _LEVEL_WORDS[word]
    return _UNKNOWN_LEVEL


@dataclass
class Winner:
    user: User
    prize: Prize
    winning_time: datetime
    order_in_round: int


class ResultManager:
    """Stores winners in real time and produces ordered summaries."""

    TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user, prize) -> Winner:
        order = sum(1 for w in self._winners if w.prize.name == prize.name) + 1
        winner = Winner(user, prize, datetime.now(), order)
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes) -> dict[str, list[Winner]]:
        """Group winners by prize name, ordered by prize level (high to low),
        and by winning time within each prize."""
        ordered = sorted(prizes, key=prize_level)
        result: dict[str, list[Winner]] = {}
        for prize in ordered:
            if prize.name in result:
                continue
            winners = [w for w in self._winners if w.prize.name == prize.name]
            winners.sort(key=lambda w: w.winning_time)
            result[prize.name] = winners
        return result

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        """Export the complete winner list to current_dir/awards_result_YYYYMMDD.txt."""
        grouped = self.get_winners_by_prize(prizes)
        date_str = datetime.now().strftime("%Y%m%d")
        path = os.path.join(os.getcwd(), f"awards_result_{date_str}.txt")
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winners in grouped.values():
                    for w in winners:
                        writer.writerow([
                            w.user.name,
                            w.user.department,
                            w.prize.name,
                            w.winning_time.strftime(self.TIME_FORMAT),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Result successfully exported to {path}"
