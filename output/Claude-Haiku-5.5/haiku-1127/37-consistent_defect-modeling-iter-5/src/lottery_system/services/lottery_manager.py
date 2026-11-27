"""Lottery rule engine: eligibility filtering, special rules, fallback and anti-duplication."""
import random
from lottery_system.models import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    Prize,
    User,
)


def _norm(value):
    return (value or "").strip().casefold()


def _is_drawer(prize, drawer_name):
    return prize.associated_drawer is not None and _norm(prize.associated_drawer) == _norm(drawer_name)


def _is_cheng_ru(user):
    return _norm(user.department) == _norm(CHENG_RU_GROUP)


class LotteryManager:
    def __init__(self, users, rng=None):
        self._users = list(users)
        self._rng = rng if rng is not None else random.Random()
        self._winner_keys = set()
        self._winners = []
        # True means the draw by Chen Qixian / Jin Duo produced a Cheng Ru group member.
        self.last_two_draw_results = []

    @property
    def winners(self):
        return list(self._winners)

    def is_winner(self, user):
        return _norm(user.name) in self._winner_keys

    def remaining_count(self):
        return len(self._available_users())

    def _available_users(self):
        return [user for user in self._users if not self.is_winner(user)]

    def _cheng_ru_protection_active(self):
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        available = self._available_users()

        # Special rule: Li Bin only filters previous winners.
        if _is_drawer(prize, LI_BIN):
            return available

        # Fallback: Ma Jiaqi's pool is forced to Cheng Ru group members when the
        # two previous Chen Qixian / Jin Duo draws both had no Cheng Ru group winner.
        if _is_drawer(prize, MA_JIAQI) and self._cheng_ru_protection_active():
            protected = [user for user in available if _is_cheng_ru(user)]
            if protected:
                return protected

        # Avoidance groups: their members stay eligible but are drawn after others.
        avoid = {_norm(group) for group in prize.avoid_groups if group and group.strip()}
        preferred = [user for user in available if _norm(user.department) not in avoid]
        if preferred:
            return preferred
        return [user for user in available if _norm(user.department) in avoid]

    def _record_draw(self, prize, user):
        if _is_drawer(prize, CHEN_QIXIAN) or _is_drawer(prize, JIN_DUO):
            self.last_two_draw_results.append(_is_cheng_ru(user))
            self.last_two_draw_results = self.last_two_draw_results[-2:]

    def draw_one(self, prize: Prize):
        """Draw one winner for the prize. Returns the User, or None if nobody is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self._winner_keys.add(_norm(user.name))
        self._winners.append(user)
        self._record_draw(prize, user)
        return user


def describe_rules(prize: Prize) -> str:
    """Human readable description of the rules applied to a prize round."""
    parts = []
    if prize.associated_drawer:
        parts.append(f"Lottery person: {prize.associated_drawer}")
    parts.append("previous winners are excluded")
    if _is_drawer(prize, LI_BIN):
        parts.append("special rule for Li Bin: avoidance groups are not applied")
    else:
        if prize.avoid_groups:
            parts.append(
                "members of avoidance groups (" + ", ".join(prize.avoid_groups)
                + ") are drawn after other members"
            )
        if _is_drawer(prize, MA_JIAQI):
            parts.append(
                "Cheng Ru group protection: if the last two draws by Chen Qixian and Jin Duo "
                "both had no Cheng Ru group member, the draw is limited to Cheng Ru group members"
            )
    return "; ".join(parts)
