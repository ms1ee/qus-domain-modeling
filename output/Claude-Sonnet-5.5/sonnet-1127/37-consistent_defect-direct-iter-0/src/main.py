import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def main():
    lm = ListManager()
    users, _ = lm.load_default_list()
    users, _ = lm.validate_users(users)
    pm = PrizeManager()
    pm.load_default_prizes()
    lot = LotteryManager(users)
    rm = ResultManager()
    for p in pm.get_prizes():
        print(f"Prize: {p.name} x{p.quantity}")
        for i in range(1, p.quantity + 1):
            print(f"Currently drawing the {i}th winner")
            u = lot.draw_one(p)
            if u is None:
                break
            rm.add_winner(u, p)
            print(f"Congratulations {u.name} ({u.department}) for winning {p.name}")
    print(rm.export_to_csv(pm.get_prizes())[1])


if __name__ == "__main__":
    main()
