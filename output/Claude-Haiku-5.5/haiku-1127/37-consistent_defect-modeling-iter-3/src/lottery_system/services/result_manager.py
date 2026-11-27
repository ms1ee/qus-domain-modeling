"""Winner recording, result summarization and CSV export."""

from __future__ import annotations

import csv
import datetime
import io
import os
from dataclasses import dataclass

from lottery_system.models import Prize, User

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    prize_level: int
    winning_order: int
    winning_time: datetime.datetime


class ResultManager:
    """Maintains the winner list in real time and exports it."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._won_names: set[str] = set()

    def add_winner(self, user: User, prize: Prize) -> Winner:
        key = user.name.strip().casefold()
        if key in self._won_names:
            raise ValueError(f"{user.name} has already won a prize.")
        winner = Winner(
            user=user,
            prize_name=prize.name,
            prize_level=prize.level,
            winning_order=len(self._winners) + 1,
            winning_time=datetime.datetime.now(),
        )
        self._winners.append(winner)
        self._won_names.add(key)
        return winner

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Map prize name -> winners in winning time order."""
        return {
            prize.name: [w for w in self._winners if w.prize_name == prize.name]
            for prize in prizes
        }

    def get_sorted_winners(self, prizes: list[Prize]) -> list[Winner]:
        """Winners ordered by prize level (high to low), then winning order."""
        by_prize = self.get_winners_by_prize(prizes)
        ordered_prizes = sorted(prizes, key=lambda prize: prize.level)
        result: list[Winner] = []
        for prize in ordered_prizes:
            result.extend(sorted(by_prize[prize.name], key=lambda w: w.winning_order))
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export winners to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        winners = self.get_sorted_winners(prizes)
        if not winners:
            return False, "No winners to export."

        now = datetime.datetime.now()
        path = os.path.join(os.getcwd(), f"awards_result_{now:%Y%m%d}.txt")

        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
        for winner in winners:
            writer.writerow(
                [
                    winner.user.name,
                    winner.user.department,
                    winner.prize_name,
                    winner.winning_time.strftime(TIME_FORMAT),
                ]
            )

        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as handle:
                handle.write(buffer.getvalue())
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
