"""Winner recording, grouping and CSV-style export."""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize: Prize
    winning_order: int
    winning_time: datetime

    @property
    def name(self) -> str:
        return self.user.name

    @property
    def department(self) -> str:
        return self.user.department


class ResultManager:
    """Keeps the complete ordered winner list for the event."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    @property
    def winners(self) -> list[Winner]:
        return list(self._winners)

    def add_winner(self, user: User, prize: Prize) -> Winner:
        winner = Winner(
            user=user,
            prize=prize,
            winning_order=len(self._winners) + 1,
            winning_time=datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name.

        Keys are ordered by prize level (high to low); ties keep the
        configured lottery order. Each list is in winning time order.
        """
        indexed = list(enumerate(prizes))
        indexed.sort(key=lambda item: (item[1].level, item[0]))
        result: dict[str, list[Winner]] = {}
        for _, prize in indexed:
            result[prize.name] = [
                w for w in self._winners if w.prize.name == prize.name
            ]
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to awards_result_YYYYMMDD.txt in the current directory."""
        grouped = self.get_winners_by_prize(prizes)
        level_map = {p.name: p.level for p in prizes}
        file_name = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), file_name)
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "Prize Level",
                        "Prize Name",
                        "Winning Order",
                        "Name",
                        "Department",
                        "Winning Time",
                    ]
                )
                for prize_name, winners in grouped.items():
                    for winner in winners:
                        writer.writerow(
                            [
                                level_map.get(prize_name, ""),
                                prize_name,
                                winner.winning_order,
                                winner.name,
                                winner.department,
                                winner.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                            ]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
