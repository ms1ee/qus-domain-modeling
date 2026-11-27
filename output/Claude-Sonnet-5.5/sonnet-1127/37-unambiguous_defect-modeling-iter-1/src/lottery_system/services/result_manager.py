import datetime


class Winner:
    def __init__(self, user, prize, order=0):
        self.user = user
        self.prize = prize
        self.order = order
        self.time = datetime.datetime.now()


def _level(name):
    n = name.lower()
    for i, k in enumerate(("special", "first", "second", "third")):
        if k in n:
            return i
    return 99


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        w = Winner(user, prize, len(self.winners) + 1)
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes):
        ordered = sorted(prizes, key=lambda p: _level(p.name))
        result = {}
        for p in ordered:
            ws = [w for w in self.winners if w.prize is p or w.prize.name == p.name]
            ws.sort(key=lambda w: w.order)
            result[p.name] = ws
        return result

    def export_to_csv(self, prizes):
        fname = f"awards_result_{datetime.date.today().strftime('%Y%m%d')}.txt"
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(fname, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize\n")
                for pname, ws in grouped.items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{pname}\n")
            return True, f"Results successfully exported to {fname}"
        except OSError as e:
            return False, f"Export failed: {e}"
