import pytest

from py_secscan.scan.parser.base import ParserBase
from py_secscan.scan.parser.v1.parser import ParserV1
from py_secscan.scan.scan import ScanBuilder
from py_secscan.settings import load_env
from py_secscan.stdx import PySecScanVirtualVenvNotLoadedError


load_env()


@pytest.fixture
def valid_config_path(tmp_path):
    config_path = tmp_path / "valid_config.yml"
    config_path.write_text("""
version: "1"
options:
  debug: true
  env:
    TEST_ENV: "test"
  pysecscan_dirpath: "/tmp/pysecscan"
  venv_dirpath: "/tmp/pysecscan/venv"
  security:
    enabled: true
    additional_forbbiden_commands:
      - "ruff1"
packages:
  - command_name: "ruff"
    command_args: ["check", "--fix"]
    install:
      package_name: "ruff"
      version: "0.0.1"
    """)
    return config_path


@pytest.fixture
def invalid_config_path(tmp_path):
    config_path = tmp_path / "invalid_config.yml"
    config_path.write_text("""
version: "-1"
options:
  debug: true
    """)
    return config_path


@pytest.fixture
def nonexistent_config_path(tmp_path):
    return tmp_path / "nonexistent_config.yml"


def test_valid_config(valid_config_path):
    builder = ScanBuilder(str(valid_config_path))

    assert isinstance(builder.parser, ParserBase)
    assert isinstance(builder.parser, ParserV1)

    assert builder.parser.version == "1"
    assert builder.parser.options.debug
    assert builder.parser.options.env["TEST_ENV"] == "test"
    assert builder.parser.options.pysecscan_dirpath == "/tmp/pysecscan"
    assert builder.parser.options.venv_dirpath == "/tmp/pysecscan/venv"
    assert builder.parser.options.security.enabled
    assert "ruff1" in builder.parser.options.security.additional_forbbiden_commands
    assert builder.parser.packages[0].command_name == "ruff"
    assert builder.parser.packages[0].command_args == ["check", "--fix"]

    with pytest.raises(PySecScanVirtualVenvNotLoadedError) as excinfo:
        builder.execute()
    assert (
        str(excinfo.value)
        == f"Virtualenv not loaded: run 'source {builder.parser.options.venv_dirpath}/bin/activate' to activate it"
    )

    builder.parser.options.security.disable_venv_check = True
    builder.execute()


def test_invalid_config(invalid_config_path):
    with pytest.raises(ValueError):
        ScanBuilder(str(invalid_config_path))


def test_nonexistent_config(nonexistent_config_path):
    with pytest.raises(FileNotFoundError):
        ScanBuilder(str(nonexistent_config_path))
