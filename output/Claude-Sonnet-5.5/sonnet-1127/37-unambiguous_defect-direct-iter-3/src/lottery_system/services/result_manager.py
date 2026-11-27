import datetime
import os
from typing import Dict, List


class Winner:
    def __init__(self, user, prize_name, order=0):
        self.user = user
        self.prize_name = prize_name
        self.order = order


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []

    def add_winner(self, user, prize):
        name = getattr(prize, "name", prize)
        w = Winner(user, name, len(self.winners))
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in prizes:
            name = getattr(p, "name", p)
            result[name] = [w for w in self.winners if w.prize_name == name]
        return result

    def export_to_csv(self, prizes):
        date = datetime.date.today().strftime("%Y%m%d")
        path = os.path.join(os.getcwd(), f"awards_result_{date}.txt")
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize\n")
                for name, ws in grouped.items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{name}\n")
            return True, f"Results successfully exported to {path}"
        except OSError as e:
            return False, f"Export failed: {e}"
