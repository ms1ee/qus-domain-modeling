import os
from datetime import datetime


class Winner:
    def __init__(self, user, prize_name, win_time=None):
        self.user = user
        self.prize_name = prize_name
        self.win_time = win_time or datetime.now()


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        w = Winner(user, prize.name)
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes):
        result = {}
        for p in prizes:
            result[p.name] = [w for w in self.winners if w.prize_name == p.name]
        return result

    def export_to_csv(self, prizes):
        grouped = self.get_winners_by_prize(prizes)
        if not any(grouped.values()):
            return False, "No winners to export"
        path = os.path.join(os.getcwd(), f"awards_result_{datetime.now():%Y%m%d}.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                for ws in grouped.values():
                    for w in sorted(ws, key=lambda x: x.win_time):
                        f.write(f"{w.user.name},{w.user.department},{w.prize_name},"
                                f"{w.win_time:%Y-%m-%d %H:%M:%S}\n")
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
