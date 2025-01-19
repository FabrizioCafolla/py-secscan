from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
import yaml
import os
from pathlib import Path


@dataclass
class ModuleConfig:
    name: str
    enabled: Optional[bool] = True
    version: Optional[str] = None
    args: Optional[List[str]] = field(default_factory=list)
    on_error_continue: Optional[bool] = True


@dataclass
class PySecScanConfig:
    env: Optional[Dict[str, str]] = field(default_factory=dict)
    venv_dirpath: Optional[str] = field(default=".venv")
    packages: Optional[List[ModuleConfig]] = None

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "PySecScanConfig":
        yaml_path = Path(yaml_path)
        if not os.path.isfile(yaml_path):
            raise FileNotFoundError(f"File {yaml_path} not found")

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        if "packages" in data:
            data["packages"] = [ModuleConfig(**module) for module in data["packages"]]

        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)
