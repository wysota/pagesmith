"""Allow running the package with ``python -m pagesmith``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
