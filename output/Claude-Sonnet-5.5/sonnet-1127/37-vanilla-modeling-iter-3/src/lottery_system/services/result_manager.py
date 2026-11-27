import os
from datetime import datetime
from typing import Dict, List


class Winner:
    def __init__(self, user, prize, time=None, order=0):
        self.user = user
        self.prize = prize
        self.time = time or datetime.now()
        self.order = order


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []

    def add_winner(self, user, prize):
        w = Winner(user, prize, datetime.now(), len(self.winners) + 1)
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in prizes:
            result[p.name] = [w for w in self.winners if w.prize.name == p.name]
        return result

    def export_to_csv(self, prizes):
        path = os.path.join(os.getcwd(),
                            f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize Name,Winning Time\n")
                for name, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{name},"
                                f"{w.time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
