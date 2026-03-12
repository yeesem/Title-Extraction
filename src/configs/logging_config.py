import logging
import sys

def setup_logging(level=logging.INFO):
    """
    Configure logging for the application.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_logger(name):
    """
    Get a logger with the specified name.
    """
    return logging.getLogger(name)
