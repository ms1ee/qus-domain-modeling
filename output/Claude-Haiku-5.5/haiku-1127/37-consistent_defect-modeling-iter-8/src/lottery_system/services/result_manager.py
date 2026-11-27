"""Winner recording, grouping, ordering and CSV-style export."""

from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from datetime import date, datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    user: User
    prize_name: str
    prize_level: int
    sequence: int
    win_time: datetime


def ordered_prizes(prizes: list[Prize]) -> list[Prize]:
    """Prizes sorted by level from high to low; ties keep configured order."""
    indexed = sorted(enumerate(prizes), key=lambda item: (item[1].level, item[0]))
    return [prize for _, prize in indexed]


class ResultManager:
    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        winner = Winner(
            user=user,
            prize_name=prize.name,
            prize_level=prize.level,
            sequence=len(self._winners) + 1,
            win_time=datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        result: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize_name in result:
                result[winner.prize_name].append(winner)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        by_prize = self.get_winners_by_prize(prizes)
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
        for prize in ordered_prizes(prizes):
            for winner in by_prize.get(prize.name, []):
                writer.writerow(
                    [
                        winner.user.name,
                        winner.user.department,
                        prize.name,
                        winner.win_time.strftime("%Y-%m-%d %H:%M:%S"),
                    ]
                )
        file_name = f"awards_result_{date.today().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), file_name)
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(buffer.getvalue())
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
