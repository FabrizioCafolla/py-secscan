from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
import yaml
import os
from pathlib import Path

# JSON Schema for the configuration file
# {
#   "$schema": "https://json-schema.org/draft/2019-09/schema",
#   "id": "py_secscan_spec.json",
#   "title": "PySecScan Specification",
#   "description": "The PySecScan specification is a JSON schema that describes the structure of the PySecScan configuration file.",
#   "properties": {
#     "env": { "$ref": "#/definitions/dict_of_str" },
#     "venv_dirpath": {
#       "type": "string",
#       "description": "The directory path to the virtual environment."
#     },
#     "packages": {
#       "type": "array",
#       "items": [
#         {
#           "type": "object",
#           "properties": {
#             "name": { "type": "string" },
#             "args": {
#               "type": "array",
#               "items": [{ "type": "string" }, { "type": "string" }]
#             }
#           },
#           "required": ["name"]
#         }
#       ],
#       "additionalProperties": false,
#       "minProperties": 0
#     }
#   },
#   "definitions": {
#     "dict_of_str": {
#       "id": "#/definitions/dict_of_str",
#       "type": "object",
#       "items": { "type": "string" }
#     }
#   },
#   "additionalProperties": false,
#   "required": ["packages"]
# }


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
