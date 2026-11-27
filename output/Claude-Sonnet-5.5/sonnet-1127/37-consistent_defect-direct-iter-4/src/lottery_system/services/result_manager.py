import os
from datetime import datetime
from typing import Dict, List


class Winner:
    def __init__(self, user, prize, win_time=None):
        self.user = user
        self.prize = prize
        self.win_time = win_time or datetime.now()

    @property
    def prize_name(self):
        return getattr(self.prize, "name", str(self.prize))


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []

    def add_winner(self, user, prize):
        w = Winner(user, prize)
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in prizes:
            ws = [w for w in self.winners if w.prize_name == p.name]
            ws.sort(key=lambda w: w.win_time)
            result[p.name] = ws
        return result

    def export_to_csv(self, prizes):
        fname = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), fname)
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize Name,Winning Time\n")
                for name, ws in grouped.items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{name},"
                                f"{w.win_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            return True, f"Results successfully exported to {path}"
        except OSError as e:
            return False, f"Export failed: {e}"
