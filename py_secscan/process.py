import os
import re
import shlex
import subprocess  # nosec
from dataclasses import asdict, dataclass, field
from enum import Enum
from types import LambdaType

from py_secscan import stdx
from py_secscan.settings import LOGGER_FILEPATH


FORBIDDEN_OPERATORS = [
    "|",
    ";",
    "&&",
    "||",
    "`",
    "$(",
    ">",
    "<",
    ">>",
    "<<",
    "&",
    "#",
    "\\",
    "~",
    " ",
]

FORBIDDEN_COMMANDS = [
    "rm",
    "srm",
    "shred",
    "mkfs",
    "mkfs.ext4",
    "mkfs.ext3",
    "mkfs.ext2",
    "mkfs.ntfs",
    "mkfs.fat",
    "mkfs.vfat",
    "dd",
    "nc",
    "netcat",
    "ncat",
    "tcpdump",
    "nmap",
    "telnet",
    "sudo",
    "su",
    "passwd",
    "chown",
    "chmod",
    "chattr",
    "visudo",
    "kill",
    "killall",
    "pkill",
    "renice",
    "shutdown",
    "reboot",
    "poweroff",
    "halt",
    "init",
    "telinit",
    "fdisk",
    "gdisk",
    "parted",
    "gparted",
    "mount",
    "umount",
    "iptables",
    "ip6tables",
    "ufw",
    "route",
    "apt",
    "apt-get",
    "yum",
    "dnf",
    "pacman",
    "snap",
    "make",
    "gcc",
    "g++",
    "sed",
    "awk",
    "perl",
    "bash",
    "sh",
    "csh",
    "ksh",
    "zsh",
    "ssh",
    "scp",
    "sftp",
    "ftp",
    "rsync",
    "wget",
]


class ExecutionStatusAllowed(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class ExecutionStatus:
    _instance = None
    logger_filepath: str | None = field(default=LOGGER_FILEPATH)
    status: dict | None = field(default_factory=dict)

    def update(self, key: str, value: ExecutionStatusAllowed) -> None:
        if not isinstance(key, str):
            raise Exception("Key param is not str")

        if value.value not in ExecutionStatusAllowed:
            raise Exception(f"Value param is not allowed. Allowed values: {ExecutionStatusAllowed}")

        self.status[key] = value.value

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        return str(self.to_dict())

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance


def interpolate(value: str, additional_variables: dict = {}):
    def replace(match):
        key = match.group(1)
        return str({**os.environ, **additional_variables}.get(key, f"${key}"))

    pattern = r"\$\{(\w+)\}"
    return re.sub(pattern, replace, value)


def sanitize_shell_command(
    command: str,
    additional_control_raise_on_success: LambdaType = None,
    additional_forbbiden_commands: list = [],
    enable_interpolate: bool = True,
) -> str:
    cmd_splitted = shlex.split(command)
    cmd = [interpolate(item) for item in cmd_splitted] if enable_interpolate else cmd_splitted
    del cmd_splitted

    if cmd[0] in list(set(additional_forbbiden_commands) | set(FORBIDDEN_COMMANDS)):
        raise stdx.PySecScanSanitizeCommandError(f"Forbidden command: {cmd[0]}")

    if any(cmd[0].startswith(item) for item in FORBIDDEN_OPERATORS):
        raise stdx.PySecScanSanitizeCommandError(f"Forbidden command: {cmd[0]} starting with {FORBIDDEN_OPERATORS}")

    if "=" in cmd[0]:
        raise stdx.PySecScanSanitizeCommandError(f"Forbidden command: {cmd[0]} containing '='")

    for item in cmd:
        if any(operator in item for operator in FORBIDDEN_OPERATORS):
            raise stdx.PySecScanSanitizeCommandError(f"Forbidden operator '{item}' in command: {command}")

    if isinstance(additional_control_raise_on_success, LambdaType) and additional_control_raise_on_success(cmd):
        raise stdx.PySecScanSanitizeCommandError(f"Command not allowed: {command}")

    return cmd


def run_subprocess(
    command: str | list,
    additional_control_raise_on_success: LambdaType = None,
    additional_forbbiden_commands: list = [],
    enable_interpolate: bool = True,
    print_stderror: bool = True,
    raise_on_failure: bool = False,
) -> subprocess.CompletedProcess:
    if isinstance(command, list):
        command = " ".join(command)

    command_sanitized = sanitize_shell_command(
        command,
        additional_control_raise_on_success,
        additional_forbbiden_commands,
        enable_interpolate,
    )

    stdx.info(f"Subprocess command: {' '.join(command_sanitized)}")

    try:
        response = subprocess.run(command_sanitized, capture_output=True, text=True, check=True, shell=False)  # nosec

        stdx.info(response.stdout)

        return response
    except subprocess.CalledProcessError as e:
        stdx.info(e.stdout)

        if print_stderror:
            stdx.error(f"Command failed: {command_sanitized} (return code: {e.returncode})")
            stdx.error(e.stderr)

        if raise_on_failure:
            stdx.exception(message=f"Command failed: {command}")


ExecutionStatusInstance = ExecutionStatus()
