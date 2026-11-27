"""System manager: funds, rider recruitment, ticks and command execution."""

import logging
import math

import globalvar
from config import DEFAULT_CONFIG, save_json
from display_manager import DisplayManager
from grid import MAP_SIZE
from input_manager import CommandError, InputManager
from order import OrderManager, OrderValidationError, find_best_rider_for_order
from order_model import STATUS_COMPLETED
from path_planner import PathPlanner
from rider import IDLE, STATE_NAMES, Rider

logger = logging.getLogger(__name__)

MAX_TICKS_PER_COMMAND = 1000


def init_system(config=None):
    """Initialise global state and create the system manager.

    Args:
        config: Optional configuration dictionary (see ``config.load_config``).

    Returns:
        SystemManager: The initialised system.
    """
    globalvar._init()
    return SystemManager(config)


class SystemManager:
    """Core coordinator for funds, riders, the simulation clock and commands.

    Attributes:
        funds (int): System fund balance, may go negative after costs.
        riders (list[Rider]): Active riders (shared with the global store).
        rider_id_counter (int): Last rider id issued.
        is_running (bool): Main loop control flag.
        current_tick (int): Simulated time.
        recruitment_cost (int): Funds deducted per recruited rider.
        order_manager (OrderManager): Order creation and assignment.
        planner (PathPlanner): Route planning for display estimates.
        display (DisplayManager): Text rendering.
        input_manager (InputManager): Command parsing and history.
    """

    def __init__(self, config=None):
        """Create the system with the given or default configuration.

        Args:
            config: Optional configuration dictionary.
        """
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(config or {})
        self.config = cfg
        self.funds = int(cfg["initial_funds"])
        self.recruitment_cost = int(cfg["recruitment_cost"])
        self.max_riders = int(cfg["max_riders"])
        self.rider_capacity = int(cfg["rider_capacity"])
        self.state_file = cfg["state_file"]
        self.rider_id_counter = 0
        self.is_running = True
        self.current_tick = 0

        self.riders = []
        globalvar.set_value("riders", self.riders)
        globalvar.set_value("current_tick", 0)
        globalvar.set_value("speed_options", tuple(cfg["speed_options"]))
        globalvar.set_value("rider_capacity", self.rider_capacity)
        globalvar.set_value("load_penalty", int(cfg["load_penalty"]))

        self.order_manager = OrderManager()
        self.planner = PathPlanner()
        self.display = DisplayManager()
        self.input_manager = InputManager()

    # ----------------------------------------------------------------- riders
    def _can_recruit(self):
        """Return True if funds and the rider cap allow a new recruit."""
        return (len(self.riders) < self.max_riders
                and self.funds >= self.recruitment_cost)

    def recruit_rider(self):
        """Recruit a new rider, deducting the recruitment cost.

        Returns:
            Rider or None: The new rider, or None if recruitment is not possible.
        """
        if not self._can_recruit():
            return None
        self.funds -= self.recruitment_cost
        self.rider_id_counter += 1
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        logger.info("recruited rider %s; funds now %s", rider.rider_id, self.funds)
        return rider

    # ----------------------------------------------------------------- orders
    def _plan_route(self, rider, order):
        """Build the display route: rider -> restaurant -> customer.

        Args:
            rider: The assigned rider.
            order: The order being served.

        Returns:
            list[tuple[int, int]]: Route points, starting at the rider's position.
        """
        to_restaurant = self.planner.plan(rider.position, order.restaurant_pos)
        to_customer = self.planner.plan(order.restaurant_pos, order.customer_pos)
        return [rider.position] + to_restaurant + to_customer

    def submit_order(self, restaurant, customer):
        """Create an order, recruit a rider if needed and assign the order.

        Args:
            restaurant: Restaurant (x, y).
            customer: Customer (x, y).

        Returns:
            dict: Keys "order", "rider", "new_rider", "route", "eta", "speed".

        Raises:
            OrderValidationError: If the input is invalid or no rider can serve it.
        """
        order = self.order_manager.create_order(restaurant, customer)
        try:
            rider = find_best_rider_for_order(order)
            new_rider = False
            if rider is None:
                recruited = self.recruit_rider()
                if recruited is None:
                    raise OrderValidationError(
                        "No rider available and cannot recruit (funds=%d, cost=%d, riders=%d/%d)"
                        % (self.funds, self.recruitment_cost, len(self.riders), self.max_riders))
                new_rider = True
                rider = find_best_rider_for_order(order)
                if rider is None:
                    raise OrderValidationError("No rider with free capacity is available.")
        except OrderValidationError:
            self.order_manager.cancel_order(order)
            raise

        self.order_manager.assign(order, rider)
        route = self._plan_route(rider, order)
        steps = max(0, len(route) - 1)
        eta = int(math.ceil(steps / float(rider.speed))) if steps else 0
        return {
            "order": order,
            "rider": rider,
            "new_rider": new_rider,
            "route": route,
            "eta": eta,
            "speed": rider.speed,
        }

    # ------------------------------------------------------------------ clock
    def tick(self, steps=1):
        """Advance the simulation by ``steps`` ticks.

        Each tick increments the clock and calls ``move()`` on every rider.
        A failing rider is recovered rather than stopping the simulation.

        Args:
            steps: Number of ticks to run.

        Returns:
            int: The new current tick.
        """
        for _ in range(steps):
            self.current_tick += 1
            globalvar.set_value("current_tick", self.current_tick)
            for rider in self.riders:
                try:
                    rider.move()
                except Exception:  # pragma: no cover - defensive recovery
                    logger.exception("rider %s failed; recovering", rider.rider_id)
                    self._recover_rider(rider)
        return self.current_tick

    @staticmethod
    def _recover_rider(rider):
        """Restore a rider to a consistent state after an unexpected error.

        Args:
            rider: The rider to repair.
        """
        rider.path = []
        rider.special_case = False
        if not rider.orders:
            rider.state = IDLE

    def check_consistency(self):
        """Check the system for state inconsistencies.

        Returns:
            list[str]: Human-readable problem descriptions (empty if healthy).
        """
        issues = []
        ids = [rider.rider_id for rider in self.riders]
        if len(ids) != len(set(ids)):
            issues.append("duplicate rider ids detected")
        for rider in self.riders:
            if rider.state != IDLE and not rider.orders:
                issues.append("rider %d is %s with no orders"
                              % (rider.rider_id, STATE_NAMES[rider.state]))
            if len(rider.orders) > self.rider_capacity:
                issues.append("rider %d exceeds capacity" % rider.rider_id)
            for order in rider.orders:
                if order.status == STATUS_COMPLETED:
                    issues.append("rider %d still holds completed order %d"
                                  % (rider.rider_id, order.id))
                if order.rider_id != rider.rider_id:
                    issues.append("order %d owner mismatch with rider %d"
                                  % (order.id, rider.rider_id))
        return issues

    # ---------------------------------------------------------------- reports
    def status_text(self):
        """Return the status snapshot text."""
        return self.display.render_status(
            self.current_tick, self.funds, self.riders,
            self.order_manager.active_orders(), self.check_consistency())

    def orders_text(self):
        """Return the order details table."""
        return self.display.render_orders(self.order_manager.orders)

    def riders_text(self):
        """Return the rider status-change log."""
        return self.display.render_rider_events(self.riders)

    def map_text(self):
        """Return the ASCII map with riders and active orders."""
        return self.display.render_map(riders=self.riders,
                                       orders=self.order_manager.active_orders())

    def history_text(self):
        """Return the numbered command history."""
        history = self.input_manager.command_history
        if not history:
            return "No commands in history."
        return "\n".join("%3d  %s" % (i, cmd) for i, cmd in enumerate(history, 1))

    # ------------------------------------------------------------ persistence
    def save_state(self, path=None):
        """Save system parameters, riders and order history as JSON.

        Args:
            path: Destination file; defaults to the configured state file.

        Returns:
            str: The path written.

        Raises:
            OSError: If the file cannot be written.
        """
        path = path or self.state_file
        data = {
            "config": self.config,
            "system": {
                "funds": self.funds,
                "current_tick": self.current_tick,
                "rider_id_counter": self.rider_id_counter,
                "recruitment_cost": self.recruitment_cost,
            },
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.order_manager.orders],
            "order_history": [record.to_dict()
                              for record in (globalvar.get_value("order_history") or [])],
        }
        save_json(path, data)
        return path

    def shutdown(self):
        """Persist state on exit, logging rather than raising on failure."""
        try:
            path = self.save_state()
            logger.info("state saved to %s", path)
        except OSError as exc:
            logger.error("could not save state: %s", exc)

    # --------------------------------------------------------------- commands
    def execute(self, command, args=None, reader=input):
        """Execute a parsed command and return its output text.

        Args:
            command: Command name from ``InputManager.parse``.
            args: List of argument tokens.
            reader: Callable used for interactive prompts.

        Returns:
            str: Output to display.

        Raises:
            CommandError: For invalid arguments or unknown commands.
        """
        args = list(args or [])
        if command == "start":
            return self._cmd_start(args, reader)
        if command == "tick":
            return self._cmd_tick(args)
        if command == "status":
            return self.status_text()
        if command == "orders":
            return self.orders_text()
        if command == "riders":
            return self.riders_text()
        if command == "map":
            return self.map_text()
        if command == "history":
            return self.history_text()
        if command == "save":
            return "State saved to %s" % self.save_state()
        if command == "help":
            return DisplayManager.HELP_TEXT
        if command == "quit":
            self.is_running = False
            self.shutdown()
            return "State saved. Goodbye."
        raise CommandError("Unknown command: %s" % command)

    def _cmd_start(self, args, reader):
        """Handle the ``start`` command: place an order and show its route."""
        if args:
            coords = self.input_manager.parse_coordinates(args)
        else:
            coords = self.input_manager.prompt_coordinates(reader)
        try:
            result = self.submit_order(coords[0:2], coords[2:4])
        except OrderValidationError as exc:
            raise CommandError(str(exc))
        return self.display.render_order_result(
            order=result["order"],
            rider=result["rider"],
            new_rider=result["new_rider"],
            route=result["route"],
            funds=self.funds,
            eta=result["eta"],
            speed=result["speed"],
        )

    def _cmd_tick(self, args):
        """Handle the ``tick [n]`` command."""
        steps = 1
        if args:
            try:
                steps = int(args[0])
            except ValueError:
                raise CommandError("tick count must be an integer, got '%s'." % args[0])
            if not 1 <= steps <= MAX_TICKS_PER_COMMAND:
                raise CommandError("tick count must be between 1 and %d."
                                   % MAX_TICKS_PER_COMMAND)
        self.tick(steps)
        completed = len(self.order_manager.completed_orders())
        return "Advanced %d tick(s). Current tick: %d. Completed orders: %d." % (
            steps, self.current_tick, completed)
