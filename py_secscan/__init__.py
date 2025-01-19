import argparse
import os

from py_secscan.parser import parser
from py_secscan import settings, utils


def main() -> bool:
    try:
        settings.load_env()

        argument_parser = argparse.ArgumentParser(description="PySecScan")
        argument_parser.add_argument(
            "--conf-filename",
            required=False,
            help="Path to the configuration file",
            default=os.environ["PY_SECSCAN_CONFIG_FILENAME"],
        )
        args = argument_parser.parse_args()

        project_configuration = parser.build(args.conf_filename)

        project_configuration.execute()
    except KeyboardInterrupt as e:
        utils.exception(e)
    except Exception as e:
        utils.exception(e)

    return 0
