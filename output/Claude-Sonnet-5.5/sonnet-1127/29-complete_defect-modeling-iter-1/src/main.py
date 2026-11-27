"""Entry point: python src/main.py"""
import globalvar
from system import init_system
from input_manager import InputManager


def main():
    system = init_system()
    im = InputManager(system)
    print("Food Delivery Dispatch Simulator. Type 'help'.")
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        out = im.handle(line)
        if out:
            print(out)
        if globalvar.get_value("running"):
            system.tick()
    try:
        system.save()
    except OSError:
        pass


if __name__ == "__main__":
    main()
