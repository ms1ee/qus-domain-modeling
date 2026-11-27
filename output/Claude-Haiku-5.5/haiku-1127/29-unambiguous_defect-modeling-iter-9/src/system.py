"""System initialisation, funds management, rider recruitment and persistence."""

import json
import logging
import os
from dataclasses import asdict
from typing import List

import globalvar
from config import DEFAULT_CONFIG_FILE, get_config, load_config
from rider import Rider

logger = logging.getLogger(__name__)


def init_system() -> None:
    """Initialise all core parameters and global state.

    Sets system funds, an empty rider list, the rider ID counter (0), the
    running flag (True), the simulated tick (0) and the order list.
    """
    globalvar._init()
    cfg = load_config(DEFAULT_CONFIG_FILE)
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", cfg.initial_funds)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("is_running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_id_counter", 0)
    logger.info("System initialised with funds=%d", cfg.initial_funds)


def get_riders() -> List[Rider]:
    """Return the live list of riders."""
    return globalvar.get_value("riders", [])


def get_funds() -> int:
    """Return the current system fund balance."""
    return int(globalvar.get_value("funds", 0))


def can_recruit() -> bool:
    """Return True if a new rider may be recruited now.

    A recruit is allowed when the rider count is below the configured maximum
    and the funds cover the recruitment cost.
    """
    cfg = get_config()
    return len(get_riders()) < cfg.max_riders and get_funds() >= cfg.recruitment_cost


def recruit_rider() -> Rider:
    """Recruit a new rider, deducting the recruitment cost from funds.

    Returns:
        The newly created ``Rider``.

    Raises:
        RuntimeError: If recruitment is not currently possible.
    """
    if not can_recruit():
        raise RuntimeError("Cannot recruit: insufficient funds or rider limit reached")
    cfg = get_config()
    globalvar.set_value("funds", get_funds() - cfg.recruitment_cost)
    counter = int(globalvar.get_value("rider_id_counter", 0)) + 1
    globalvar.set_value("rider_id_counter", counter)
    new_rider = Rider(counter)
    get_riders().append(new_rider)
    logger.info("Recruited rider %d; funds now %d", counter, get_funds())
    return new_rider


def advance_tick() -> int:
    """Advance the simulation by one tick and move every rider.

    Errors raised by an individual rider are logged and the rider is
    recovered, so one faulty rider cannot stop the simulation.

    Returns:
        The new tick value.
    """
    tick = int(globalvar.get_value("tick", 0)) + 1
    globalvar.set_value("tick", tick)
    for rider in list(get_riders()):
        try:
            rider.move()
        except Exception:  # noqa: BLE001 - recovery is intentional here
            logger.exception("Error while moving rider %d; attempting recovery", rider.rider_id)
            try:
                rider.recover()
            except Exception:  # noqa: BLE001
                logger.exception("Recovery failed for rider %d", rider.rider_id)
    return tick


def save_state(path: str) -> None:
    """Persist configuration, funds, riders and orders to a JSON file.

    Args:
        path: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    payload = {
        "config": asdict(get_config()),
        "tick": globalvar.get_value("tick", 0),
        "funds": get_funds(),
        "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
        "order_id_counter": globalvar.get_value("order_id_counter", 0),
        "riders": [r.to_dict() for r in get_riders()],
        "orders": [o.to_dict() for o in globalvar.get_value("orders", [])],
    }
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    os.replace(tmp_path, path)
    logger.info("State saved to %s", path)
