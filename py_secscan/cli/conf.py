import os
import logging
from datetime import datetime

CURRENT_DIRPATH = os.getcwd()
PY_SECSCAN_DIRNAME = ".py-secscan"

DEFAULT_ENV = {
    "PY_SECSCAN_CONFIG_FILENAME": ".py-secscan.conf.yml",
    "PY_SECSCAN_PATH": os.path.join(f"{CURRENT_DIRPATH}/{PY_SECSCAN_DIRNAME}"),
    "PY_SECSCAN_LOGGING_PATH": os.path.join(
        f"{CURRENT_DIRPATH}/{PY_SECSCAN_DIRNAME}/logs"
    ),
    "PY_SECSCAN__LOGGING_NAME": "main",
    "PY_SECSCAN_LOGGING_FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "PY_SECSCAN_DATA": str(datetime.now().strftime("%Y-%m-%d")),
    "PY_SECSCAN_DATATIME_START": str(datetime.now().strftime("%Y-%m-%d %H:%m:%s")),
}


def get_logging_filepath() -> str:
    return os.path.join(
        f"{DEFAULT_ENV['PY_SECSCAN_LOGGING_PATH']}/{DEFAULT_ENV['PY_SECSCAN__LOGGING_NAME']}.{DEFAULT_ENV['PY_SECSCAN_DATA']}.log"
    )


def get_logging_level() -> list:
    return ["info", "warning", "error", "debug", "critical", "exception"]


def setenv(key: str, value: str, overwrite: bool = False) -> None:
    if not isinstance(key, str):
        raise Exception("ENVIRON KEY is not str")

    if not isinstance(value, str):
        value = str(value)

    key = key.upper()

    if key in os.environ.keys() and overwrite is False:
        return

    os.environ[key] = value


def setenv_from_dict(overwrite: bool = False, **kargs) -> None:
    for key, value in kargs.items():
        if isinstance(kargs[key], str):
            setenv(key, value, overwrite)
            continue

        if isinstance(kargs[key], dict):
            [setenv(key + "_" + k, v, overwrite) for k, v in kargs[key].items()]

        raise Exception(f"Error load env var: {key}={str(value)}")


def load_default_env() -> None:
    setenv_from_dict(overwrite=False, **DEFAULT_ENV)


try:
    LOGGER = logging.getLogger(DEFAULT_ENV["PY_SECSCAN__LOGGING_NAME"])
    os.makedirs(DEFAULT_ENV["PY_SECSCAN_LOGGING_PATH"], exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG,
        format=DEFAULT_ENV["PY_SECSCAN_LOGGING_FORMAT"],
        filename=get_logging_filepath(),
    )
except Exception as e:
    print(str(e))
    exit(1)


def _get_logger(logger_name: str = None) -> object:
    if logger_name is None:
        return LOGGER
    return logging.getLogger(logger_name)


def info(message: str, logger_name: str = None) -> None:
    _get_logger(logger_name).info(message)


def debug(message: str, logger_name: str = None) -> None:
    _get_logger(logger_name).debug(message)


def warning(message: str, logger_name: str = None) -> None:
    _get_logger(logger_name).warning(message)


def error(message: str, logger_name: str = None) -> None:
    _get_logger(logger_name).error(message)


def critical(message: str, logger_name: str = None) -> None:
    _get_logger(logger_name).critical(message)


def exception(message: str = "", logger_name: str = None) -> None:
    _get_logger(logger_name).exception(message)
