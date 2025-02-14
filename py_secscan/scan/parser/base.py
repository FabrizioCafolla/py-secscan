import json
import os
from dataclasses import asdict, dataclass

import jsonschema
import jsonschema.exceptions
import yaml

from py_secscan import stdx


def load_schema(version: str):
    schema_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f"v{version}",
        "pysecscan.schema.json",
    )

    if not os.path.isfile(schema_path):
        stdx.exception(FileNotFoundError(f"File {schema_path} not found"))

    try:
        with open(schema_path) as f:
            return json.load(f)
    except Exception as e:
        stdx.exception(f"Failed to load jsonschema file: {str(e)}")


def jsonschema_validate(version: str, data: dict):
    schema = load_schema(version)
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.exceptions.ValidationError as e:
        stdx.exception(e)
    except jsonschema.exceptions.SchemaError as e:
        stdx.exception(e)


class ParserDataclassBase:
    def __post_init__(self):
        """The validation is performed by calling a function named:
        `validate_<field_name>(self, value, field) -> field.type`
        """
        for field_name in self.__dataclass_fields__:
            if method := getattr(self, f"validate_{field_name}", None):
                setattr(self, field_name, method(getattr(self, field_name)))

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParserBase(ParserDataclassBase):
    version: str
    jsonschema: str

    def __post_init__(self):
        super().__post_init__()

    def execute(self):
        raise NotImplementedError

    @classmethod
    def load_config(cls, data: dict = None, py_secscan_config_filename: str = None) -> "ParserBase":
        if py_secscan_config_filename:
            if not os.path.isfile(py_secscan_config_filename):
                raise FileNotFoundError(f"File {py_secscan_config_filename} not found")

            with open(py_secscan_config_filename) as f:
                data = yaml.safe_load(f)

        if data is None:
            stdx.exception(ValueError("Either data or py_secscan_config_filename must be provided"))

        jsonschema_validate(cls.version, data)

        return cls(**data)
