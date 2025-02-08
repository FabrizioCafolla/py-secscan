from py_secscan.cli.parser_base import PySecScanConfigBase
from py_secscan.cli.parser_config_v1 import PySecScanConfigV1

from py_secscan import settings
from py_secscan import stdx

import argparse
import os
import yaml


class ParserBuilder:
    parser_versions = {
        "1": PySecScanConfigV1,
    }

    py_secscan_config_filename: str
    py_secscan_config: PySecScanConfigBase

    @property
    def instance(self) -> PySecScanConfigBase:
        return self.py_secscan_config

    def __init__(self, py_secscan_config_filename: str) -> None:
        if not os.path.isfile(py_secscan_config_filename):
            raise FileNotFoundError(f"File {py_secscan_config_filename} not found")

        self.py_secscan_config_filename = py_secscan_config_filename

        self.py_secscan_config = self.build()

    def build(self) -> PySecScanConfigBase:
        try:
            if not os.path.isfile(self.py_secscan_config_filename):
                raise FileNotFoundError(
                    f"File {self.py_secscan_config_filename} not found"
                )

            with open(self.py_secscan_config_filename) as f:
                data = yaml.safe_load(f)

            if "version" not in data:
                raise ValueError("Version not found in the configuration file")

            if data["version"] not in self.parser_versions:
                raise ValueError(f"Version {data['version']} not supported")

            return (self.parser_versions[data["version"]]).from_yaml(
                self.py_secscan_config_filename
            )
        except FileNotFoundError as e:
            stdx.exception(e)
        except Exception as e:
            stdx.exception(e)


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

        argument_parser.add_argument(
            "-v",
            action=stdx.StoreVerbosityParser,
            type=str,
            nargs=0,
            help="Verbosity level",
        )

        argument_parser.add_argument(
            "-vv",
            action=stdx.StoreVerbosityParser,
            type=str,
            nargs=0,
            help="Verbosity level",
        )

        argument_parser.add_argument(
            "-vvv",
            action=stdx.StoreVerbosityParser,
            type=str,
            nargs=0,
            help="Verbosity level",
        )
        args = argument_parser.parse_args()

        parser = ParserBuilder(args.config_filename)
        py_secscan = parser.instance
        py_secscan.execute()
    except KeyboardInterrupt as e:
        stdx.exception(e)
    except Exception as e:
        stdx.exception(e)

    return 0
