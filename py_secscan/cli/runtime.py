from py_secscan.cli.parser import Parser
from py_secscan import settings
from py_secscan import stdx

import argparse
import os


class StoreVerbosityParser(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if option_string == "-vv":
            values = "2"
        elif option_string == "-vvv":
            values = "3"
        else:
            values = "1"

        settings.setenv("PY_SECSCAN_VERBOSITY", values, overwrite=True)
        setattr(namespace, self.dest, values)


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
            action=StoreVerbosityParser,
            type=str,
            nargs=0,
            help="Verbosity level",
        )

        argument_parser.add_argument(
            "-vv",
            action=StoreVerbosityParser,
            type=str,
            nargs=0,
            help="Verbosity level",
        )

        argument_parser.add_argument(
            "-vvv",
            action=StoreVerbosityParser,
            type=str,
            nargs=0,
            help="Verbosity level",
        )
        args = argument_parser.parse_args()

        parser = Parser(args.config_filename)
        config = parser.config
        config.execute()
    except KeyboardInterrupt as e:
        stdx.exception(e)
    except Exception as e:
        stdx.exception(e)

    return 0
