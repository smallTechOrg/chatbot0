"""Logging setup. Every module logs through ``logging.getLogger(__name__)``; this configures where it goes."""

import logging
import os
import sys

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging() -> None:
    """
    Send logs to stdout (Cloud Run ships stdout to Cloud Logging). The level comes from LOG_LEVEL (default INFO).
    Safe to call more than once.
    """
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    root = logging.getLogger()
    if any(getattr(h, "_chatbot0", False) for h in root.handlers):
        root.setLevel(level)
        return
    handler = logging.StreamHandler(sys.stdout)
    handler._chatbot0 = True  # type: ignore[attr-defined]
    handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(handler)
    root.setLevel(level)
    # Noisy libraries stay at WARNING whatever LOG_LEVEL says.
    for noisy in ("httpx", "httpcore", "urllib3", "werkzeug"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
