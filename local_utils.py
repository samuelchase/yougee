"""
Helpful utilities for working locally with nearwoo
"""
import logging


def initialize_logging(level=logging.WARNING):
    if isinstance(level, basestring):
        level = getattr(logging, level.upper())
    logging.basicConfig()
    logging.getLogger().setLevel(level)
