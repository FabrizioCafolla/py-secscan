from py_secscan.cli.parser import Parser
from py_secscan import settings
from py_secscan import utils

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Optional

import argparse
import os


class ExecutionStatusAllowed(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class ExecutionStatus:
    _instance = None
    logger_filepath: Optional[str] = field(default=settings.LOGGER_FILEPATH)
    status: Optional[Dict] = field(default_factory=dict)

    def update(self, key: str, value: ExecutionStatusAllowed) -> None:
        if not isinstance(key, str):
            raise Exception("Key param is not str")

        if value.value not in ExecutionStatusAllowed:
            raise Exception(
                f"Value param is not allowed. Allowed values: {ExecutionStatusAllowed}"
            )

        self.status[key] = value.value

    def to_dict(self) -> Dict:
        return asdict(self)

    def __str__(self) -> str:
        return str(self.to_dict())

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance


def main() -> bool:
    try:
        settings.load_env()

        argument_parser = argparse.ArgumentParser(description="PySecScan")
        argument_parser.add_argument(
            "-c",
            "--config-filename",
            required=False,
            help="Path to the configuration file",
            default=os.environ["PY_SECSCAN_CONFIG_FILENAME"],
        )
        args = argument_parser.parse_args()

        parser = Parser(args.config_filename)
        config = parser.config
        config.execute()
    except KeyboardInterrupt as e:
        utils.exception(e)
    except Exception as e:
        utils.exception(e)

    return 0
