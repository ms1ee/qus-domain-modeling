"""Winner records, summary and export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from lottery_system.models import Prize, User


@dataclass
class Winner:
    user: User
    prize: Prize
    draw_order: int
    win_time: datetime = field(default_factory=datetime.now)


class ResultManager:
    def __init__(self) -> None:
        self.winners: List[Winner] = []
        self._counter = 0

    @property
    def total_winners(self) -> int:
        return len(self.winners)

    def has_won(self, user: User) -> bool:
        key = user.name.strip().lower()
        return any(w.user.name.strip().lower() == key for w in self.winners)

    def add_winner(self, user, prize) -> Optional[Winner]:
        if self.has_won(user):
            return None
        self._counter += 1
        winner = Winner(user=user, prize=prize, draw_order=self._counter)
        self.winners.append(winner)
        return winner

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        prizes = list(prizes or [])
        indexed = list(enumerate(prizes))
        indexed.sort(key=lambda item: (item[1].level_rank, item[0]))
        result: Dict[str, List[Winner]] = {}
        for _, prize in indexed:
            items = [w for w in self.winners if w.prize.name == prize.name]
            items.sort(key=lambda w: (w.win_time, w.draw_order))
            result[prize.name] = items
        return result

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winners to export"
        path = os.path.join(os.getcwd(), f"awards_result_{datetime.now():%Y%m%d}.txt")
        grouped = self.get_winners_by_prize(prizes)
        # Include winners of prizes not in the given list, too.
        listed = {name for name in grouped}
        extra = [w for w in self.winners if w.prize.name not in listed]
        try:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["No.", "Name", "Department", "Prize Name", "Prize Level", "Win Time"])
                no = 0
                for prize_name, winners in grouped.items():
                    for w in winners:
                        no += 1
                        writer.writerow([no, w.user.name, w.user.department, prize_name,
                                         w.prize.level, w.win_time.strftime("%Y-%m-%d %H:%M:%S")])
                for w in extra:
                    no += 1
                    writer.writerow([no, w.user.name, w.user.department, w.prize.name,
                                     w.prize.level, w.win_time.strftime("%Y-%m-%d %H:%M:%S")])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
