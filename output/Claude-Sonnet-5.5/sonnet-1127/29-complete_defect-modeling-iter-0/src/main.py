"""Entry point: python src/main.py"""
import globalvar
import system
from input_manager import InputManager


def main():
    system.init_system()
    im = InputManager()
    print("Commands: start x1 y1 x2 y2 | status | orders | riders | "
          "tick [n] | history | quit")
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


if __name__ == "__main__":
    main()
