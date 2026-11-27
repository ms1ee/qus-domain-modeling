import re
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

import globalvar as gl
import system
from rider import Rider
from order_model import Order

MAX_TICKS = 500


def norm(s):
    return re.sub(r"\s+", "", s).lower()

def test_order_completion():
    # Metric 8.1
    system.init_system()
    rider = Rider(1)
    gl.set_value("riders", [rider]) # register the rider so assign_to can find it
    # grid cell centers (PRD 2.3), unchanged by coordinate conversion
    order = Order(res_pos=(150, 150), cus_pos=(250, 250))
    order.assign_to(rider.rider_id)
    if order not in rider.orders: # assign_to may already append it
        rider.orders.append(order)
    
    # Move until the order is delivered
    rider.move()
    for _ in range(MAX_TICKS):
        if not rider.orders:
            break
        rider.move()
    
    assert rider.state == 0 # Rider should be idle
    assert not rider.orders # Order list should be empty
    assert norm(order.status) == norm("completed") # Order status should be completed
