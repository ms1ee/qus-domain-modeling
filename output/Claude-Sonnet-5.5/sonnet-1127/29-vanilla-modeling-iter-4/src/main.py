"""Entry point: each loop iteration is one tick."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from input_manager import InputManager  # noqa: E402
from system import SystemManager  # noqa: E402


def main():
    system = SystemManager()
    im = InputManager(system)
    while system.running:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        try:
            out = im.handle(line)
        except Exception as e:  # graceful recovery
            out = "Error: %s" % e
        if out:
            print(out)
        system.step()
    try:
        system.save()
    except OSError:
        pass


if __name__ == "__main__":
    main()
