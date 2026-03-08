import logging
import sys

LOG_FORMAT = "%(levelname)s %(name)s: %(message)s"
DEBUG_FORMAT = "%(levelname)s %(name)s:%(funcName)s: %(message)s"


def setup_logging(verbosity: int) -> None:
    """Configure logging based on verbosity level.

    0 (default): WARNING
    1 (-v):      INFO for musictl
    2 (-vv):     DEBUG for musictl
    3 (-vvv):    DEBUG for everything (including libraries)
    """
    if verbosity >= 3:
        level = logging.DEBUG
        fmt = DEBUG_FORMAT
        logging.basicConfig(level=level, format=fmt, stream=sys.stderr)
    elif verbosity >= 2:
        level = logging.DEBUG
        fmt = DEBUG_FORMAT
        logging.basicConfig(level=logging.WARNING, format=fmt, stream=sys.stderr)
        logging.getLogger("musictl").setLevel(level)
    elif verbosity >= 1:
        level = logging.INFO
        fmt = LOG_FORMAT
        logging.basicConfig(level=logging.WARNING, format=fmt, stream=sys.stderr)
        logging.getLogger("musictl").setLevel(level)
    else:
        logging.basicConfig(level=logging.WARNING, format=LOG_FORMAT, stream=sys.stderr)
