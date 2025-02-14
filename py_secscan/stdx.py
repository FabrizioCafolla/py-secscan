import os
import sys
from argparse import Action

from py_secscan.settings import DEFAULT_ENV, LOGGER, set_debug_mode


try:
    from distutils.version import LooseVersion
except ModuleNotFoundError:
    from packaging.version import parse as LooseVersion  # noqa: N812


class PySecScanBaseError(Exception):
    pass


class PySecScanSanitizeCommandError(PySecScanBaseError):
    pass


class PySecScanVirtualVenvNotLoadedError(PySecScanBaseError):
    def __init__(self, venv_dirpath: str, *args, **kwargs):
        self.message = f"Virtualenv not loaded: run 'source {venv_dirpath}/bin/activate' to activate it"
        super().__init__(self.message, *args, **kwargs)


class ParserPackageExecutionError(PySecScanBaseError):
    def __init__(
        self,
        package_name: str,
        package_args: list[str],
        command: list[str] = None,
        *args,
        **kwargs,
    ):
        self.package = package_name
        self.args = args
        self.command = " ".join(command) if command else None
        self.message = f"Error executing package {package_name} with args {package_args}" + (
            f"\n{self.command}" if self.command else ""
        )
        super().__init__(self.message, *args, **kwargs)


class StoreVerbosityParser(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if option_string == "-v":
            values = "2"
            set_debug_mode()
        if option_string == "-vv":
            values = "2"
            set_debug_mode()
            sys.tracebacklimit = 1

        setattr(namespace, self.dest, values)


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
                <= LooseVersion(os.getenv("PY_SECSCAN_VERBOSITY", DEFAULT_ENV["PY_SECSCAN_VERBOSITY"]))
                else neutered
            )

        return wrapper

    return actual_decorator


@verbose(level=2)
def debug(message: str) -> None:
    LOGGER.debug(message)
    print("[DEBUG]", message)  # noqa: T201


@verbose(level=1)
def info(message: str) -> None:
    LOGGER.info(message)
    print("[INFO]", message)  # noqa: T201


@verbose(level=1)
def warning(message: str) -> None:
    LOGGER.warning(message)
    print("[WARNING]", message)  # noqa: T201


@verbose(level=1)
def error(message: str) -> None:
    LOGGER.error(message)
    print("[ERROR]", message)  # noqa: T201


@verbose(level=1)
def critical(message: str) -> None:
    LOGGER.critical(message)
    print("[CRITICAL]", message)  # noqa: T201


@verbose(level=1)
def exception(exception: Exception = None, message: str = "") -> None:
    if exception:
        LOGGER.exception(str(exception))
        raise exception

    LOGGER.exception(message)
    raise PySecScanBaseError(message)
