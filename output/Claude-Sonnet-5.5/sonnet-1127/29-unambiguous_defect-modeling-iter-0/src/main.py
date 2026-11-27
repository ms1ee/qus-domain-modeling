"""Entry point."""
import system
from input_manager import InputManager


def main():
    system.init_system()
    print("Commands: start rx ry cx cy | status | orders | riders | quit")
    InputManager().loop()
    try:
        system.save()
    except OSError:
        pass


if __name__ == "__main__":
    main()
