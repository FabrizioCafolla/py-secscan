import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml
import jsonschema
import json

from py_secscan import settings
from py_secscan import utils
from py_secscan.cli import runtime


DEFAULT_ALLOWED_PACKAGES = [
    "ruff",
    "pylint",
    "bandit",
    "pre-commit",
    "checkov",
    "cyclonedx-py",
    "safety",
    "pip-audit",
    "osv-scanner",
]


class ParserBase:
    def __post_init__(self):
        """The validation is performed by calling a function named:
        `validate_<field_name>(self, value, field) -> field.type`
        """
        for field_name, _ in self.__dataclass_fields__.items():
            if method := getattr(self, f"validate_{field_name}", None):
                setattr(self, field_name, method(getattr(self, field_name)))


class SchemaLoader:
    _schema = None

    @classmethod
    def load_schema(cls, schema_filename: str):
        if cls._schema is None:
            schema_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), schema_filename
            )

            try:
                with open(schema_path, "r") as f:
                    cls._schema = json.load(f)
            except Exception as e:
                utils.exception(f"Failed to load jsonschema file: {str(e)}")

        return cls._schema

    @classmethod
    def validate(cls, schema_filename: str, instance: dict):
        schema = cls.load_schema(schema_filename)
        try:
            jsonschema.validate(instance=instance, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            utils.exception(f"Configuration validation failed: {str(e)}")


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
class OptionsConfigV1(ParserBase):
    @dataclass
    class SecurityConfigV1:
        enabled: Optional[bool] = True
        additional_allowed_packages: Optional[List[str]] = field(default_factory=list)
        exclude_default_allowed_packages: Optional[bool] = False

        @property
        def allowed_packages(self):
            default_allowed_package = (
                []
                if self.exclude_default_allowed_packages
                else DEFAULT_ALLOWED_PACKAGES
            )
            return list(
                set(self.additional_allowed_packages) | set(default_allowed_package)
            )

    debug: Optional[bool] = False
    env: Optional[Dict[str, str]] = field(default_factory=dict)
    venv_dirpath: Optional[str] = field(default=settings.DEFAULT_ENV["PY_SECSCAN_VENV"])
    security: Optional[SecurityConfigV1] = field(default_factory=SecurityConfigV1)

    def __post_init__(self):
        if not isinstance(self.security, self.SecurityConfigV1):
            self.security = self.SecurityConfigV1(**self.security)


@dataclass
class PackageConfigV1(ParserBase):
    @dataclass
    class InstallConfigV1:
        package_name: str
        version: Optional[str] = None
        extras: Optional[List[str]] = field(default_factory=list)

    type: str
    on_error_continue: Optional[bool] = True
    enabled: Optional[bool] = True
    install: Optional[InstallConfigV1] = None
    command_name: Optional[str] = None
    command_args: Optional[List[str]] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.command_name

    @property
    def args(self) -> List[str]:
        return self.command_args

    def __post_init__(self):
        super().__post_init__()

        if not isinstance(self.install, self.InstallConfigV1):
            self.install = self.InstallConfigV1(**self.install)

    def validate_type(self, value, **_):
        if value not in ["python", "bin"]:
            raise ValueError(f"Invalid type: {value}")


@dataclass
class PySecScanConfigBase(ParserBase):
    version: str
    jsonschema: str

    def execute(self):
        raise NotImplementedError

    @classmethod
    def from_yaml(cls, py_secscan_config_filename: Path) -> "PySecScanConfigBase":
        if not os.path.isfile(py_secscan_config_filename):
            raise FileNotFoundError(f"File {py_secscan_config_filename} not found")

        with open(py_secscan_config_filename) as f:
            data = yaml.safe_load(f)

        SchemaLoader.validate(cls.jsonschema, data)

        return cls(**data)


@dataclass
class PySecScanConfigBaseV1(PySecScanConfigBase):
    version: str = "1"
    jsonschema: str = "pysecscan-1.schema.json"
    options: Optional[OptionsConfigV1] = None
    packages: Optional[List[PackageConfigV1]] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.options, OptionsConfigV1):
            self.options = OptionsConfigV1(**self.options)

        packages = []
        for package in self.packages:
            if not isinstance(package, PackageConfigV1):
                packages.append(PackageConfigV1(**package))
        self.packages = packages

        self.load()

    def load(self) -> None:
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
                if not package.install:
                    continue

                line = (
                    f"{package.install.package_name}=={package.install.version}"
                    if package.install.version
                    else package.install.package_name
                )
                f.write(f"{line}\n")

                for extra in package.install.extras:
                    f.write(f"{package.install.package_name}[{extra}]\n")

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

        settings.setenv_from_dict(overwrite=True, **self.options.env)

        if self.options.debug:
            utils.debug("Debug mode enabled")
            settings.setenv("PY_SECSCAN_DEBUG", "1")
        else:
            sys.tracebacklimit = 0

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
    parser_versions = {
        "1": PySecScanConfigBaseV1,
    }

    py_secscan_config_filename: str
    py_secscan_config: PySecScanConfigBase

    @property
    def config(self) -> PySecScanConfigBase:
        return self.py_secscan_config

    def __init__(self, py_secscan_config_filename: str, auto_build: bool = True):
        if not os.path.isfile(py_secscan_config_filename):
            raise FileNotFoundError(f"File {py_secscan_config_filename} not found")

        self.py_secscan_config_filename = py_secscan_config_filename

        if auto_build:
            self.build()

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

            self.py_secscan_config = (self.parser_versions[data["version"]]).from_yaml(
                self.py_secscan_config_filename
            )
        except FileNotFoundError as e:
            utils.exception(e)
        except Exception as e:
            utils.exception(e)
        return None
