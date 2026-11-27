"""JSON persistence: configuration loading and state snapshots."""

import json
import logging

import config
import globalvar

logger = logging.getLogger(__name__)


def build_snapshot():
    """Build a JSON-serialisable snapshot of the current system state.

    Returns:
        dict: Funds, tick, rider list, order history and pending orders.
    """
    riders = globalvar.get_value("riders", []) or []
    orders = globalvar.get_value("orders", []) or []
    pending = globalvar.get_value("pending_orders", []) or []
    return {
        "funds": globalvar.get_value("funds", 0),
        "tick": globalvar.get_value("tick", 0),
        "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
        "parameters": {
            "recruit_threshold": config.RECRUIT_THRESHOLD,
            "rider_cost": config.RIDER_COST,
            "order_fee": config.ORDER_FEE,
            "default_speed": config.DEFAULT_SPEED,
        },
        "riders": [rider.to_dict() for rider in riders],
        "orders": [order.to_dict() for order in orders],
        "pending_orders": [order.id for order in pending],
    }


def save_snapshot(path=None):
    """Write the current system state to a JSON file.

    Args:
        path: Destination file path; defaults to ``config.DEFAULT_SNAPSHOT_PATH``.

    Returns:
        str: The path that was written.

    Raises:
        OSError: If the file cannot be written.
    """
    target = path or config.DEFAULT_SNAPSHOT_PATH
    snapshot = build_snapshot()
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2)
    logger.info("Snapshot saved to %s", target)
    return target


def load_configuration(path):
    """Apply system parameters from a JSON configuration file.

    Args:
        path: Path to the configuration file.

    Returns:
        list[str]: Names of the applied parameters.
    """
    applied = config.load_parameters(path)
    logger.info("Loaded configuration %s: %s", path, applied)
    return applied
