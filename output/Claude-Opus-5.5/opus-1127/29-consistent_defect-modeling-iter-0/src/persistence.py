"""JSON persistence of configuration, riders and order history."""

import json
import logging
import os

try:
    from . import config, globalvar
    from .order_model import Order
    from .rider import Rider
except ImportError:  # pragma: no cover
    import config
    import globalvar
    from order_model import Order
    from rider import Rider

logger = logging.getLogger(__name__)


def load_config(path):
    """Load a JSON configuration file; returns defaults on failure."""
    cfg = dict(config.DEFAULT_CONFIG)
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for k in cfg:
                    if k in data:
                        cfg[k] = int(data[k])
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("Could not read config %s: %s", path, exc)
    return cfg


def save_state(path):
    """Save system parameters, riders and orders to ``path``."""
    data = {
        "config": globalvar.get_value("config"),
        "funds": globalvar.get_value("funds"),
        "rider_id_counter": globalvar.get_value("rider_id_counter"),
        "time": globalvar.get_value("time"),
        "orders": [o.to_dict() for o in globalvar.get_value("orders") or []],
        "riders": [r.to_dict() for r in globalvar.get_value("riders") or []],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return path


def load_state(path):
    """Load a previously saved state into the global registry."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    orders = [Order.from_dict(d) for d in data.get("orders", [])]
    by_id = {o.id: o for o in orders}
    riders = [Rider.from_dict(d, by_id) for d in data.get("riders", [])]
    globalvar.set_value("orders", orders)
    globalvar.set_value("riders", riders)
    globalvar.set_value("funds", data.get("funds", config.INITIAL_FUNDS))
    globalvar.set_value("rider_id_counter", data.get("rider_id_counter", 0))
    globalvar.set_value("rider_id", data.get("rider_id_counter", 0))
    globalvar.set_value("time", data.get("time", 0))
    return len(riders), len(orders)
