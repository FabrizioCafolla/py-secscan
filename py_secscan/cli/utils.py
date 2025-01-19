from py_secscan.cli.settings import LOGGER


class PySecScanException(Exception):
    pass


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


def exception(exception: Exception = None, message: str = "") -> None:
    if exception:
        LOGGER.exception(str(exception))
        raise exception

    LOGGER.exception(message)
    raise PySecScanException(message)
