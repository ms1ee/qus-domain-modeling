"""Winner recording, grouping and CSV-style export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User, normalize


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    prize_level: int
    winning_order: int
    winning_time: datetime


class ResultManager:
    """Stores all winners of the lottery session."""

    def __init__(self):
        self._winners: list[Winner] = []
        self._winner_keys: set[str] = set()

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner. Raises ValueError if the same person already won."""
        key = normalize(user.name)
        if key in self._winner_keys:
            raise ValueError(f"'{user.name}' has already won a prize")
        self._winner_keys.add(key)
        winner = Winner(
            user=user,
            prize_name=prize.name,
            prize_level=prize.level,
            winning_order=len(self._winners) + 1,
            winning_time=datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def count(self) -> int:
        return len(self._winners)

    def get_winners_by_prize(self, prizes) -> dict[str, list[Winner]]:
        """Group winners by prize name, ordered by prize level (high to low).

        Within each prize, winners are in winning time order.
        """
        ordered = sorted(prizes, key=lambda prize: prize.level)
        result: dict[str, list[Winner]] = {}
        for prize in ordered:
            if prize.name in result:
                continue
            result[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return result

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        """Export winners to 'awards_result_YYYYMMDD.txt' in the current directory, in CSV format."""
        winners_map = self.get_winners_by_prize(prizes)
        file_name = datetime.now().strftime("awards_result_%Y%m%d.txt")
        path = os.path.join(os.getcwd(), file_name)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize_name, winners in winners_map.items():
                    for winner in winners:
                        writer.writerow([
                            winner.user.name,
                            winner.user.department,
                            prize_name,
                            winner.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
