"""Winner recording, grouping and CSV export."""

import csv
import io
import os
from dataclasses import dataclass
from datetime import datetime

from ..models import Prize, User

CSV_HEADER = ["Name", "Department", "Prize Name", "Winning Time"]


@dataclass
class Winner:
    user: User
    prize: Prize
    winning_time: datetime
    winning_order: int


def _sorted_prizes(prizes) -> list[Prize]:
    """Prize level from high to low; stable so addition order is kept within a level."""
    return sorted(prizes, key=lambda prize: prize.level)


class ResultManager:
    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._counter = 0

    def add_winner(self, user: User, prize: Prize) -> Winner:
        self._counter += 1
        winner = Winner(
            user=user,
            prize=prize,
            winning_time=datetime.now(),
            winning_order=self._counter,
        )
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes) -> dict[str, list[Winner]]:
        result: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize.name in result:
                result[winner.prize.name].append(winner)
        return result

    def get_ordered_winners(self, prizes) -> list[Winner]:
        """Winners ordered by prize level (high to low), then winning order."""
        by_prize = self.get_winners_by_prize(_sorted_prizes(prizes))
        ordered: list[Winner] = []
        for prize in _sorted_prizes(prizes):
            ordered.extend(by_prize.get(prize.name, []))
        return ordered

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        file_name = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), file_name)
        try:
            buffer = io.StringIO()
            writer = csv.writer(buffer, lineterminator="\n")
            writer.writerow(CSV_HEADER)
            for winner in self.get_ordered_winners(prizes):
                writer.writerow(
                    [
                        winner.user.name,
                        winner.user.department,
                        winner.prize.name,
                        winner.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                    ]
                )
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(buffer.getvalue())
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
