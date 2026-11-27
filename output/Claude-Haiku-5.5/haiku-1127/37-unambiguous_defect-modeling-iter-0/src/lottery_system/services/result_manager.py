"""Winner recording, grouping and CSV-style export."""

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.constants import RESULT_DATE_FORMAT, RESULT_FILE_PREFIX
from lottery_system.models import Prize, User


@dataclass
class Winner:
    user: User
    prize_name: str
    level: int
    winning_order: int
    win_time: datetime


class ResultManager:
    def __init__(self):
        self._winners: list[Winner] = []
        self._counter = 0

    def add_winner(self, user, prize):
        self._counter += 1
        winner = Winner(
            user=user,
            prize_name=prize.name,
            level=prize.level,
            winning_order=self._counter,
            win_time=datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        return list(self._winners)

    def _ordered_winners(self, prizes=None) -> list[Winner]:
        winners = self._winners
        if prizes is not None:
            names = {p.name for p in prizes}
            winners = [w for w in winners if w.prize_name in names]
        return sorted(winners, key=lambda w: (w.level, w.winning_order))

    def get_winners_by_prize(self, prizes) -> dict[str, list[Winner]]:
        ordered_prizes = sorted(prizes, key=lambda p: p.level)
        result: dict[str, list[Winner]] = {}
        for prize in ordered_prizes:
            result[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return result

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        date_text = datetime.now().strftime(RESULT_DATE_FORMAT)
        path = os.path.join(os.getcwd(), f"{RESULT_FILE_PREFIX}{date_text}.txt")
        header = ["Prize Level", "Prize Name", "Winning Order", "Name", "Department", "Win Time"]
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(header)
                for winner in self._ordered_winners(prizes):
                    writer.writerow([
                        winner.level,
                        winner.prize_name,
                        winner.winning_order,
                        winner.user.name,
                        winner.user.department,
                        winner.win_time.strftime("%Y-%m-%d %H:%M:%S"),
                    ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
