"""Winner recording, grouping and CSV export."""

from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from datetime import datetime

from ..models import Prize, User


@dataclass
class Winner:
    """A winning record: the winner and the name of the prize won."""

    user: User
    prize_name: str


class ResultManager:
    """Keeps the list of winners and produces summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> None:
        prize_name = getattr(prize, "name", prize)
        self._winners.append(Winner(user=user, prize_name=str(prize_name)))

    def get_winners(self) -> list[Winner]:
        """All winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Map each prize name (in the given order) to its winners."""
        result: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize_name in result:
                result[winner.prize_name].append(winner)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list as CSV into the current directory."""
        try:
            grouped = self.get_winners_by_prize(prizes)
            buffer = io.StringIO()
            writer = csv.writer(buffer, lineterminator="\n")
            writer.writerow(["Name", "Department", "Prize"])
            for prize in prizes:
                for winner in grouped.get(prize.name, []):
                    writer.writerow([winner.user.name, winner.user.department, winner.prize_name])

            file_name = f"awards_result_{datetime.now():%Y%m%d}.txt"
            path = os.path.join(os.getcwd(), file_name)
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(buffer.getvalue())
            return True, f"Results successfully exported to {path}"
        except OSError as exc:
            return False, f"Export failed: {exc}"
