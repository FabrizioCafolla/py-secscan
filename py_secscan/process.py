import shlex
import subprocess
from types import LambdaType
from py_secscan import stdx

import re
import os

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
    cmd = (
        [interpolate(item) for item in shlex.split(command)]
        if enable_interpolate
        else shlex.split(command)
    )

    if cmd[0] in list(set(additional_forbbiden_commands) | set(FORBIDDEN_COMMANDS)):
        raise stdx.PySecScanBaseException(f"Forbidden command: {cmd[0]}")

    for item in cmd:
        if any(operator in item for operator in FORBIDDEN_OPERATORS):
            raise stdx.PySecScanBaseException(
                f"Forbidden operator '{item}' in command: {command}"
            )

    if isinstance(
        additional_control_raise_on_success, LambdaType
    ) and additional_control_raise_on_success(cmd):
        raise stdx.PySecScanBaseException(f"Command not allowed: {command}")

    return cmd


def run_subprocess(
    command: str,
    additional_control_raise_on_success: LambdaType = None,
    additional_forbbiden_commands: list = [],
    enable_interpolate: bool = True,
    print_stdout: bool = True,
    print_stderror: bool = True,
    raise_on_failure: bool = False,
) -> subprocess.CompletedProcess:
    command_sanitized = sanitize_shell_command(
        command,
        additional_control_raise_on_success,
        additional_forbbiden_commands,
        enable_interpolate,
    )

    response = subprocess.run(
        command_sanitized, capture_output=True, text=True, check=False
    )

    if print_stdout:
        print(response.stdout)

    if response.returncode != 0:
        if print_stderror:
            stdx.error(
                f"Command failed: {command} (return code: {response.returncode})"
            )
            print(response.stderr)

        if raise_on_failure:
            stdx.exception(message=f"Command failed: {command}")

    return response
