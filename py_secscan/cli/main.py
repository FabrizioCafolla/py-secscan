import sys
import os
import subprocess
import shlex
from py_secscan.cli import configuration_parser, settings, utils


def setup_venv(
    packages: list[configuration_parser.ModuleConfig], venv_dirpath: str
) -> None:
    def create_requirements_txt(packages) -> None:
        with open(
            f"{settings.DEFAULT_ENV['PY_SECSCAN_PATH']}/requirements.txt", "w"
        ) as f:
            for package in packages:
                line = (
                    f"{package.name}=={package.version}"
                    if package.version
                    else package.name
                )
                f.write(f"{line}\n")

    def install_packages() -> None:
        command = (
            f"pip install -r {settings.DEFAULT_ENV['PY_SECSCAN_PATH']}/requirements.txt"
        )
        subprocess.check_call(
            shlex.split(command),
        )
        utils.info("Packages installed")

    def create_venv() -> None:
        if os.path.isdir(venv_dirpath):
            return

        subprocess.check_call(
            shlex.split(f"python -m venv {venv_dirpath}"),
        )
        utils.warning(
            f"Virtualenv created: run 'source {venv_dirpath}/bin/activate' to activate it"
        )
        sys.exit(0)

    create_venv()
    create_requirements_txt(packages)
    install_packages()

    # Create a .gitignore file in the root directory if it does not exist, and add the exclusion line if not already present
    if not os.path.isfile(".gitignore"):
        gitignore = []
    else:
        with open(".gitignore", "r") as f:
            gitignore = f.read().splitlines()

    exclude_filepath = f"{settings.PY_SECSCAN_DIRNAME}/"
    if exclude_filepath not in gitignore:
        gitignore.append(exclude_filepath)

    with open(".gitignore", "w") as f:
        f.write("\n".join(gitignore))


def load_project_conf() -> configuration_parser.PySecScanConfig:
    try:
        if not os.path.isfile(settings.DEFAULT_ENV["PY_SECSCAN_CONFIG_FILENAME"]):
            utils.exception(
                message=f"File {settings.DEFAULT_ENV['PY_SECSCAN_CONFIG_FILENAME']} not found"
            )

        project_settings = configuration_parser.PySecScanConfig.from_yaml(
            settings.DEFAULT_ENV["PY_SECSCAN_CONFIG_FILENAME"]
        )

        settings.setenv_from_dict(overwrite=True, **project_settings.env)
    except FileNotFoundError as e:
        utils.exception(e)

    return project_settings


def run(package_name: str, args: list[str]) -> None:
    try:
        subprocess.check_call(
            shlex.split(f"{package_name} {' '.join(args)}"),
        )
        return 0
    except subprocess.CalledProcessError as e:
        utils.warning(f"Error running {package_name}: {e}")
        return e.returncode


def main() -> bool:
    try:
        settings.load_default_conf()

        project_settings = load_project_conf()

        setup_venv(
            project_settings.packages,
            project_settings.venv_dirpath,
        )

        for package in project_settings.packages:
            settings.RUNTIME_EXCUTION_STATUS.update(
                package.name, settings.RunTimeAllowedExecutionStatus.RUNNING
            )

            if not package.enabled:
                utils.warning(f"{package.name} package is disabled")
                settings.RUNTIME_EXCUTION_STATUS.update(
                    package.name, settings.RunTimeAllowedExecutionStatus.DISABLED
                )
                continue

            utils.info(f"Running {package.name}")

            returncode = run(package.name, package.args)

            if returncode == 0:
                utils.info(f"Package {package.name} completed")
                settings.RUNTIME_EXCUTION_STATUS.update(
                    package.name, settings.RunTimeAllowedExecutionStatus.COMPLETED
                )
                continue

            settings.RUNTIME_EXCUTION_STATUS.update(
                package.name, settings.RunTimeAllowedExecutionStatus.FAILED
            )
            if not package.on_error_continue:
                utils.exception(
                    message=f"Error {package.name} package returncode: {returncode}"
                )
    except KeyboardInterrupt as e:
        utils.exception(e)
    except Exception as e:
        utils.exception(e)
    finally:
        utils.info(settings.RUNTIME_EXCUTION_STATUS)

    return 0


if __name__ == "__main__":
    sys.exit(main())
