import pytest
from py_secscan.settings import load_env
from py_secscan.cli.runtime import ParserBuilder
from py_secscan.cli.parser_base import PySecScanConfigBase
from py_secscan.cli.parser_config_v1 import PySecScanConfigV1
from py_secscan.stdx import PySecScanVirtualVenvNotLoadedException

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
    parser = ParserBuilder(str(valid_config_path))
    py_secscan = parser.instance

    assert isinstance(py_secscan, PySecScanConfigBase)
    assert isinstance(py_secscan, PySecScanConfigV1)

    assert py_secscan.version == "1"
    assert py_secscan.options.debug
    assert py_secscan.options.env["TEST_ENV"] == "test"
    assert py_secscan.options.pysecscan_dirpath == "/tmp/pysecscan"
    assert py_secscan.options.venv_dirpath == "/tmp/pysecscan/venv"
    assert py_secscan.options.security.enabled
    assert "ruff1" in py_secscan.options.security.additional_forbbiden_commands
    assert py_secscan.packages[0].command_name == "ruff"
    assert py_secscan.packages[0].command_args == ["check", "--fix"]

    with pytest.raises(PySecScanVirtualVenvNotLoadedException) as excinfo:
        py_secscan.execute()
    assert (
        str(excinfo.value)
        == f"Virtualenv not loaded: run 'source {py_secscan.options.venv_dirpath}/bin/activate' to activate it"
    )

    py_secscan.options.security.disable_venv_check = True
    py_secscan.execute()


def test_invalid_config(invalid_config_path):
    with pytest.raises(ValueError):
        ParserBuilder(str(invalid_config_path))


def test_nonexistent_config(nonexistent_config_path):
    with pytest.raises(FileNotFoundError):
        ParserBuilder(str(nonexistent_config_path))
