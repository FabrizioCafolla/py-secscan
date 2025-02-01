import shlex
import subprocess
from types import LambdaType

from py_secscan.settings import LOGGER

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


class PySecScanException(Exception):
    pass


def info(message: str) -> None:
    LOGGER.info(message)
    print("[INFO]", message)


def debug(message: str) -> None:
    LOGGER.debug(message)
    print("[DEBUG]", message)


def warning(message: str) -> None:
    LOGGER.warning(message)
    print("[WARNING]", message)


def error(message: str) -> None:
    LOGGER.error(message)
    print("[ERROR]", message)


def critical(message: str) -> None:
    LOGGER.critical(message)
    print("[CRITICAL]", message)


def exception(exception: Exception = None, message: str = "") -> None:
    if exception:
        LOGGER.exception(str(exception))
        raise exception

    LOGGER.exception(message)
    raise PySecScanException(message)


def sanitize_shell_command(
    command: str, additional_control_raise_on_success: LambdaType = None
) -> str:
    cmd = shlex.split(command)
    if cmd[0] in FORBIDDEN_COMMANDS:
        raise PySecScanException(f"Forbidden command: {cmd[0]}")
    if any(operator in command for operator in FORBIDDEN_OPERATORS):
        raise PySecScanException(f"Forbidden operator in command: {command}")
    if isinstance(
        additional_control_raise_on_success, LambdaType
    ) and additional_control_raise_on_success(cmd):
        raise PySecScanException(f"Command not allowed: {command}")

    return cmd


def run_subprocess(
    command: str,
    additional_control_raise_on_success: LambdaType = None,
    print_stdout: bool = True,
    print_stderror: bool = True,
    raise_on_failure: bool = False,
) -> subprocess.CompletedProcess:
    command_shlex = sanitize_shell_command(command, additional_control_raise_on_success)

    response = subprocess.run(
        command_shlex,
        capture_output=True,
        text=True,
        check=False,
    )

    if print_stdout:
        print(response.stdout)

    if response.returncode != 0:
        print(response.stderr)
        if raise_on_failure:
            error(f"Command failed: {command}")
            error(f"Command failed with return code: {response.returncode}")
            error(f"Command failed with stderr: {response.stderr}")
            exception(message=f"Command failed: {command}")

    return response
