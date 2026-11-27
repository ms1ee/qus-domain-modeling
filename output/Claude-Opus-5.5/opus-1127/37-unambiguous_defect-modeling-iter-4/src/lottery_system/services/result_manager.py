"""Result management: winner records, summaries and export."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Dict, List, Optional

from lottery_system.models import Prize, User

_LEVEL_KEYWORDS = [
    ("special", 0),
    ("grand", 0),
    ("first", 1),
    ("second", 2),
    ("third", 3),
    ("fourth", 4),
    ("fifth", 5),
    ("consolation", 90),
    ("participation", 91),
]


def prize_level_rank(name: str) -> int:
    lower = name.lower()
    for kw, rank in _LEVEL_KEYWORDS:
        if kw in lower:
            return rank
    return 50


def sort_prizes_by_level(prizes) -> List:
    indexed = list(enumerate(prizes))
    indexed.sort(key=lambda t: (prize_level_rank(_prize_name(t[1])), -t[0]))
    return [p for _, p in indexed]


def _prize_name(prize) -> str:
    return prize.name if hasattr(prize, "name") else str(prize)


class Winner:
    """A winning record."""

    def __init__(self, user: User, prize, order: int, win_time: Optional[datetime] = None):
        self.user = user
        self.prize = prize if isinstance(prize, Prize) else None
        self.prize_name = _prize_name(prize)
        self.order = order
        self.win_time = win_time or datetime.now()

    def __repr__(self) -> str:
        return f"Winner(user={self.user!r}, prize={self.prize_name!r}, order={self.order})"


class ResultManager:
    """Maintains the winner list in real time."""

    def __init__(self):
        self.winners: List[Winner] = []
        self._names = set()

    def has_won(self, name: str) -> bool:
        return name in self._names

    def add_winner(self, user, prize) -> bool:
        if user.name in self._names:
            return False
        self.winners.append(Winner(user, prize, len(self.winners) + 1))
        self._names.add(user.name)
        return True

    def get_winners(self) -> List[Winner]:
        return list(self.winners)

    def clear(self) -> None:
        self.winners.clear()
        self._names.clear()

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for prize in sort_prizes_by_level(list(prizes or [])):
            result[_prize_name(prize)] = []
        extra: Dict[str, List[Winner]] = {}
        for w in sorted(self.winners, key=lambda x: (x.win_time, x.order)):
            if w.prize_name in result:
                result[w.prize_name].append(w)
            else:
                extra.setdefault(w.prize_name, []).append(w)
        result.update(extra)
        return result

    def export_to_csv(self, prizes, directory: Optional[str] = None):
        if not self.winners:
            return False, "No winners to export"
        directory = directory or os.getcwd()
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(directory, filename)
        grouped = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["No", "Name", "Department", "Prize", "Winning Order", "Winning Time"])
                no = 1
                for prize_name, winners in grouped.items():
                    for w in winners:
                        writer.writerow([
                            no,
                            w.user.name,
                            w.user.department,
                            prize_name,
                            w.order,
                            w.win_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ])
                        no += 1
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
