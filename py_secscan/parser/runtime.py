from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Optional
from py_secscan import settings


class RunTimeAllowedExecutionStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class RunTimeExecutionStatus:
    logger_filepath: Optional[str] = field(default=settings.LOGGER_FILEPATH)
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
        return asdict(self)

    def __str__(self) -> str:
        return str(self.to_dict())


RUNTIME_EXCUTION_STATUS = RunTimeExecutionStatus()
