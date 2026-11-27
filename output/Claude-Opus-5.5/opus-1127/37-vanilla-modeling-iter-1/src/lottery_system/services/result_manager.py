"""Result storage, summarizing and export."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List, Tuple

from lottery_system.models import Prize, User


class Winner:
    """A winning record."""

    def __init__(self, user: User, prize: Prize, order: int, win_time: datetime = None) -> None:
        self.user = user
        self.prize = prize
        self.order = order
        self.win_time = win_time or datetime.now()

    @property
    def prize_name(self) -> str:
        return self.prize.name if isinstance(self.prize, Prize) else str(self.prize)

    def __repr__(self) -> str:
        return f"Winner({self.user.name}, {self.user.department}, {self.prize_name})"


class ResultManager:
    """Maintains the winner list."""

    def __init__(self) -> None:
        self.winners: List[Winner] = []

    def add_winner(self, user, prize) -> Winner:
        winner = Winner(user, prize, len(self.winners) + 1)
        self.winners.append(winner)
        return winner

    @staticmethod
    def _sorted_prizes(prizes) -> List[Prize]:
        indexed = list(enumerate(prizes or []))
        indexed.sort(key=lambda t: (getattr(t[1], "level", 100) or 0, t[0]))
        return [p for _, p in indexed]

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for prize in self._sorted_prizes(prizes):
            result.setdefault(prize.name, [])
        for w in sorted(self.winners, key=lambda w: (w.win_time, w.order)):
            result.setdefault(w.prize_name, []).append(w)
        return result

    def export_to_csv(self, prizes) -> Tuple[bool, str]:
        if not self.winners:
            return False, "No winners to export"
        path = os.path.join(os.getcwd(), f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt")
        try:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write("Name,Department,Prize Name,Winning Time\n")
                for _, lst in self.get_winners_by_prize(prizes).items():
                    for w in lst:
                        fh.write(
                            f"{w.user.name},{w.user.department},{w.prize_name},"
                            f"{w.win_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
