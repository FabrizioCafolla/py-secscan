import sys
import os
import yaml
import subprocess
import shlex
from py_secscan.cli import conf


def manipolate_modules(packages: list[object]) -> None:
    return {package["name"]: package for package in packages}


def setup_venv(packages: list[object], venv_dirpath: str) -> None:
    def create_requirements_txt(packages) -> None:
        manipolated_packages = manipolate_modules(packages)
        with open(f"{conf.DEFAULT_ENV['PY_SECSCAN_PATH']}/requirements.txt", "w") as f:
            for name, package in manipolated_packages.items():
                line = (
                    f"{name}=={package['version']}" if package.get("version") else name
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


def load_project_settings() -> dict:
    try:
        if not os.path.isfile(conf.DEFAULT_ENV["PY_SECSCAN_CONFIG_FILENAME"]):
            raise Exception(
                f"File {conf.DEFAULT_ENV['PY_SECSCAN_CONFIG_FILENAME']} not found"
            )

        project_settings = yaml.safe_load(
            open(conf.DEFAULT_ENV["PY_SECSCAN_CONFIG_FILENAME"], "r")
        )
        conf.setenv_from_dict(overwrite=True, **project_settings.get("env", {}))
    except FileNotFoundError as e:
        raise e
    except Exception as e:
        raise e
    else:
        return project_settings


def main() -> bool:
    try:
        conf.load_default_env()

        project_settings = load_project_settings()

        setup_venv(
            project_settings.get("packages", {}),
            project_settings.get("venv_dirpath", ".venv"),
        )

    except KeyboardInterrupt as e:
        raise e
    except Exception as e:
        raise e
    else:
        return 0
    finally:
        os.chdir(conf.CURRENT_DIR)


if __name__ == "__main__":
    sys.exit(main())
