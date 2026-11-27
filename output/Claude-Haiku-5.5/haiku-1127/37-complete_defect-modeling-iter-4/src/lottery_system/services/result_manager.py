import csv
import os
from dataclasses import dataclass, field
from datetime import datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A winning record."""
    user: User
    prize_name: str = ""
    winning_order: int = 0
    won_at: datetime = field(default_factory=datetime.now)

    @property
    def name(self) -> str:
        return self.user.name

    @property
    def department(self) -> str:
        return self.user.department


class ResultManager:
    """Keeps winning records, groups them by prize and exports them."""

    def __init__(self):
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        if any(w.user.name == user.name for w in self._winners):
            raise ValueError(f"{user.name} has already won a prize.")
        winner = Winner(
            user=user,
            prize_name=prize.name,
            winning_order=len(self._winners) + 1,
            won_at=datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes) -> dict[str, list[Winner]]:
        result: dict[str, list[Winner]] = {}
        for prize in prizes:
            result.setdefault(prize.name, [])
        for winner in self._winners:
            if winner.prize_name in result:
                result[winner.prize_name].append(winner)
        return result

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        filename = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        by_prize = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize"])
                for prize in prizes:
                    for winner in by_prize.get(prize.name, []):
                        writer.writerow([winner.name, winner.department, winner.prize_name])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
