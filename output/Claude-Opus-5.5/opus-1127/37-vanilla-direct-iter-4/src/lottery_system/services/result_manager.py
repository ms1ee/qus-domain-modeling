"""Result storage, summary and export."""

import csv
import os
from datetime import datetime
from typing import Dict, List

LEVEL_KEYWORDS = [
    ("grand", 0),
    ("special", 0),
    ("first", 1),
    ("second", 2),
    ("third", 3),
    ("fourth", 4),
    ("fifth", 5),
    ("consolation", 6),
    ("participation", 7),
]
UNKNOWN_LEVEL = 100


class Winner:
    """A single winning record."""

    def __init__(self, user, prize, time=None) -> None:
        self.user = user
        self.prize = prize
        self.time = time or datetime.now()

    @property
    def prize_name(self) -> str:
        return self.prize.name if hasattr(self.prize, "name") else str(self.prize)

    def __repr__(self) -> str:
        return f"Winner({self.user!r}, {self.prize_name!r}, {self.time:%Y-%m-%d %H:%M:%S})"


def prize_level(name: str) -> int:
    lower = name.lower()
    for kw, level in LEVEL_KEYWORDS:
        if kw in lower:
            return level
    return UNKNOWN_LEVEL


class ResultManager:
    """Keeps winning records."""

    def __init__(self) -> None:
        self.winners: List[Winner] = []

    def add_winner(self, user, prize) -> Winner:
        winner = Winner(user, prize)
        self.winners.append(winner)
        return winner

    def _sorted_prize_names(self, prizes) -> List[str]:
        names: List[str] = []
        for p in prizes:
            n = p.name if hasattr(p, "name") else str(p)
            if n not in names:
                names.append(n)
        for w in self.winners:
            if w.prize_name not in names:
                names.append(w.prize_name)
        indexed = list(enumerate(names))
        indexed.sort(
            key=lambda t: (
                prize_level(t[1]),
                -t[0] if prize_level(t[1]) == UNKNOWN_LEVEL else t[0],
            )
        )
        return [n for _, n in indexed]

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for name in self._sorted_prize_names(prizes):
            ws = [w for w in self.winners if w.prize_name == name]
            ws.sort(key=lambda w: w.time)  # stable: keeps insertion order on ties
            result[name] = ws
        return result

    def export_to_csv(self, prizes):
        filename = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for name, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        writer.writerow(
                            [w.user.name, w.user.department, name,
                             w.time.strftime("%Y-%m-%d %H:%M:%S")]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
