import shlex
import subprocess
from types import LambdaType
from py_secscan import stdx

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


def sanitize_shell_command(
    command: str, additional_control_raise_on_success: LambdaType = None
) -> str:
    cmd = shlex.split(command)
    if cmd[0] in FORBIDDEN_COMMANDS:
        raise stdx.ySecScanException(f"Forbidden command: {cmd[0]}")
    if any(operator in command for operator in FORBIDDEN_OPERATORS):
        raise stdx.PySecScanException(f"Forbidden operator in command: {command}")
    if isinstance(
        additional_control_raise_on_success, LambdaType
    ) and additional_control_raise_on_success(cmd):
        raise stdx.PySecScanException(f"Command not allowed: {command}")

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
        if print_stderror:
            stdx.error(
                f"Command failed: {command} (return code: {response.returncode})"
            )
            print(response.stderr)

        if raise_on_failure:
            stdx.exception(message=f"Command failed: {command}")

    return response
