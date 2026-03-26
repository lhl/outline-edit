from argparse import Namespace

import pytest

from outline_cli.cli import (
    DEFAULT_ENV_FILE,
    Config,
    KBError,
    OutlineClient,
    build_config,
    build_parser,
    command_init,
    default_cache_dir,
)


def test_build_parser_uses_console_name() -> None:
    parser = build_parser()
    assert parser.prog == "outline-cli"


def test_default_env_file_uses_xdg_config_path() -> None:
    assert DEFAULT_ENV_FILE.name == "config.env"
    assert DEFAULT_ENV_FILE.parent.name == "outline-cli"


def test_default_cache_dir_is_scoped_by_host() -> None:
    cache_dir = default_cache_dir("https://kb.example.com")
    assert cache_dir.name == "kb-example-com"
    assert cache_dir.parent.name == "cache"


def test_root_runtime_args_survive_subcommand_defaults(tmp_path) -> None:
    parser = build_parser()
    env_file = tmp_path / "config.env"

    args = parser.parse_args(["--env-file", str(env_file), "init"])

    assert args.env_file == env_file


def test_command_init_writes_template_config(tmp_path, capsys) -> None:
    env_file = tmp_path / "config.env"
    args = Namespace(force=False, interactive=False, json=False)
    config = Config(
        base_url="",
        api_key=None,
        cache_dir=tmp_path / "cache",
        timeout=30.0,
        env_file=env_file,
    )

    assert command_init(args, config) == 0

    content = env_file.read_text(encoding="utf-8")
    assert "OUTLINE_CLI_BASE_URL=https://your-outline.example.com" in content
    assert "OUTLINE_CLI_API_KEY=..." in content
    assert "Next step: outline-cli auth" in capsys.readouterr().out


def test_missing_config_error_points_to_init(tmp_path) -> None:
    env_file = tmp_path / "config.env"
    config = Config(
        base_url="",
        api_key=None,
        cache_dir=tmp_path / "cache",
        timeout=30.0,
        env_file=env_file,
    )

    with pytest.raises(KBError) as excinfo:
        OutlineClient(config)

    message = str(excinfo.value)
    assert str(env_file) in message
    assert "outline-cli init" in message


def test_build_config_rejects_invalid_timeout(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OUTLINE_CLI_TIMEOUT", "abc")
    args = Namespace(
        base_url=None,
        api_key=None,
        cache_dir=None,
        env_file=tmp_path / "config.env",
        timeout=None,
    )

    with pytest.raises(KBError, match="Invalid timeout value"):
        build_config(args)
