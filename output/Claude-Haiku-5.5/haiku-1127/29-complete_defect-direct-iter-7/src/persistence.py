"""JSON persistence of system parameters, riders and order history."""

from __future__ import annotations

import json
import logging
import os
import tempfile

import config

logger = logging.getLogger("dispatch.persistence")


def build_snapshot(system) -> dict:
    """Assemble a JSON-compatible snapshot of the simulation.

    Args:
        system: The SystemManager instance.

    Returns:
        dict: Parameters, funds, tick, riders and order history.
    """
    return {
        "parameters": config.get_parameters(),
        "funds": system.funds,
        "tick": system.tick,
        "riders": [rider.to_dict() for rider in system.riders],
        "orders": [order.to_dict()
                   for order in system.order_manager.all_orders()],
        "pending_order_ids": [order.id for order in
                              system.order_manager.pending_orders()],
    }


def save_state(path: str, system) -> bool:
    """Write a snapshot to ``path`` atomically.

    Args:
        path: Destination JSON file.
        system: The SystemManager instance.

    Returns:
        bool: True if the file was written successfully.
    """
    snapshot = build_snapshot(system)
    directory = os.path.dirname(os.path.abspath(path))
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(dir=directory, prefix=".dispatch-",
                                         suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, indent=2)
        os.replace(temp_path, path)
        temp_path = None
        logger.info("State saved to %s", path)
        return True
    except (OSError, TypeError, ValueError) as exc:
        logger.error("Could not save state to %s: %s", path, exc)
        return False
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
