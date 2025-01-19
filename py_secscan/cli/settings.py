import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

CURRENT_DIRPATH = os.getcwd()
PY_SECSCAN_DIRNAME = ".py-secscan"

DEFAULT_ENV = {
    "PY_SECSCAN_CONFIG_FILENAME": ".py-secscan.conf.yml",
    "PY_SECSCAN_PATH": os.path.join(f"{CURRENT_DIRPATH}/{PY_SECSCAN_DIRNAME}"),
    "PY_SECSCAN_LOGGING_PATH": os.path.join(
        f"{CURRENT_DIRPATH}/{PY_SECSCAN_DIRNAME}/logs"
    ),
    "PY_SECSCAN__LOGGING_NAME": "py-secscan",
    "PY_SECSCAN_LOGGING_FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "PY_SECSCAN_DATA": str(datetime.now().strftime("%Y-%m-%d")),
    "PY_SECSCAN_DATATIME_START": str(datetime.now().strftime("%Y-%m-%d %H:%m:%s")),
    "PY_SECSCAN_DEBUG": "0",
}

LOGGER = logging.getLogger(DEFAULT_ENV["PY_SECSCAN__LOGGING_NAME"])
LOGGER_FILEPATH = os.path.join(
    f"{DEFAULT_ENV['PY_SECSCAN_LOGGING_PATH']}/{DEFAULT_ENV['PY_SECSCAN__LOGGING_NAME']}.{DEFAULT_ENV['PY_SECSCAN_DATA']}.log"
)


class RunTimeAllowedExecutionStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class RunTimeExecutionStatus:
    logger_filepath: Optional[str] = field(default=LOGGER_FILEPATH)
    status: Optional[Dict] = field(default_factory=dict)

    def update(self, key: str, value: RunTimeAllowedExecutionStatus) -> None:
        if not isinstance(key, str):
            raise Exception("Key param is not str")

        if value.value not in RunTimeAllowedExecutionStatus:
            raise Exception(
                f"Value param is not allowed. Allowed values: {RunTimeAllowedExecutionStatus}"
            )

        self.status[key] = value.value

    def to_dict(self) -> Dict:
        return {"logger_filepath": self.logger_filepath, "status": self.status}

    def __str__(self) -> str:
        return str(self.to_dict())


RUNTIME_EXCUTION_STATUS = RunTimeExecutionStatus()


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


def load_env() -> None:
    setenv_from_dict(overwrite=False, **DEFAULT_ENV)
    try:
        os.makedirs(DEFAULT_ENV["PY_SECSCAN_LOGGING_PATH"], exist_ok=True)
        logging.basicConfig(
            level=logging.DEBUG,
            format=DEFAULT_ENV["PY_SECSCAN_LOGGING_FORMAT"],
            filename=LOGGER_FILEPATH,
        )
    except Exception as e:
        print(str(e))
        exit(1)
