"""Winner recording, grouping and CSV-style export."""

import csv
import os
from dataclasses import dataclass
from datetime import date

from lottery_system.models import Prize, User


@dataclass(frozen=True)
class Winner:
    """A winning record."""

    user: User
    prize_name: str


class ResultManager:
    """Maintains the real-time winner list."""

    def __init__(self):
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> None:
        """Record a winner. Raises ValueError if the person has already won."""
        if user.name in self.winner_names():
            raise ValueError(f"{user.name} has already won a prize.")
        self._winners.append(Winner(user, prize.name))

    def winner_names(self) -> set[str]:
        """Names of everyone who has won so far."""
        return {winner.user.name for winner in self._winners}

    def get_all_winners(self) -> list[Winner]:
        """All winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, keeping the order of `prizes`."""
        result: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize_name in result:
                result[winner.prize_name].append(winner)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export winners to ./awards_result_YYYYMMDD.txt in CSV format."""
        path = os.path.join(
            os.getcwd(), f"awards_result_{date.today().strftime('%Y%m%d')}.txt"
        )
        grouped = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize"])
                for prize in prizes:
                    for winner in grouped[prize.name]:
                        writer.writerow(
                            [winner.user.name, winner.user.department, winner.prize_name]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
