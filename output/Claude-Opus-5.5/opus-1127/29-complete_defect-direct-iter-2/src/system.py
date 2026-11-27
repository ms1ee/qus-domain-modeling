"""System manager: funds, riders, time and consistency."""

import logging

import config
import globalvar
from order_model import Order
from rider import Rider, STATE_IDLE

logger = logging.getLogger(__name__)


class SystemManager:
    """Core manager for funds, riders and the simulation clock."""

    @property
    def funds(self):
        """Current system funds."""
        return globalvar.get_value("funds", 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", int(value))

    @property
    def riders(self):
        """List of riders."""
        lst = globalvar.get_value("riders")
        if lst is None:
            lst = []
            globalvar.set_value("riders", lst)
        return lst

    @property
    def tick(self):
        """Current simulated time."""
        return globalvar.get_value("tick", 0)

    @property
    def running(self):
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("running", False))

    def stop(self):
        """Stop the main loop."""
        globalvar.set_value("running", False)

    def add_rider(self):
        """Create a new rider with an auto-incremented ID."""
        counter = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        return rider

    def remove_rider(self, rider_id):
        """Remove an idle rider by id; returns True on success."""
        for r in self.riders:
            if r.rider_id == rider_id and not r.active_orders():
                self.riders.remove(r)
                return True
        return False

    def get_rider(self, rider_id):
        """Find a rider by id."""
        for r in self.riders:
            if r.rider_id == rider_id:
                return r
        return None

    def check_recruitment(self):
        """Recruit a rider if funds allow; returns the rider or None."""
        if self.funds >= config.RIDER_COST and \
                len(self.riders) < config.MAX_RIDERS:
            self.funds = self.funds - config.RIDER_COST
            rider = self.add_rider()
            logger.info("Recruited rider %d", rider.rider_id)
            return rider
        return None

    def advance_tick(self):
        """Advance the simulation by one tick."""
        globalvar.set_value("tick", self.tick + 1)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception as exc:  # recovery mechanism
                logger.error("Rider %d error: %s", rider.rider_id, exc)
                self.consistency_check()
        from order import OrderManager
        OrderManager(self).assign_pending()
        self.check_recruitment()

    def consistency_check(self):
        """Repair inconsistent state; returns list of fixes performed."""
        fixes = []
        for r in self.riders:
            if r.state != STATE_IDLE and not r.active_orders():
                r.state = STATE_IDLE
                r.path = []
                r.special_case = False
                fixes.append("rider %d reset to idle" % r.rider_id)
            r.orders = [o for o in r.orders if o.status != "completed"]
        ids = [r.rider_id for r in self.riders]
        if ids and globalvar.get_value("rider_id_counter", 0) < max(ids):
            globalvar.set_value("rider_id_counter", max(ids))
            fixes.append("rider id counter repaired")
        return fixes


def init_system():
    """Initialise all global parameters; returns a SystemManager."""
    globalvar._init()
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("funds", config.INITIAL_FUNDS)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("grid", {"size": config.MAP_SIZE,
                                 "cell": config.GRID_SIZE,
                                 "cells": config.GRID_CELLS})
    Order.reset_counter()
    return SystemManager()
