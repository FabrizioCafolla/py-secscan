import os
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml
import jsonschema
import json

from py_secscan import stdx


class SchemaLoader:
    _schema = None

    @classmethod
    def load_schema(cls, schema_filename: str):
        if cls._schema is None:
            schema_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), schema_filename
            )

            try:
                with open(schema_path, "r") as f:
                    cls._schema = json.load(f)
            except Exception as e:
                stdx.exception(f"Failed to load jsonschema file: {str(e)}")

        return cls._schema

    @classmethod
    def validate(cls, schema_filename: str, instance: dict):
        schema = cls.load_schema(schema_filename)
        try:
            jsonschema.validate(instance=instance, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            stdx.exception(f"Configuration validation failed: {str(e)}")


class ParserDataclassBase:
    def __post_init__(self):
        """The validation is performed by calling a function named:
        `validate_<field_name>(self, value, field) -> field.type`
        """
        for field_name, _ in self.__dataclass_fields__.items():
            if method := getattr(self, f"validate_{field_name}", None):
                setattr(self, field_name, method(getattr(self, field_name)))

    def __dict__(self) -> dict:
        return asdict(self)


@dataclass
class PySecScanConfigBase(ParserDataclassBase):
    version: str
    jsonschema: str

    def __post_init__(self):
        super().__post_init__()

    def execute(self):
        raise NotImplementedError

    @classmethod
    def from_yaml(cls, py_secscan_config_filename: Path) -> "PySecScanConfigBase":
        if not os.path.isfile(py_secscan_config_filename):
            raise FileNotFoundError(f"File {py_secscan_config_filename} not found")

        with open(py_secscan_config_filename) as f:
            data = yaml.safe_load(f)

        SchemaLoader.validate(cls.jsonschema, data)

        return cls(**data)
