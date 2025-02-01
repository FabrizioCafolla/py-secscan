import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from py_secscan import settings
from py_secscan import utils
from py_secscan.cli import runtime


DEFAULT_ALLOWED_PACKAGES = [
    "ruff",
    "pylint",
    "bandit",
    "pre-commit",
    "checkov",
]


class ExceptionParserPackageExecutionError(Exception):
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
class PySecScanConfig:
    version: Optional[str] = None

    def execute(self):
        raise NotImplementedError


@dataclass
class SecurityConfigV1:
    enabled: Optional[bool] = True
    additional_allowed_packages: Optional[List[str]] = field(default_factory=list)
    exclude_default_allowed_packages: Optional[bool] = False

    @property
    def allowed_packages(self):
        default_allowed_package = (
            [] if self.exclude_default_allowed_packages else DEFAULT_ALLOWED_PACKAGES
        )
        return list(
            set(self.additional_allowed_packages) | set(default_allowed_package)
        )


@dataclass
class OptionsConfigV1:
    debug: Optional[bool] = False
    env: Optional[Dict[str, str]] = field(default_factory=dict)
    venv_dirpath: Optional[str] = field(default=settings.DEFAULT_ENV["PY_SECSCAN_VENV"])
    security: Optional[SecurityConfigV1] = field(default_factory=SecurityConfigV1)


@dataclass
class ModuleConfigV1:
    package_name: str = None
    # Use the name of the package if not provided. If package name is different from the command name, provide the command name
    command_name: Optional[str] = None
    version: Optional[str] = None
    enabled: Optional[bool] = True
    args: Optional[List[str]] = field(default_factory=list)
    extras: Optional[List[str]] = field(default_factory=list)
    on_error_continue: Optional[bool] = True

    @property
    def name(self) -> str:
        return self.command_name if self.command_name else self.package_name


@dataclass
class PySecScanConfigV1(PySecScanConfig):
    version: str = "1"
    options: Optional[OptionsConfigV1] = None
    packages: Optional[List[ModuleConfigV1]] = field(default_factory=list)

    def __post_init__(self):
        self.setup_venv()

        settings.setenv_from_dict(overwrite=True, **self.options.env)

        if self.options.debug:
            utils.debug("Debug mode enabled")
            settings.setenv("PY_SECSCAN_DEBUG", "1")
        else:
            sys.tracebacklimit = 0

    @classmethod
    def from_yaml(cls, py_secscan_config_filename: Path) -> "PySecScanConfig":
        with open(py_secscan_config_filename) as f:
            data = yaml.safe_load(f)

        if "packages" in data:
            data["packages"] = [
                ModuleConfigV1(**module) for module in data.get("packages", [])
            ]

        if "options" in data:
            if "security" in data["options"]:
                data["options"]["security"] = SecurityConfigV1(
                    **data["options"]["security"]
                )

            data["options"] = OptionsConfigV1(**data["options"])

        return cls(**data)

    def setup_venv(self) -> None:
        if not os.path.isdir(self.options.venv_dirpath):
            utils.run_subprocess(
                f"{sys.executable} -m venv {self.options.venv_dirpath}",
                raise_on_failure=True,
            )
            utils.warning(
                f"Virtualenv created: run 'source {self.options.venv_dirpath}/bin/activate' to activate it"
            )
            sys.exit(0)

        settings.setenv("PY_SECSCAN_PATH", self.options.venv_dirpath)

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
            f"{sys.executable} -m ensurepip --upgrade",
            raise_on_failure=True,
        )

        utils.run_subprocess(
            f"{sys.executable} -m pip install -r {settings.DEFAULT_ENV['PY_SECSCAN_PATH']}/requirements.txt",
            raise_on_failure=True,
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
                runtime.ExecutionStatus().update(
                    package.name, runtime.ExecutionStatusAllowed.RUNNING
                )

                if not package.enabled:
                    utils.warning(f"{package.name} package is disabled")
                    runtime.ExecutionStatus().update(
                        package.name, runtime.ExecutionStatusAllowed.DISABLED
                    )
                    continue

                utils.info(f"Running {package.name}")

                response = utils.run_subprocess(
                    " ".join([package.name] + package.args),
                    lambda cmd: cmd[0] not in self.options.security.allowed_packages,
                )

                if response.returncode == 0:
                    utils.info(f"Package {package.name} completed")
                    runtime.ExecutionStatus().update(
                        package.name, runtime.ExecutionStatusAllowed.COMPLETED
                    )
                    continue

                runtime.ExecutionStatus().update(
                    package.name, runtime.ExecutionStatusAllowed.FAILED
                )
                if not package.on_error_continue:
                    raise ExceptionParserPackageExecutionError(
                        package.name, package.args, response.args
                    )
        except Exception as e:
            utils.exception(e)
        finally:
            utils.info(runtime.ExecutionStatus())

    def __dict__(self) -> dict:
        return asdict(self)


class Parser:
    py_secscan_config_filename: str
    py_secscan_config: PySecScanConfig

    def __init__(self, py_secscan_config_filename: str):
        if not os.path.isfile(py_secscan_config_filename):
            raise FileNotFoundError(f"File {py_secscan_config_filename} not found")

        self.py_secscan_config_filename = py_secscan_config_filename
        self.py_secscan_config = self.build()

    def build(self) -> PySecScanConfig:
        try:
            if not os.path.isfile(self.py_secscan_config_filename):
                raise FileNotFoundError(
                    f"File {self.py_secscan_config_filename} not found"
                )

            with open(self.py_secscan_config_filename) as f:
                data = yaml.safe_load(f)

            if "version" not in data:
                raise ValueError("Version not found in the configuration file")

            if data["version"] == "1":
                return PySecScanConfigV1.from_yaml(self.py_secscan_config_filename)

            raise ValueError(f"Version {data['version']} not supported")
        except FileNotFoundError as e:
            utils.exception(e)
        except Exception as e:
            utils.exception(e)
        return None
