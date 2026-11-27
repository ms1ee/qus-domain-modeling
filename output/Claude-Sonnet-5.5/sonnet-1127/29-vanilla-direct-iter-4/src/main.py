"""Entry point."""
import globalvar
from system import init_system
from inputmanager import InputManager


def main():
    init_system()
    im = InputManager()
    print("Food Delivery Dispatch Simulator. Type help.")
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
