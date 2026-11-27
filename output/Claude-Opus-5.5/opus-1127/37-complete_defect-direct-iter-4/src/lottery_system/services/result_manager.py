"""Result management and export."""

import csv
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

from lottery_system.models import User


@dataclass
class Winner:
    user: User
    prize_name: str

    @property
    def name(self) -> str:
        return self.user.name

    @property
    def department(self) -> str:
        return self.user.department


def _prize_name(prize) -> str:
    return prize.name if hasattr(prize, "name") else str(prize)


class ResultManager:
    def __init__(self) -> None:
        self.winners: List[Winner] = []

    def add_winner(self, user: User, prize) -> Winner:
        w = Winner(user, _prize_name(prize))
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in prizes or []:
            result[_prize_name(p)] = []
        for w in self.winners:
            result.setdefault(w.prize_name, []).append(w)
        return result

    def export_to_csv(self, prizes) -> Tuple[bool, str]:
        if not self.winners:
            return False, "No winners to export"
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize"])
                for pname, winners in self.get_winners_by_prize(prizes).items():
                    for w in winners:
                        writer.writerow([w.user.name, w.user.department, pname])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
