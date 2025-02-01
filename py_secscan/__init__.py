import argparse
import os

from py_secscan.cli import runtime
from py_secscan import settings, utils
from py_secscan.modules import sbom


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

        py_secscan_configuration = runtime.loader(args.config_filename)

        py_secscan_configuration.execute()
        sbom.create_sbom()

    except KeyboardInterrupt as e:
        utils.exception(e)
    except Exception as e:
        utils.exception(e)

    return 0
