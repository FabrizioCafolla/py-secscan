from py_secscan.cli.settings import LOGGER


def info(message: str) -> None:
    LOGGER.info(message)
    print("[INFO]", message)


def debug(message: str) -> None:
    LOGGER.debug(message)
    print("[DEBUG]", message)


def warning(message: str) -> None:
    LOGGER.warning(message)
    print("[WARNING]", message)


def error(message: str) -> None:
    LOGGER.error(message)
    print("[ERROR]", message)


def critical(message: str) -> None:
    LOGGER.critical(message)
    print("[CRITICAL]", message)


def exception(e: Exception, message: str = "") -> None:
    LOGGER.exception(message)
    print("[EXCEPTION]", message)
    raise e
