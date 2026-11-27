import os
from collections import OrderedDict
from datetime import datetime


class Winner:
    def __init__(self, user, prize_name, winning_time=None, order=0):
        self.user = user
        self.prize_name = prize_name
        self.winning_time = winning_time or datetime.now()
        self.order = order


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        w = Winner(user, prize.name, datetime.now(), len(self.winners) + 1)
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes):
        result = OrderedDict()
        for p in prizes:
            result[p.name] = [w for w in self.winners if w.prize_name == p.name]
        return dict(result)

    def export_to_csv(self, prizes):
        grouped = self.get_winners_by_prize(prizes)
        if not self.winners:
            return False, "No winners to export"
        path = os.path.join(os.getcwd(),
                            f"awards_result_{datetime.now():%Y%m%d}.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize Name,Winning Time\n")
                for name, ws in grouped.items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{name},"
                                f"{w.winning_time:%Y-%m-%d %H:%M:%S}\n")
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
