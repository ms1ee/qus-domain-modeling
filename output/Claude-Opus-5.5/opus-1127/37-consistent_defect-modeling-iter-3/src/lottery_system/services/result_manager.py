"""Result management and export."""
import csv
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

from lottery_system.models import UNKNOWN_LEVEL, Prize, User


@dataclass
class Winner:
    user: User
    prize_name: str
    winning_time: datetime
    order: int

    @property
    def name(self) -> str:
        return self.user.name

    @property
    def department(self) -> str:
        return self.user.department


def _prize_name(prize) -> str:
    return prize.name if hasattr(prize, "name") else str(prize)


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []
        self._counter = 0

    def has_won(self, name: str) -> bool:
        return any(w.user.name == name for w in self.winners)

    def add_winner(self, user, prize) -> bool:
        if self.has_won(user.name):
            return False
        self._counter += 1
        self.winners.append(Winner(user, _prize_name(prize), datetime.now(), self._counter))
        return True

    @staticmethod
    def _sorted_prize_names(prizes) -> List[str]:
        indexed = []
        for i, p in enumerate(prizes or []):
            if isinstance(p, Prize):
                lvl = p.level
            else:
                lvl = Prize(_prize_name(p), 1).level
            indexed.append((lvl, i, _prize_name(p)))
        indexed.sort(key=lambda t: (t[0], t[1]))
        names = []
        for _, _, n in indexed:
            if n not in names:
                names.append(n)
        return names

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for n in self._sorted_prize_names(prizes):
            result[n] = []
        extra = []
        for w in sorted(self.winners, key=lambda w: w.order):
            if w.prize_name not in result:
                result[w.prize_name] = []
                extra.append(w.prize_name)
            result[w.prize_name].append(w)
        if extra:
            ordered = {k: v for k, v in result.items() if k not in extra}
            extra.sort(key=lambda n: (Prize(n, 1).level, extra.index(n)))
            for n in extra:
                ordered[n] = result[n]
            result = ordered
        return result

    def get_sorted_winners(self, prizes) -> List[Winner]:
        out: List[Winner] = []
        for lst in self.get_winners_by_prize(prizes).values():
            out.extend(lst)
        return out

    def export_to_csv(self, prizes) -> Tuple[bool, str]:
        if not self.winners:
            return False, "No winners to export"
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for w in self.get_sorted_winners(prizes):
                    writer.writerow([
                        w.user.name,
                        w.user.department,
                        w.prize_name,
                        w.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                    ])
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"


__all__ = ["Winner", "ResultManager", "UNKNOWN_LEVEL"]
