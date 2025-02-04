import os

from py_secscan.settings import LOGGER
from typing import List

try:
    from distutils.version import LooseVersion
except ModuleNotFoundError:
    from packaging.version import parse as LooseVersion


class PySecScanBaseException(Exception):
    pass


class ParserPackageExecutionException(PySecScanBaseException):
    def __init__(
        self,
        package_name: str,
        package_args: List[str],
        command: list[str] = None,
        *args,
        **kwargs,
    ):
        self.package = package_name
        self.args = args
        self.command = " ".join(command) if command else None
        self.message = (
            f"Error executing package {package_name} with args {package_args}"
            + (f"\n{self.command}" if self.command else "")
        )
        super().__init__(self.message, *args, **kwargs)


def verbose(level: str):
    import functools

    def actual_decorator(func):
        def neutered(*args, **kw):
            return

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return (
                func(*args, **kwargs)
                if LooseVersion(str(level))
                <= LooseVersion(os.environ["PY_SECSCAN_VERBOSITY"])
                else neutered
            )

        return wrapper

    return actual_decorator


@verbose(level=2)
def info(message: str) -> None:
    LOGGER.info(message)
    print("[INFO]", message)


@verbose(level=3)
def debug(message: str) -> None:
    LOGGER.debug(message)
    print("[DEBUG]", message)


@verbose(level=1)
def warning(message: str) -> None:
    LOGGER.warning(message)
    print("[WARNING]", message)


@verbose(level=0)
def error(message: str) -> None:
    LOGGER.error(message)
    print("[ERROR]", message)


@verbose(level=0)
def critical(message: str) -> None:
    LOGGER.critical(message)
    print("[CRITICAL]", message)


@verbose(level=0)
def exception(exception: Exception = None, message: str = "") -> None:
    if exception:
        LOGGER.exception(str(exception))
        raise exception

    LOGGER.exception(message)
    raise PySecScanBaseException(message)
