"""
core/logger.py
Structured logger — all agent logs go through here.
"""
import logging
import sys
import os


def get_logger(name: str) -> logging.Logger:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        logger.addHandler(handler)

    logger.setLevel(getattr(logging, log_level, logging.INFO))
    return logger