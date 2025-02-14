import os
import sys
from dataclasses import dataclass, field

from py_secscan import process, settings, stdx
from py_secscan.scan.parser.base import ParserBase, ParserDataclassBase


DEFAULT_ALLOWED_PACKAGES = ["ruff", "cyclonedx-py"]


@dataclass
class OptionsConfigV1(ParserDataclassBase):
    @dataclass
    class SecurityConfigV1:
        enabled: bool | None = True
        disable_builtins: bool | None = False
        disable_venv_check: bool | None = False
        disable_venv_creation: bool | None = False
        disable_venv_install: bool | None = False
        additional_forbbiden_commands: list[str] | None = field(default_factory=list)

    debug: bool | None = False
    env: dict[str, str] | None = field(default_factory=dict)
    pysecscan_dirpath: str | None = field(default=settings.DEFAULT_ENV["PY_SECSCAN_PATH"])
    venv_dirpath: str | None = field(default=settings.DEFAULT_ENV["PY_SECSCAN_VENV"])
    security: SecurityConfigV1 | None = field(default_factory=SecurityConfigV1)

    def __post_init__(self):
        if not isinstance(self.security, self.SecurityConfigV1):
            self.security = self.SecurityConfigV1(**self.security)


@dataclass
class PackageBaseConfigV1(ParserDataclassBase):
    command_name: str
    command_args: list[str] | None = field(default_factory=list)
    enabled: bool | None = True
    on_error_continue: bool | None = True

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
        enabled: bool | None = False
        package_name: str = None
        version: str | None = None
        extras: list[str] | None = field(default_factory=list)

    install: InstallConfigV1 | None = None

    def __post_init__(self):
        super().__post_init__()

        if not isinstance(self.install, self.InstallConfigV1):
            self.install = self.InstallConfigV1(**self.install if self.install else {})

        if not self.install.package_name:
            self.install.package_name = self.command_name


@dataclass
class PackageBuiltinConfigV1(ParserDataclassBase):
    packages: dict[str, PackageBaseConfigV1] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()

        for package_name, package_config in self.packages.items():
            if not isinstance(package_config, PackageBaseConfigV1):
                self.packages[package_name] = PackageBaseConfigV1(**package_config)

    @property
    def packages_list(self) -> list[PackageBaseConfigV1]:
        return [package_config for _, package_config in self.packages.items()]


