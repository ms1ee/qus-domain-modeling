"""Winner recording, grouped summaries and CSV/txt export."""

import csv
import datetime
import os
from dataclasses import dataclass

from lottery_system.models import Prize, User


@dataclass
class Winner:
    user: User
    prize: Prize
    winning_order: int
    winning_time: datetime.datetime

    @property
    def prize_name(self) -> str:
        return self.prize.name


class ResultManager:
    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._order_counter: int = 0

    def add_winner(self, user: User, prize: Prize) -> Winner:
        self._order_counter += 1
        winner = Winner(
            user=user,
            prize=prize,
            winning_order=self._order_counter,
            winning_time=datetime.datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Prize names ordered by level (high to low), then addition order.
        Winners within each prize are in winning time order."""
        ordered = sorted(prizes, key=lambda prize: prize.level)  # stable sort
        result: dict[str, list[Winner]] = {}
        for prize in ordered:
            result.setdefault(prize.name, [])
        for winner in self._winners:
            if winner.prize_name in result:
                result[winner.prize_name].append(winner)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        date_str = datetime.date.today().strftime("%Y%m%d")
        path = os.path.join(os.getcwd(), f"awards_result_{date_str}.txt")
        grouped = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winners in grouped.values():
                    for winner in winners:
                        writer.writerow([
                            winner.user.name,
                            winner.user.department,
                            winner.prize_name,
                            winner.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
