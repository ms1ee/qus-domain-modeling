"""Entry point."""
import globalvar
from system import SystemManager
from inputmgr import InputManager


def main():
    system = SystemManager()
    im = InputManager(system)
    print("Food Delivery Dispatch. Commands: start, status, orders, "
          "riders, tick [n], save, quit")
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        try:
            out = im.execute(line)
            if out:
                print(out)
        except ValueError as e:
            print("Error: %s" % e)
        except Exception as e:  # recover gracefully
            print("Unexpected error: %s" % e)
        if globalvar.get_value("running") and line.strip() and \
                not line.strip().lower().startswith(("tick", "t ", "t")):
            system.tick()


if __name__ == "__main__":
    main()
