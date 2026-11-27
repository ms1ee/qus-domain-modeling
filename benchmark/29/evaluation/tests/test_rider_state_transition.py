import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

import globalvar as gl
from rider import Rider
from order_model import Order

MAX_TICKS = 500


def move_until(rider, done):
    for _ in range(MAX_TICKS):
        if done():
            return
        rider.move()


def test_rider_state_transition():
    # Metric 4.2
    gl._init()
    rider = Rider(1)
    # grid cell centers (PRD 2.3), unchanged by coordinate conversion
    order = Order(res_pos=(150, 150), cus_pos=(250, 250))
    rider.orders.append(order)
    
    # Initial state should be 0 (idle)
    assert rider.state == 0
    
    # After first move, state should be 1 (to_pickup)
    rider.move()
    assert rider.state == 1
    
    # Move until the rider reaches the restaurant
    move_until(rider, lambda: rider.state != 1)
    # Now state should be 2 (to_deliver)
    assert rider.state == 2
    
    # Move until the rider reaches the customer
    move_until(rider, lambda: rider.state != 2)
    # Now state should be 0 (idle)
    assert rider.state == 0
    assert not rider.orders # Order should be completed and removed
