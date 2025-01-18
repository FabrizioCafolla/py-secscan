import sys
import os
import subprocess
import shlex
from py_secscan.cli import conf, parser


def setup_venv(packages: list[parser.ModuleConfig], venv_dirpath: str) -> None:
    def create_requirements_txt(packages) -> None:
        with open(f"{conf.DEFAULT_ENV['PY_SECSCAN_PATH']}/requirements.txt", "w") as f:
            for package in packages:
                line = (
                    f"{package.name}=={package.version}"
                    if package.version
                    else package.name
                )
                f.write(f"{line}\n")

    def install_packages() -> None:
        command = (
            f"pip install -r {conf.DEFAULT_ENV['PY_SECSCAN_PATH']}/requirements.txt"
        )
        subprocess.check_call(
            shlex.split(command),
        )
        print("Packages installed")

    def create_venv() -> None:
        if os.path.isdir(venv_dirpath):
            return

        subprocess.check_call(
            shlex.split(f"python -m venv {venv_dirpath}"),
        )
        print(
            f"Virtualenv created: run 'source {venv_dirpath}/bin/activate' to activate it"
        )
        exit(0)

    create_venv()
    create_requirements_txt(packages)
    install_packages()

    # Create gitignore in root directory if not exist in the .gitignore file add new line
    if not os.path.isfile(".gitignore"):
        gitignore = []
    else:
        with open(".gitignore", "r") as f:
            gitignore = f.read().splitlines()

    exclude_filepath = f"{conf.PY_SECSCAN_DIRNAME}/"
    if exclude_filepath not in gitignore:
        gitignore.append(exclude_filepath)

    with open(".gitignore", "w") as f:
        f.write("\n".join(gitignore))


def load_project_settings() -> parser.PySecScanConfig:
    try:
        if not os.path.isfile(conf.DEFAULT_ENV["PY_SECSCAN_CONFIG_FILENAME"]):
            raise Exception(
                f"File {conf.DEFAULT_ENV['PY_SECSCAN_CONFIG_FILENAME']} not found"
            )

        project_settings = parser.PySecScanConfig.from_yaml(
            conf.DEFAULT_ENV["PY_SECSCAN_CONFIG_FILENAME"]
        )

        conf.setenv_from_dict(overwrite=True, **project_settings.env)
    except FileNotFoundError as e:
        raise e
    except Exception as e:
        raise e
    else:
        return project_settings


def run(package_name: str, args: list[str]) -> None:
    try:
        subprocess.check_call(
            shlex.split(f"{package_name} {' '.join(args)}"),
        )
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error running {package_name}: {e}")
        return e.returncode


def main() -> bool:
    try:
        conf.load_default_env()

        project_settings = load_project_settings()

        setup_venv(
            project_settings.packages,
            project_settings.venv_dirpath,
        )
        status = {}
        for package in project_settings.packages:
            if not package.enabled:
                continue
            returncode = run(package.name, package.args)
            status[package.name] = returncode
            if not package.on_error_continue and returncode != 0:
                sys.exit(returncode)

        print(status)

    except KeyboardInterrupt as e:
        raise e
    except Exception as e:
        raise e
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
