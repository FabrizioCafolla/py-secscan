import argparse
import os

from py_secscan import settings, stdx
from py_secscan.scan import scan
from py_secscan.view import view


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="""PySecScan is a lightweight and easy-to-use security scanning tool for Python projects. \\
        With a simple YAML configuration, it seamlessly integrates into any workflow, regardless of the framework or dependencies used."""
    )
    parser.add_argument(
        "-v",
        action=stdx.StoreVerbosityParser,
        type=str,
        nargs=0,
        help="Change verbosity level to level: DEBUG",
    )

    parser.add_argument(
        "-vv",
        action=stdx.StoreVerbosityParser,
        type=str,
        nargs=0,
        help="Change verbosity level to level: DEBUG with traceback",
    )

    subparsers = parser.add_subparsers(dest="command", help="PySecScan commands")

    view_parser = subparsers.add_parser(
        "view",
        help="Start the web application to view the sbom file and vulnerabilities",
    )

    view_parser.add_argument("-s", "--sbom-filepath", type=str, default="sbom.json", help="SBOM file path")
    view_parser.add_argument(
        "-v",
        "--vulnerabilities-filepath",
        type=str,
        default="sbom_vulnerabilities.json",
        help="SBOM Vulnerabilities file path",
    )

    scan_parser = subparsers.add_parser("scan", help="Execute the security scan using the configuration")
    scan_parser.add_argument(
        "-c",
        "--config-filename",
        required=False,
        help="Configuration filename",
        default=os.environ["PY_SECSCAN_CONFIG_FILENAME"],
    )

    return parser.parse_args()


def main() -> bool:
    try:
        settings.load_env()

        args = parse_args()

        if args.command == "view":
            view.start(args.sbom_filepath, args.vulnerabilities_filepath)
            return 0

        if args.command == "scan":
            builder = scan.ScanBuilder(args.config_filename)
            builder.execute()
            return 0

        stdx.exception(ValueError(f"Command {args.command} not found. Run with --help for more information"))
    except KeyboardInterrupt:
        stdx.warning("Manual interruption")
    except Exception as e:
        stdx.exception(e)

    return 0