@dataclass
class ParserV1(ParserBase):
    version: str = "1"
    jsonschema: str = "pysecscan-1.schema.json"
    options: OptionsConfigV1 | None = None
    packages: list[PackageConfigV1] | None = field(default_factory=list)
    builtins: PackageBuiltinConfigV1 | None = field(default_factory=dict)

    def __post_init__(self):
        def _load_builtin_packages(builtins: dict) -> dict[str, PackageBaseConfigV1]:
            if self.options.security.disable_builtins:
                return {}

            default_builtins = {
                "ruff_check": {
                    "command_name": "ruff",
                    "command_args": ["check --fix"],
                    "enabled": True,
                    "on_error_continue": False,
                },
                "ruff_format": {
                    "command_name": "ruff",
                    "command_args": ["format"],
                    "enabled": True,
                    "on_error_continue": False,
                },
                "cyclonedx": {
                    "command_name": "cyclonedx-py",
                    "command_args": [f"environment --outfile sbom.json {self.options.venv_dirpath}"],
                    "enabled": True,
                    "on_error_continue": False,
                },
                "sbom_vulnerabilities": {
                    "command_name": "python -m py_secscan.modules.builtins.sbom_vulnerabilities",
                    "command_args": ["sbom.json sbom_vulnerabilities.json"],
                    "enabled": False,
                    "on_error_continue": True,
                },
            }

            if not builtins:
                return default_builtins

            for package_name, package_config in builtins.items():
                if package_name not in default_builtins:
                    stdx.exception(f"Package {package_name} is not a valid builtin")

                default_builtins[package_name].update(package_config)

            return default_builtins

        super().__post_init__()

        if not isinstance(self.options, OptionsConfigV1):
            self.options = OptionsConfigV1(**self.options if self.options else {})

        packages = []
        for package in self.packages:
            if not isinstance(package, PackageConfigV1):
                package = PackageConfigV1(**package)  # noqa: PLW2901
            packages.append(package)
        self.packages = packages

        self.builtins = PackageBuiltinConfigV1(packages=_load_builtin_packages(self.builtins))

    def setup(self) -> None:  # noqa: C901
        def _setup_venv() -> str:
            # Ensure the environment variable is set to the correct value
            settings.setenv("PY_SECSCAN_PATH", self.options.pysecscan_dirpath)
            settings.setenv("PY_SECSCAN_VENV", self.options.venv_dirpath)

            if (
                os.path.isdir(self.options.venv_dirpath) is False
                and self.options.security.disable_venv_creation is True
            ):
                process.run_subprocess(
                    f"{sys.executable} -m venv {self.options.venv_dirpath}",
                    raise_on_failure=True,
                )
                stdx.exception(
                    exception=stdx.PySecScanVirtualVenvNotLoadedError(
                        f"Virtualenv created: run 'source {self.options.venv_dirpath}/bin/activate' to activate it"
                    ),
                )

            if (
                os.getenv("VIRTUAL_ENV") is None
                and os.environ["VIRTUAL_ENV"].endswith(self.options.venv_dirpath) is False
            ):
                stdx.exception(
                    exception=stdx.PySecScanVirtualVenvNotLoadedError(self.options.venv_dirpath),
                )

            stdx.debug(f"Virtualenv successfully loaded: {self.options.venv_dirpath}")

            with open(f"{self.options.pysecscan_dirpath}/requirements.txt", "w") as f:
                for package in self.packages:
                    if package.install.enabled is False or self.options.security.disable_venv_install:
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
            gitignore_lines = []
            if os.path.isfile(".gitignore"):
                with open(".gitignore") as f:
                    gitignore_lines = f.read().splitlines()

            exclude_filepath = f"{settings.PY_SECSCAN_DIRNAME}/"

            if exclude_filepath not in gitignore_lines:
                gitignore_lines.append(exclude_filepath)

            with open(".gitignore", "w") as f:
                f.write("\n".join(gitignore_lines))

        def _load_env() -> None:
            settings.setenv_from_dict(overwrite=True, **self.options.env)

            if self.options.debug or os.environ.get("PY_SECSCAN_DEBUG") == "1":
                settings.set_debug_mode()

        _load_env()
        _setup_gitignore()

        if self.options.security.disable_venv_check:
            stdx.warning("Virtualenv check disabled")
            return

        _setup_venv()

    def execute_packages(self, packages: list[PackageBaseConfigV1]) -> None:
        try:
            for package in packages:
                command = package.get_command(
                    additional_forbbiden_commands=self.options.security.additional_forbbiden_commands
                )
                process.ExecutionStatusInstance.update(command[0], process.ExecutionStatusAllowed.RUNNING)

                if not package.enabled:
                    stdx.warning(f"{command[0]} package is disabled")
                    process.ExecutionStatusInstance.update(command[0], process.ExecutionStatusAllowed.DISABLED)
                    continue

                try:
                    stdx.info(f"Executing package {command[0]}")

                    process.run_subprocess(
                        command=command,
                        raise_on_failure=True,
                    )
                    stdx.info(f"Package {command[0]} completed")
                    process.ExecutionStatusInstance.update(command[0], process.ExecutionStatusAllowed.COMPLETED)
                except stdx.PySecScanSanitizeCommandError:
                    process.ExecutionStatusInstance.update(command[0], process.ExecutionStatusAllowed.FAILED)
                    if not package.on_error_continue:
                        stdx.exception(stdx.ParserPackageExecutionError(command))
        except Exception as e:
            stdx.exception(e)
        finally:
            stdx.info(process.ExecutionStatusInstance)

    def execute(self):
        self.setup()

        stdx.info("Execute builtins packages")
        self.execute_packages(self.builtins.packages_list)

        stdx.info("Execute packages")
        self.execute_packages(self.packages)

        return process.ExecutionStatusInstance
