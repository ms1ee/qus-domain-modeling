"""Result recording, summarizing and exporting."""

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple

from lottery_system.models import Prize, User, prize_rank

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class Winner:
    user: User
    prize_name: str
    win_time: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return (f"Congratulations {self.user.name} ({self.user.department}) "
                f"for winning {self.prize_name}")


def _prize_name(prize) -> str:
    return prize.name if isinstance(prize, Prize) else str(prize)


class ResultManager:
    def __init__(self) -> None:
        self.winners: List[Winner] = []

    def add_winner(self, user, prize):
        if any(w.user.name == user.name for w in self.winners):
            return None
        winner = Winner(user, _prize_name(prize))
        self.winners.append(winner)
        return winner

    def get_round_winners(self, prize) -> List[Winner]:
        name = _prize_name(prize)
        return [w for w in self.winners if w.prize_name == name]

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        indexed = list(enumerate(prizes))
        indexed.sort(key=lambda t: (prize_rank(_prize_name(t[1])), t[0]))
        result: Dict[str, List[Winner]] = {}
        for _, prize in indexed:
            name = _prize_name(prize)
            items = [w for w in self.winners if w.prize_name == name]
            items.sort(key=lambda w: w.win_time)  # stable: keeps insertion order
            result[name] = items
        return result

    def export_to_csv(self, prizes) -> Tuple[bool, str]:
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for name, items in self.get_winners_by_prize(prizes).items():
                    for w in items:
                        writer.writerow([w.user.name, w.user.department, name,
                                         w.win_time.strftime(TIME_FORMAT)])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
