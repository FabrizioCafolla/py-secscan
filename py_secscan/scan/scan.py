import os

import yaml

from py_secscan import stdx
from py_secscan.scan.parser.base import ParserBase
from py_secscan.scan.parser.v1.parser import ParserV1


class ScanBuilder:
    py_secscan_config_filename: str
    parser: ParserBase

    def __init__(self, py_secscan_config_filename: str) -> None:
        if not os.path.isfile(py_secscan_config_filename):
            raise FileNotFoundError(f"File {py_secscan_config_filename} not found")

        self.py_secscan_config_filename = py_secscan_config_filename

        self.parser = self.build()

    @classmethod
    def get_parser_versions(cls) -> dict[str, ParserBase]:
        return {
            "1": ParserV1,
        }

    def build(self) -> ParserBase:
        if not os.path.isfile(self.py_secscan_config_filename):
            stdx.exception(FileNotFoundError(f"File {self.py_secscan_config_filename} not found"))

        with open(self.py_secscan_config_filename) as f:
            data = yaml.safe_load(f)

        if "version" not in data:
            stdx.exception(ValueError("Version not found in the configuration file"))

        allowed_parser_versions = self.get_parser_versions()

        if data["version"] not in allowed_parser_versions:
            stdx.exception(ValueError(f"Version {data['version']} not supported"))

        parser = allowed_parser_versions[data["version"]]

        return parser.load_config(
            data=data,
        )

    def execute(self) -> None:
        if self.parser is None:
            stdx.error(ValueError("Parser not found"))
            return

        self.parser.execute()
