"""Rider recruitment (resource management)."""

import logging

import globalvar
from config import DEFAULTS
from rider import Rider

logger = logging.getLogger(__name__)


def _cfg(key):
    cfg = globalvar.get_value("config") or {}
    return int(cfg.get(key, DEFAULTS[key]))


def can_recruit():
    """True if funds allow another rider and the rider cap is not reached."""
    funds = globalvar.get_value("funds")
    if funds is None:
        return False
    riders = globalvar.get_value("riders") or []
    return funds >= _cfg("recruitment_cost") and len(riders) < _cfg("max_riders")


def recruit_rider():
    """Create a new rider if possible, deducting the cost. Returns it or None."""
    if not can_recruit():
        return None
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    counter = int(globalvar.get_value("rider_id_counter", 0) or 0) + 1
    globalvar.set_value("rider_id_counter", counter)
    globalvar.set_value("funds", globalvar.get_value("funds") - _cfg("recruitment_cost"))
    rider = Rider(counter)
    riders.append(rider)
    logger.info("Recruited rider %d", counter)
    return rider
