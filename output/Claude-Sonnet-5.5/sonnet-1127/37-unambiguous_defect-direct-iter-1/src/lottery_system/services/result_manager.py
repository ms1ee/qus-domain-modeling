import datetime
from typing import Dict, List, Tuple

from ..models import Prize, User


class Winner:
    def __init__(self, user: User, prize_name: str, order: int = 0):
        self.user = user
        self.prize_name = prize_name
        self.order = order


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []

    def add_winner(self, user, prize):
        name = prize.name if hasattr(prize, "name") else str(prize)
        w = Winner(user, name, len(self.winners))
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in reversed(list(prizes)):
            result[p.name] = sorted(
                (w for w in self.winners if w.prize_name == p.name),
                key=lambda w: w.order)
        return result

    def export_to_csv(self, prizes) -> Tuple[bool, str]:
        if not self.winners:
            return False, "No winners to export"
        path = f"awards_result_{datetime.date.today().strftime('%Y%m%d')}.txt"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize\n")
                for name, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{name}\n")
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
