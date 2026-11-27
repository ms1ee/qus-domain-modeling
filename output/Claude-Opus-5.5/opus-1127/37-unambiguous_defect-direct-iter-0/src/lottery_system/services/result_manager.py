"""Result management and export."""

import csv
import os
from datetime import datetime
from typing import Dict, List

from lottery_system.models import Prize, User, prize_level


class Winner:
    def __init__(self, user: User, prize: Prize, order: int, time: datetime):
        self.user = user
        self.prize = prize
        self.order = order
        self.time = time

    def __repr__(self):
        return f"Winner({self.user.name!r}, {self.prize.name!r}, #{self.order})"


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []
        self._counter = 0

    def add_winner(self, user, prize) -> bool:
        if any(w.user.name.lower() == user.name.lower() for w in self.winners):
            return False
        self._counter += 1
        self.winners.append(Winner(user, prize, self._counter, datetime.now()))
        return True

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        prize_list = list(prizes or [])
        names = [p.name for p in prize_list]
        for w in self.winners:
            if w.prize.name not in names:
                names.append(w.prize.name)
        indexed = list(enumerate(names))
        indexed.sort(key=lambda t: (prize_level(t[1]), t[0]))
        result: Dict[str, List[Winner]] = {}
        for _, name in indexed:
            result[name] = sorted(
                [w for w in self.winners if w.prize.name == name], key=lambda w: w.order
            )
        return result

    def export_to_csv(self, prizes):
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Order", "Winning Time"])
                for prize_name, winners in grouped.items():
                    for w in winners:
                        writer.writerow([
                            w.user.name,
                            w.user.department,
                            prize_name,
                            w.order,
                            w.time.strftime("%Y-%m-%d %H:%M:%S"),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
