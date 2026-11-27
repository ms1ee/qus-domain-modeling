"""System initialisation."""
import globalvar


def init_system():
    """Initialise core parameters."""
    globalvar._init()
    globalvar.set_value("funds", 1000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("map_size", 800)
    globalvar.set_value("cell_size", 100)
