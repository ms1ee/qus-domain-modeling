"""Entry point."""
import globalvar
from system import SystemManager


def main():
    """Run the command loop; each iteration is one tick."""
    sm = SystemManager()
    print("Food Delivery Dispatch. Type help for commands.")
    while globalvar.get_value("running"):
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        try:
            out = sm.handle(line)
        except Exception as e:  # recover gracefully
            out = "Error: %s" % e
        if out:
            print(out)
        sm.tick()
    try:
        sm.save()
    except OSError:
        pass


if __name__ == "__main__":
    main()
