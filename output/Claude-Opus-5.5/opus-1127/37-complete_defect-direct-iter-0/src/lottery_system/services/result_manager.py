"""Result management and export."""

import csv
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from lottery_system.models import Prize, User


@dataclass
class Winner:
    user: User
    prize_name: str
    order: int

    def __str__(self) -> str:
        return (f"Congratulations {self.user.name} ({self.user.department}) "
                f"for winning {self.prize_name}")


def _prize_name(prize) -> str:
    return prize.name if isinstance(prize, Prize) or hasattr(prize, "name") else str(prize)


class ResultManager:
    """Keeps the list of winners and exports it."""

    def __init__(self) -> None:
        self.winners: List[Winner] = []
        self._names = set()

    def add_winner(self, user: User, prize) -> Optional[Winner]:
        if user.name in self._names:
            return None
        w = Winner(user, _prize_name(prize), len(self.winners) + 1)
        self.winners.append(w)
        self._names.add(user.name)
        return w

    def has_winner(self, name: str) -> bool:
        return name in self._names

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in prizes or []:
            result[_prize_name(p)] = []
        for w in self.winners:
            result.setdefault(w.prize_name, []).append(w)
        return result

    def export_to_csv(self, prizes):
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize"])
                for prize_name, winners in grouped.items():
                    for w in winners:
                        writer.writerow([w.user.name, w.user.department, prize_name])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"

    def clear(self) -> None:
        self.winners = []
        self._names = set()
