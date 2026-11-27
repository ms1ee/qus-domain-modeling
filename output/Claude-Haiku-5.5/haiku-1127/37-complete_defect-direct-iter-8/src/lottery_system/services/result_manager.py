"""Winner recording, grouping and CSV-style export."""

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from lottery_system.models import Prize, User


@dataclass(frozen=True)
class Winner:
    """A winning record."""

    user: User
    prize_name: str


class ResultManager:
    """Keeps all winners in winning order."""

    def __init__(self):
        self._winners: list[Winner] = []

    @property
    def winners(self) -> list[Winner]:
        return list(self._winners)

    def add_winner(self, user: User, prize: Prize) -> Winner:
        winner = Winner(user=user, prize_name=prize.name)
        self._winners.append(winner)
        return winner

    def get_winners_by_prize(self, prizes) -> dict:
        """Return {prize name: [Winner, ...]} for the given prizes, in prize order."""
        result: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize_name in result:
                result[winner.prize_name].append(winner)
        return result

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        """Export the complete winner list to current_dir/awards_result_YYYYMMDD.txt (CSV)."""
        grouped = self.get_winners_by_prize(prizes)
        rows = [winner for prize in prizes for winner in grouped.get(prize.name, [])]
        if not rows:
            return False, "No winners to export."

        path = Path.cwd() / f"awards_result_{date.today():%Y%m%d}.txt"
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["Name", "Department", "Prize"])
                for winner in rows:
                    writer.writerow([winner.user.name, winner.user.department, winner.prize_name])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
