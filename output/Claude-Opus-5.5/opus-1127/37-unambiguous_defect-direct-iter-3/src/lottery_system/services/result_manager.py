"""Result management: collecting, ordering and exporting winners."""

import csv
import os
from datetime import datetime
from typing import Dict, List

from lottery_system.models import Prize, User

LEVEL_KEYWORDS = [
    ("grand", 0),
    ("special", 0),
    ("first", 1),
    ("second", 2),
    ("third", 3),
    ("fourth", 4),
    ("fifth", 5),
    ("consolation", 8),
]


def prize_level(name: str) -> int:
    low = (name or "").lower()
    for kw, lvl in LEVEL_KEYWORDS:
        if kw in low:
            return lvl
    return 9


class Winner:
    """A winning record."""

    def __init__(self, user: User, prize: Prize, order: int, timestamp=None) -> None:
        self.user = user
        self.prize = prize
        self.order = order
        self.timestamp = timestamp or datetime.now()

    def __repr__(self) -> str:
        return f"Winner({self.user!r}, {self.prize.name!r}, #{self.order})"


class ResultManager:
    """Stores winners and exports them."""

    def __init__(self) -> None:
        self.winners: List[Winner] = []
        self._counter = 0

    def add_winner(self, user: User, prize: Prize) -> Winner:
        self._counter += 1
        w = Winner(user, prize, self._counter)
        self.winners.append(w)
        return w

    def get_round_winners(self, prize: Prize) -> List[Winner]:
        return [w for w in self.winners if w.prize.name == prize.name]

    def _sorted_prizes(self, prizes) -> List[Prize]:
        prizes = list(prizes)
        known = {p.name for p in prizes}
        for w in self.winners:
            if w.prize.name not in known:
                prizes.append(w.prize)
                known.add(w.prize.name)
        indexed = list(enumerate(prizes))
        indexed.sort(key=lambda t: (prize_level(t[1].name), t[0]))
        return [p for _, p in indexed]

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in self._sorted_prizes(prizes):
            ws = [w for w in self.winners if w.prize.name == p.name]
            ws.sort(key=lambda w: (w.timestamp, w.order))
            result[p.name] = ws
        return result

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winners to export."
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["No", "Name", "Department", "Prize Name", "Winning Time"])
                no = 0
                for prize_name, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        no += 1
                        writer.writerow([
                            no,
                            w.user.name,
                            w.user.department,
                            prize_name,
                            w.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
