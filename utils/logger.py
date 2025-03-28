import logging
import sys

# Configure default logger
logger = logging.getLogger("brainrot")


def setup_logger(level=logging.INFO):
    """
    Setup the logger with appropriate formatting and level.

    Args:
        level: Logging level (default: logging.INFO)

    Returns:
        The configured logger
    """
    logger.setLevel(level)

    # Create handler for console output if none exists
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def log_info(message):
    """
    Log an info message.

    Args:
        message: The message to log
    """
    logger.info(message)


def log_error(message):
    """
    Log an error message.

    Args:
        message: The error message to log
    """
    logger.error(message)


# Initialize the logger when module is imported
setup_logger()
