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
        disable_builtins: Optional[bool] = False
        disable_venv_check: Optional[bool] = False
        disable_venv_creation: Optional[bool] = False
        disable_venv_install: Optional[bool] = False
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
class PackageBaseConfigV1(ParserDataclassBase):
    command_name: str
    command_args: Optional[List[str]] = field(default_factory=list)
    enabled: Optional[bool] = True
    on_error_continue: Optional[bool] = True

    def get_command(self, additional_forbbiden_commands) -> str:
        return process.sanitize_shell_command(
            command=" ".join([self.command_name] + self.command_args),
            additional_forbbiden_commands=additional_forbbiden_commands,
        )

    def __post_init__(self):
        super().__post_init__()


@dataclass
class PackageConfigV1(PackageBaseConfigV1):
    @dataclass
    class InstallConfigV1:
        package_name: str = None
        version: Optional[str] = None
        extras: Optional[List[str]] = field(default_factory=list)

    install: Optional[InstallConfigV1] = None

    def __post_init__(self):
        super().__post_init__()

        if self.install:
            if not isinstance(self.install, self.InstallConfigV1):
                self.install = self.InstallConfigV1(**self.install)

            if not self.install.package_name:
                self.install.package_name = self.command_name


class PackageBuiltinConfigV1(PackageBaseConfigV1):
    pass


@dataclass
class PySecScanConfigV1(PySecScanConfigBase):
    version: str = "1"
    jsonschema: str = "pysecscan-1.schema.json"
    options: Optional[OptionsConfigV1] = None
    packages: Optional[List[PackageConfigV1]] = field(default_factory=list)
    builtins: Optional[List[PackageBuiltinConfigV1]] = field(default_factory=list)

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

        builtins = []
        if not self.builtins and self.options.security.disable_builtins is False:
            self.builtins = [
                {"command_name": "ruff", "command_args": ["check"], "enabled": True},
                {
                    "command_name": "cyclonedx-py",
                    "command_args": [
                        f"environment --outfile sbom.json {self.options.venv_dirpath}"
                    ],
                    "enabled": True,
                },
                {
                    "command_name": "python",
                    "command_args": [
                        "-m py_secscan.modules.sbom_vulnerabilities sbom.json sbom_vulnerabilities.json"
                    ],
                    "enabled": True,
                },
            ]
        for builtin in self.builtins:
            if not isinstance(builtin, PackageBuiltinConfigV1):
                builtin = PackageBuiltinConfigV1(**builtin)
                builtins.append(builtin)
        self.builtins = builtins

    def setup(self) -> None:
        def _setup_venv() -> str:
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
                    if (
                        not package.install
                        or self.options.security.disable_venv_install
                    ):
                        continue

                    line = (
                        f"{package.install.package_name}=={package.install.version}"
                        if package.install.version
                        else package.install.package_name
                    )
                    stdx.debug(f"Installing package: {line}")
                    f.write(f"{line}\n")

                    for extra in package.install.extras:
                        stdx.debug(f"  Extra: {extra}")
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
        _setup_venv()

    def execute_packages(self, packages: list) -> None:
        try:
            for package in packages:
                command = package.get_command(
                    additional_forbbiden_commands=self.options.security.additional_forbbiden_commands
                )
                status.ExecutionStatusInstance.update(
                    command[0], status.ExecutionStatusAllowed.RUNNING
                )

                if not package.enabled:
                    stdx.warning(f"{command[0]} package is disabled")
                    status.ExecutionStatusInstance.update(
                        command[0], status.ExecutionStatusAllowed.DISABLED
                    )
                    continue

                response = process.run_subprocess(
                    command=command,
                    sanitize_command=False,  # Command is already sanitized
                )

                if response.returncode == 0:
                    stdx.info(f"Package {command[0]} completed")
                    status.ExecutionStatusInstance.update(
                        command[0], status.ExecutionStatusAllowed.COMPLETED
                    )
                    continue

                status.ExecutionStatusInstance.update(
                    command[0], status.ExecutionStatusAllowed.FAILED
                )
                if not package.on_error_continue:
                    raise stdx.ParserPackageExecutionException(
                        command[0], package.args, response.args
                    )
        except Exception as e:
            stdx.exception(e)
        finally:
            stdx.info(status.ExecutionStatusInstance)

    def execute(self):
        self.setup()

        stdx.info("Execute builtins packages")
        self.execute_packages(self.builtins)

        stdx.info("Execute packages")
        self.execute_packages(self.packages)

        return status.ExecutionStatusInstance
