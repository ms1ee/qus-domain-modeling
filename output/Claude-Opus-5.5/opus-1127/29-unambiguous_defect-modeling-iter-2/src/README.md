# Food Delivery Order Dispatch System (CLI simulator)

Run: `python main.py [--config config.json] [--debug] [--no-save]`

Commands (shortcut in brackets):

* `start` (`s`) – enter `restaurant_x restaurant_y customer_x customer_y` (0-800).
  Can be given inline: `start 120 340 560 780`.
* `status` (`st`) – funds, riders, states, order lists and map.
* `orders` (`o`) – all orders with timing, distance and rider.
* `riders` (`r`) – status-change log of every rider.
* `map` (`m`) – ASCII map.
* `step [n]` (`n`) – advance simulation `n` ticks.
* `history` (`hi`), `!N` – show / re-run command N.
* `save` – write state to the JSON state file.
* `quit` / `exit` (`q`).

Every iteration of the main loop advances the simulation by one tick.

Map coordinates: 800x800, cells of 100x100. Streets run along multiples of
100; restaurants/customers sit at cell centres (`(v // 100) * 100 + 50`).
