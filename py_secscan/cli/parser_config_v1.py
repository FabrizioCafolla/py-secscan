import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional


from py_secscan import settings
from py_secscan import process
from py_secscan import stdx
from py_secscan.cli import status
from py_secscan.cli.parser_base import ParserDataclassBase, PySecScanConfigBase


DEFAULT_ALLOWED_PACKAGES = ["ruff", "cyclonedx-py"]


@dataclass
class OptionsConfigV1(ParserDataclassBase):
    @dataclass
    class SecurityConfigV1:
        enabled: Optional[bool] = True
        disable_venv_check: Optional[bool] = False
        disable_venv_creation: Optional[bool] = False
        additional_forbbiden_commands: Optional[List[str]] = field(default_factory=list)

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
class PackageConfigV1(ParserDataclassBase):
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

        self.packages = packages

    def setup(self) -> None:
        def _setup_venv_dirpath() -> str:
            # Ensure the environment variable is set to the correct value
            settings.setenv("PY_SECSCAN_PATH", self.options.pysecscan_dirpath)
            settings.setenv("PY_SECSCAN_VENV", self.options.venv_dirpath)

            if self.options.security.disable_venv_check:
                stdx.warning("Virtualenv check disabled")
                return

            if os.getenv("VIRTUAL_ENV") and os.environ["VIRTUAL_ENV"].endswith(
                self.options.venv_dirpath
            ):
                stdx.debug(
                    f"Virtualenv successfully loaded: {self.options.venv_dirpath}"
                )
                return

            if (
                not os.path.isdir(self.options.venv_dirpath)
                and not self.options.security.disable_venv_creation
            ):
                stdx.debug(
                    f"Virtualenv created: run 'source {self.options.venv_dirpath}/bin/activate' to activate it"
                )
                process.run_subprocess(
                    f"{sys.executable} -m venv {self.options.venv_dirpath}",
                    raise_on_failure=True,
                )

            stdx.exception(
                exception=stdx.PySecScanVirtualVenvNotLoadedException(
                    self.options.venv_dirpath
                ),
            )

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
                    additional_forbbiden_commands=self.options.security.additional_forbbiden_commands,
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

    def execute(self):
        self.setup()
        self.execute_packages()
        return status.ExecutionStatusInstance
