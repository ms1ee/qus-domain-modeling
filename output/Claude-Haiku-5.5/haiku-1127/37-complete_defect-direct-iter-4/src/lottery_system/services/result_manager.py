"""Winner recording, grouping and CSV export."""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User


@dataclass(frozen=True)
class Winner:
    """A winning record."""

    user: User
    prize_name: str


class ResultManager:
    """Keeps the winner list in winning order and exports it."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> None:
        self._winners.append(Winner(user=user, prize_name=prize.name))

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        result: dict[str, list[Winner]] = {p.name: [] for p in prizes}
        for winner in self._winners:
            if winner.prize_name in result:
                result[winner.prize_name].append(winner)
        return result

    def export_to_csv(self, prizes: list[Prize], directory: str | None = None) -> tuple[bool, str]:
        """Export all winners as CSV into <directory>/awards_result_YYYYMMDD.txt.
        Defaults to the current working directory."""
        base_dir = directory or os.getcwd()
        filename = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(base_dir, filename)

        by_prize = self.get_winners_by_prize(prizes)
        rows: list[Winner] = []
        for prize in prizes:
            rows.extend(by_prize.get(prize.name, []))
        known = {p.name for p in prizes}
        rows.extend(w for w in self._winners if w.prize_name not in known)

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize"])
                for winner in rows:
                    writer.writerow([winner.user.name, winner.user.department, winner.prize_name])
        except OSError as exc:
            return False, f"Export failed: {exc}"

        return True, f"Winner list successfully exported to {path}"
