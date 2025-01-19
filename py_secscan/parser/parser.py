import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from py_secscan import settings
from py_secscan import utils
from py_secscan.parser import runtime

DEFAULT_ALLOWED_PACKAGES = [
    "ruff",
    "pylint",
    "bandit",
    "pre-commit",
    "checkov",
]


class SubprocessFailed(Exception):
    def __init__(
        self,
        package_name: str,
        package_args: List[str],
        command: list[str] = None,
        *args,
        **kwargs,
    ):
        self.package = package_name
        self.args = args
        self.command = " ".join(command) if command else None
        self.message = (
            f"Error executing package {package_name} with args {package_args}"
            + (f"\n{self.command}" if self.command else "")
        )
        super().__init__(self.message, *args, **kwargs)


@dataclass
class SecurityConfig:
    enabled: Optional[bool] = True
    additional_allowed_packages: Optional[List[str]] = field(default_factory=list)
    exclude_default_allowed_packages: Optional[bool] = False

    @property
    def allowed_packages(self):
        return list(
            set(self.additional_allowed_packages)
            | set(
                []
                if self.exclude_default_allowed_packages
                else DEFAULT_ALLOWED_PACKAGES
            )
        )


@dataclass
class OptionsConfig:
    debug: Optional[bool] = False
    env: Optional[Dict[str, str]] = field(default_factory=dict)
    venv_dirpath: Optional[str] = field(default=".venv")
    security: Optional[SecurityConfig] = field(default_factory=SecurityConfig)


@dataclass
class ModuleConfig:
    package_name: str = None
    command_name: Optional[str] = (
        None  # Use the name of the package if not provided. If package name is different from the command name, provide the command name
    )
    enabled: Optional[bool] = True
    version: Optional[str] = None
    args: Optional[List[str]] = field(default_factory=list)
    extras: Optional[List[str]] = field(default_factory=list)
    on_error_continue: Optional[bool] = True

    @property
    def name(self) -> str:
        return self.command_name if self.command_name else self.package_name


@dataclass
class PySecScanConfig:
    options: Optional[OptionsConfig] = None
    packages: Optional[List[ModuleConfig]] = None

    def __post_init__(self):
        self.setup_venv()
        settings.setenv_from_dict(overwrite=True, **self.options.env)
        if self.options.debug:
            utils.debug("Debug mode enabled")
            settings.setenv("PY_SECSCAN_DEBUG", "1")
        else:
            sys.tracebacklimit = 0

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "PySecScanConfig":
        yaml_path = Path(yaml_path)
        if not os.path.isfile(yaml_path):
            raise FileNotFoundError(f"File {yaml_path} not found")

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        if "packages" in data:
            data["packages"] = [ModuleConfig(**module) for module in data["packages"]]

        if "options" in data:
            if "security" in data["options"]:
                data["options"]["security"] = SecurityConfig(
                    **data["options"]["security"]
                )

            data["options"] = OptionsConfig(**data["options"])

        return cls(**data)

    def setup_venv(self) -> None:
        if not os.path.isdir(self.options.venv_dirpath):
            utils.run_subprocess(f"python -m venv {self.options.venv_dirpath}")
            utils.warning(
                f"Virtualenv created: run 'source {self.options.venv_dirpath}/bin/activate' to activate it"
            )
            sys.exit(0)

        with open(
            f"{settings.DEFAULT_ENV['PY_SECSCAN_PATH']}/requirements.txt", "w"
        ) as f:
            for package in self.packages:
                line = (
                    f"{package.package_name}=={package.version}"
                    if package.version
                    else package.package_name
                )
                f.write(f"{line}\n")

                for extra in package.extras:
                    f.write(f"{package.package_name}[{extra}]\n")

        utils.run_subprocess(
            f"pip install -r {settings.DEFAULT_ENV['PY_SECSCAN_PATH']}/requirements.txt"
        )

        # Create a .gitignore file in the root directory if it does not exist, and add the exclusion line if not already present
        gitignore = (
            open(".gitignore").read().splitlines()
            if os.path.isfile(".gitignore")
            else []
        )
        exclude_filepath = f"{settings.PY_SECSCAN_DIRNAME}/"

        if exclude_filepath not in gitignore:
            gitignore.append(exclude_filepath)

        with open(".gitignore", "w") as f:
            f.write("\n".join(gitignore))

    def execute(self) -> None:
        try:
            for package in self.packages:
                runtime.RUNTIME_EXCUTION_STATUS.update(
                    package.name, runtime.RunTimeAllowedExecutionStatus.RUNNING
                )

                if not package.enabled:
                    utils.warning(f"{package.name} package is disabled")
                    runtime.RUNTIME_EXCUTION_STATUS.update(
                        package.name, runtime.RunTimeAllowedExecutionStatus.DISABLED
                    )
                    continue

                utils.info(f"Running {package.name}")

                response = utils.run_subprocess(
                    " ".join([package.name] + package.args),
                    lambda cmd: cmd[0] not in self.options.security.allowed_packages,
                )

                print(response.stdout)

                if response.returncode == 0:
                    utils.info(f"Package {package.name} completed")
                    runtime.RUNTIME_EXCUTION_STATUS.update(
                        package.name, runtime.RunTimeAllowedExecutionStatus.COMPLETED
                    )
                    continue

                print(response.stderr)

                runtime.RUNTIME_EXCUTION_STATUS.update(
                    package.name, runtime.RunTimeAllowedExecutionStatus.FAILED
                )
                if not package.on_error_continue:
                    raise SubprocessFailed(package.name, package.args, response.args)
        except Exception as e:
            utils.exception(e)
        finally:
            utils.info(runtime.RUNTIME_EXCUTION_STATUS)

    def __dict__(self) -> dict:
        return asdict(self)


def build(py_secscan_config_filename: str) -> PySecScanConfig:
    try:
        if not os.path.isfile(py_secscan_config_filename):
            utils.exception(message=f"File {py_secscan_config_filename} not found")

        return PySecScanConfig.from_yaml(py_secscan_config_filename)
    except FileNotFoundError as e:
        utils.exception(e)
