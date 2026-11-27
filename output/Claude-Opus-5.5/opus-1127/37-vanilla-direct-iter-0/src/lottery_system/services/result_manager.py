"""Result management: storage, summary and export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from lottery_system.models import Prize, User, prize_level

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class Winner:
    user: User
    prize_name: str
    time: datetime
    sequence: int

    @property
    def time_str(self) -> str:
        return self.time.strftime(TIME_FORMAT)


def _prize_name(prize) -> str:
    return prize.name if isinstance(prize, Prize) else str(prize)


class ResultManager:
    def __init__(self) -> None:
        self.winners: List[Winner] = []
        self._names = set()
        self._seq = 0

    def add_winner(self, user: User, prize):
        """Record a winner; returns the Winner, or None if already a winner."""
        if user.name in self._names:
            return None
        self._seq += 1
        winner = Winner(user, _prize_name(prize), datetime.now(), self._seq)
        self.winners.append(winner)
        self._names.add(user.name)
        return winner

    def has_won(self, name: str) -> bool:
        return name in self._names

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        names = []
        for p in prizes or []:
            n = _prize_name(p)
            if n not in names:
                names.append(n)
        for w in self.winners:
            if w.prize_name not in names:
                names.append(w.prize_name)
        ordered = sorted(enumerate(names), key=lambda t: (prize_level(t[1]), t[0]))
        result: Dict[str, List[Winner]] = {}
        for _, n in ordered:
            lst = [w for w in self.winners if w.prize_name == n]
            lst.sort(key=lambda w: (w.time, w.sequence))
            result[n] = lst
        return result

    def export_to_csv(self, prizes):
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize_name, winners in grouped.items():
                    for w in winners:
                        writer.writerow([w.user.name, w.user.department, prize_name, w.time_str])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
