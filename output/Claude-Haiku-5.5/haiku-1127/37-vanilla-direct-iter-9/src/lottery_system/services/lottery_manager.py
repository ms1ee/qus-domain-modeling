"""Lottery rule engine: eligibility filtering, special rules and fallback protection."""
import random

from lottery_system.config import CHEN_QIXIAN, CHENG_RU_GROUP, JIN_DUO, LI_BIN, MA_JIAQI
from lottery_system.models import Prize, User
from lottery_system.utils import normalize_text


def _drawer_key(prize: Prize) -> str:
    return normalize_text(prize.associated_drawer or "")


class LotteryManager:
    """Draws winners while enforcing all lottery rules."""

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self._users: list[User] = list(users)
        self._winner_keys: set[str] = set()
        # Results of the most recent draws by Chen Qixian / Jin Duo:
        # True means the winner belonged to the Cheng Ru group.
        self.last_two_draw_results: list[bool] = []
        self._rng = rng or random.Random()

    # ----------------------------------------------------------- helpers
    def has_won(self, user: User) -> bool:
        return normalize_text(user.name) in self._winner_keys

    def remaining_users(self) -> list[User]:
        return [user for user in self._users if not self.has_won(user)]

    @staticmethod
    def is_cheng_ru_member(user: User) -> bool:
        return normalize_text(user.department) == normalize_text(CHENG_RU_GROUP)

    def is_fallback_active(self) -> bool:
        """True when the last two draws by Chen Qixian / Jin Duo had no Cheng Ru member."""
        return len(self.last_two_draw_results) >= 2 and not any(self.last_two_draw_results[-2:])

    def _cheng_ru_remaining(self) -> list[User]:
        return [user for user in self.remaining_users() if self.is_cheng_ru_member(user)]

    # ------------------------------------------------------------- rules
    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the users who may win the given prize right now."""
        available = self.remaining_users()
        drawer = _drawer_key(prize)

        # Fallback: Ma Jiaqi's pool is forced to Cheng Ru members, ignoring avoid groups.
        if drawer == normalize_text(MA_JIAQI) and self.is_fallback_active():
            forced = [user for user in available if self.is_cheng_ru_member(user)]
            if forced:
                return forced
            # No Cheng Ru members remain: fall back to the ordinary rules.

        # Special rule: Li Bin only filters previous winners.
        if drawer == normalize_text(LI_BIN):
            return available

        avoid = {normalize_text(group) for group in prize.avoid_groups}
        return [user for user in available if normalize_text(user.department) not in avoid]

    def eligible_count(self, prize: Prize) -> int:
        return len(self._get_eligible_pool(prize))

    def describe_rule(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to this prize."""
        drawer = _drawer_key(prize)
        if (drawer == normalize_text(MA_JIAQI) and self.is_fallback_active()
                and self._cheng_ru_remaining()):
            return (f"{CHENG_RU_GROUP} protection is active: only unawarded {CHENG_RU_GROUP} "
                    f"members can win this prize (avoid groups are ignored).")
        base = "Previous winners are excluded."
        if drawer == normalize_text(LI_BIN):
            return base + " Avoid groups do not apply to this lottery person."
        if prize.avoid_groups:
            return base + " Avoid groups: " + ", ".join(prize.avoid_groups) + "."
        return base + " No avoid groups."

    # ------------------------------------------------------------- drawing
    def draw_one(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no eligible candidate exists."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self._winner_keys.add(normalize_text(winner.name))

        drawer = _drawer_key(prize)
        if drawer in (normalize_text(CHEN_QIXIAN), normalize_text(JIN_DUO)):
            self.last_two_draw_results.append(self.is_cheng_ru_member(winner))
            del self.last_two_draw_results[:-2]
        return winner
