"""Shared logging helpers for the site framework."""

import logging


class _TracebackFilter(logging.Filter):
    """Strip exception tracebacks from records unless debug output is on.

    Recoverable errors are logged with ``logger.exception`` in a number of
    places; by default we want the concise message, not a wall of traceback.
    Running with ``--debug`` keeps the full traceback.
    """

    def __init__(self, show_tracebacks: bool) -> None:
        super().__init__()
        self.show_tracebacks = show_tracebacks

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.show_tracebacks:
            record.exc_info = None
            record.exc_text = None
        return True


def configure_logging(debug: bool = False) -> None:
    """Configure framework logging.

    Debug output (including tracebacks) is disabled by default.
    """
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(level=level, format='[%(levelname)s] %(name)s: %(message)s')

    root = logging.getLogger()
    for handler in root.handlers:
        handler.filters = [
            f for f in handler.filters if not isinstance(f, _TracebackFilter)
        ]
        handler.addFilter(_TracebackFilter(debug))
