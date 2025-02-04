import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml
import jsonschema
import json

from py_secscan import settings
from py_secscan import process
from py_secscan import stdx
from py_secscan.cli import status


DEFAULT_ALLOWED_PACKAGES = ["ruff", "cyclonedx-py"]


class ParserBase:
    def __post_init__(self):
        """The validation is performed by calling a function named:
        `validate_<field_name>(self, value, field) -> field.type`
        """
        for field_name, _ in self.__dataclass_fields__.items():
            if method := getattr(self, f"validate_{field_name}", None):
                setattr(self, field_name, method(getattr(self, field_name)))

    def __dict__(self) -> dict:
        return asdict(self)


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
                stdx.exception(f"Failed to load jsonschema file: {str(e)}")

        return cls._schema

    @classmethod
    def validate(cls, schema_filename: str, instance: dict):
        schema = cls.load_schema(schema_filename)
        try:
            jsonschema.validate(instance=instance, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            stdx.exception(f"Configuration validation failed: {str(e)}")


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
    pysecscan_dirpath: Optional[str] = field(
        default=settings.DEFAULT_ENV["PY_SECSCAN_PATH"]
    )
    venv_dirpath: Optional[str] = field(default=settings.DEFAULT_ENV["PY_SECSCAN_VENV"])
    security: Optional[SecurityConfigV1] = field(default_factory=SecurityConfigV1)

    def __post_init__(self):
        if not isinstance(self.security, self.SecurityConfigV1):
            self.security = self.SecurityConfigV1(**self.security)


@dataclass
class PackageConfigV1(ParserBase):
    @dataclass
    class InstallConfigV1:
        package_name: str = None
        version: Optional[str] = None
        extras: Optional[List[str]] = field(default_factory=list)

    command_name: Optional[str]
    on_error_continue: Optional[bool] = True
    enabled: Optional[bool] = True
    install: Optional[InstallConfigV1] = None
    command_args: Optional[List[str]] = field(default_factory=list)

    @property
    def package_type(self) -> str:
        return self.type

    @property
    def name(self) -> str:
        return self.command_name

    @property
    def args(self) -> List[str]:
        return self.command_args

    def __post_init__(self):
        super().__post_init__()

        if self.install:
            if not isinstance(self.install, self.InstallConfigV1):
                self.install = self.InstallConfigV1(**self.install)

            if not self.install.package_name:
                self.install.package_name = self.command_name

    def validate_type(self, value, **_):
        if value not in ["python", "bin"]:
            raise ValueError(f"Invalid type: {value}")


@dataclass
class PySecScanConfigBase(ParserBase):
    version: str
    jsonschema: str

    def __post_init__(self):
        super().__post_init__()

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
class PySecScanConfigV1(PySecScanConfigBase):
    version: str = "1"
    jsonschema: str = "pysecscan-1.schema.json"
    options: Optional[OptionsConfigV1] = None
    packages: Optional[List[PackageConfigV1]] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()

        if not isinstance(self.options, OptionsConfigV1):
            self.options = OptionsConfigV1(**self.options)

        packages = []
        for package in self.packages:
            if not isinstance(package, PackageConfigV1):
                package = PackageConfigV1(**package)
                packages.append(package)

            if (
                package.command_name
                not in self.options.security.additional_allowed_packages
            ):
                self.options.security.additional_allowed_packages.append(
                    package.command_name
                )

        self.packages = packages

    def setup(self) -> None:
        def _setup_venv_dirpath() -> str:
            # Ensure the environment variable is set to the correct value
            settings.setenv("PY_SECSCAN_PATH", self.options.pysecscan_dirpath)
            settings.setenv("PY_SECSCAN_VENV", self.options.venv_dirpath)

            if not os.path.isdir(self.options.venv_dirpath):
                process.run_subprocess(
                    f"{sys.executable} -m venv {self.options.venv_dirpath}",
                    raise_on_failure=True,
                )
                stdx.warning(
                    f"Virtualenv created: run 'source {self.options.venv_dirpath}/bin/activate' to activate it"
                )
                sys.exit(0)

            with open(f"{self.options.pysecscan_dirpath}/requirements.txt", "w") as f:
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

            process.run_subprocess(
                f"{sys.executable} -m ensurepip --upgrade",
                raise_on_failure=True,
            )

            process.run_subprocess(
                f"{sys.executable} -m pip install -r {settings.DEFAULT_ENV['PY_SECSCAN_PATH']}/requirements.txt",
                raise_on_failure=True,
            )

        def _setup_gitignore() -> None:
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

        def _load_env() -> None:
            settings.setenv_from_dict(overwrite=True, **self.options.env)

            if self.options.debug or os.environ.get("PY_SECSCAN_DEBUG") == "1":
                settings.set_debug_mode()
                return

            sys.tracebacklimit = 0

        _load_env()
        _setup_gitignore()
        _setup_venv_dirpath()

    def execute_packages(self) -> None:
        try:
            for package in self.packages:
                status.ExecutionStatusInstance.update(
                    package.name, status.ExecutionStatusAllowed.RUNNING
                )

                if not package.enabled:
                    stdx.warning(f"{package.name} package is disabled")
                    status.ExecutionStatusInstance.update(
                        package.name, status.ExecutionStatusAllowed.DISABLED
                    )
                    continue

                stdx.info(f"Running {package.name}")

                response = process.run_subprocess(
                    command=" ".join([package.name] + package.args),
                    additional_control_raise_on_success=lambda cmd: cmd[0]
                    not in self.options.security.allowed_packages,
                )

                if response.returncode == 0:
                    stdx.info(f"Package {package.name} completed")
                    status.ExecutionStatusInstance.update(
                        package.name, status.ExecutionStatusAllowed.COMPLETED
                    )
                    continue

                status.ExecutionStatusInstance.update(
                    package.name, status.ExecutionStatusAllowed.FAILED
                )
                if not package.on_error_continue:
                    raise stdx.ParserPackageExecutionException(
                        package.name, package.args, response.args
                    )
        except Exception as e:
            stdx.exception(e)
        finally:
            stdx.info(status.ExecutionStatusInstance)

    def execute(self) -> None:
        self.setup()
        self.execute_packages()


class Parser:
    parser_versions = {
        "1": PySecScanConfigV1,
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
            stdx.exception(e)
        except Exception as e:
            stdx.exception(e)
        return None
