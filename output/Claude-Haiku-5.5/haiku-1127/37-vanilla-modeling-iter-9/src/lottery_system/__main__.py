"""Allow running the package with: python -m lottery_system (with src/ on sys.path)."""

from lottery_system.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
