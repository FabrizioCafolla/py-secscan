import logging
import os
import sys
from datetime import datetime


CURRENT_DIRPATH = os.getcwd()
PY_SECSCAN_DIRNAME = ".py-secscan"
VEVN_DIRNAME = ".venv"

DEFAULT_ENV = {
    "PY_SECSCAN_CONFIG_FILENAME": ".py-secscan.conf.yml",
    "PY_SECSCAN_PATH": os.path.join(f"{CURRENT_DIRPATH}/{PY_SECSCAN_DIRNAME}"),
    "PY_SECSCAN_VENV": os.path.join(f"{CURRENT_DIRPATH}/{VEVN_DIRNAME}"),
    "PY_SECSCAN_LOGGING_PATH": os.path.join(f"{CURRENT_DIRPATH}/{PY_SECSCAN_DIRNAME}/logs"),
    "PY_SECSCAN__LOGGING_NAME": "py-secscan",
    "PY_SECSCAN_LOGGING_FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "PY_SECSCAN_DATA": str(datetime.now().strftime("%Y-%m-%d")),
    "PY_SECSCAN_DATATIME_START": str(datetime.now().strftime("%Y-%m-%d %H:%m:%s")),
    "PY_SECSCAN_DEBUG": "0",
    "PY_SECSCAN_VERBOSITY": "1",
}

LOGGER = logging.getLogger(DEFAULT_ENV["PY_SECSCAN__LOGGING_NAME"])
LOGGER_FILEPATH = os.path.join(
    f"{DEFAULT_ENV['PY_SECSCAN_LOGGING_PATH']}/{DEFAULT_ENV['PY_SECSCAN__LOGGING_NAME']}.{DEFAULT_ENV['PY_SECSCAN_DATA']}.log"
)


def setenv(key: str, value: str, overwrite: bool = False) -> None:
    if not isinstance(key, str):
        raise Exception("ENVIRON KEY is not str")

    if not isinstance(value, str):
        value = str(value)

    key = key.upper()

    if key in os.environ and overwrite is False:
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


def load_env() -> None:
    setenv_from_dict(overwrite=False, **DEFAULT_ENV)
    setenv("PY_SECSCAN_LOGGING_FILEPATH", LOGGER_FILEPATH, overwrite=True)

    try:
        os.makedirs(os.environ["PY_SECSCAN_LOGGING_PATH"], exist_ok=True)
        logging.basicConfig(
            level=logging.DEBUG,
            format=os.environ["PY_SECSCAN_LOGGING_FORMAT"],
            filename=os.environ["PY_SECSCAN_LOGGING_FILEPATH"],
        )
        sys.tracebacklimit = 0
    except Exception as e:
        print(str(e))  # noqa: T201
        sys.exit(1)


def set_debug_mode() -> None:
    setenv("PY_SECSCAN_DEBUG", "1", overwrite=True)
    setenv("PY_SECSCAN_VERBOSITY", "2", overwrite=True)
    LOGGER.debug("Debug mode enabled")
