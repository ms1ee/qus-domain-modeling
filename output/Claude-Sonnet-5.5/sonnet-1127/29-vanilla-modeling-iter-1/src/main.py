"""Entry point: python src/main.py"""

import globalvar
from system import SystemManager
from display import DisplayManager
from input_manager import InputManager


def main():
    system = SystemManager()
    display = DisplayManager(system)
    im = InputManager(system, display)
    print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        out = im.handle(line)
        if out:
            print(out)


if __name__ == "__main__":
    main()
