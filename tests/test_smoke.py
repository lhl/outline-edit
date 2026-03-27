from argparse import Namespace
from multiprocessing import Process
from pathlib import Path
import time

import pytest

from outline_edit.cli import (
    DEFAULT_ENV_FILE,
    Config,
    KBError,
    OutlineClient,
    build_config,
    build_parser,
    cache_operation_lock,
    command_init,
    command_skill,
    current_state,
    default_cache_dir,
    push_single_document,
    update_cached_document_from_remote,
)


def _hold_cache_lock(cache_dir: str, ready_path: str, release_path: str) -> None:
    from pathlib import Path

    from outline_edit.cli import cache_operation_lock

    ready = Path(ready_path)
    release = Path(release_path)

    with cache_operation_lock(Path(cache_dir), timeout=0.5):
        ready.write_text("ready", encoding="utf-8")
        deadline = time.time() + 5
        while time.time() < deadline and not release.exists():
            time.sleep(0.05)


def _acquire_cache_lock_once(cache_dir: str, ready_path: str) -> None:
    from pathlib import Path

    from outline_edit.cli import cache_operation_lock

    with cache_operation_lock(Path(cache_dir), timeout=0.5):
        Path(ready_path).write_text("ready", encoding="utf-8")


def test_build_parser_uses_console_name() -> None:
    parser = build_parser()
    assert parser.prog == "outline-edit"


def test_default_env_file_uses_xdg_config_path() -> None:
    assert DEFAULT_ENV_FILE.name == "config.env"
    assert DEFAULT_ENV_FILE.parent.name == "outline-edit"


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
    assert "Next step: outline-edit auth" in capsys.readouterr().out


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
    assert "outline-edit init" in message


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


def test_command_skill_reads_repo_export_in_checkout(tmp_path, capsys) -> None:
    exported_skill = (
        Path(__file__).resolve().parents[1]
        / "integrations/skills/outline-edit/SKILL.md"
    )
    config = Config(
        base_url="",
        api_key=None,
        cache_dir=tmp_path / "cache",
        timeout=30.0,
        env_file=tmp_path / "config.env",
    )

    assert exported_skill.is_file()
    assert not exported_skill.is_symlink()
    assert command_skill(Namespace(), config) == 0
    assert capsys.readouterr().out == exported_skill.read_text(encoding="utf-8")


def test_push_updates_local_state_to_clean(tmp_path) -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.updated_text = None

        def post_json(self, path: str, payload: dict) -> dict:
            if path == "documents.info":
                return {
                    "data": {
                        "document": {
                            "id": doc_id,
                            "title": "Doc",
                            "url": "/doc/doc-1",
                            "urlId": "doc-1",
                            "collectionId": collection_id,
                            "revision": 1,
                            "createdAt": "2026-03-27T00:00:00.000Z",
                            "updatedAt": "2026-03-27T00:00:00.000Z",
                            "publishedAt": "2026-03-27T00:00:00.000Z",
                            "archivedAt": None,
                            "deletedAt": None,
                            "createdBy": {"id": "u1", "name": "Tester"},
                            "updatedBy": {"id": "u1", "name": "Tester"},
                            "collaboratorIds": [],
                        }
                    }
                }
            if path == "documents.update":
                self.updated_text = payload["text"]
                return {
                    "data": {
                        "id": doc_id,
                        "title": "Doc",
                        "url": "/doc/doc-1",
                        "urlId": "doc-1",
                        "collectionId": collection_id,
                        "revision": 2,
                        "text": payload["text"],
                        "createdAt": "2026-03-27T00:00:00.000Z",
                        "updatedAt": "2026-03-27T00:01:00.000Z",
                        "publishedAt": "2026-03-27T00:00:00.000Z",
                        "archivedAt": None,
                        "deletedAt": None,
                        "createdBy": {"id": "u1", "name": "Tester"},
                        "updatedBy": {"id": "u1", "name": "Tester"},
                        "collaboratorIds": [],
                    }
                }
            raise AssertionError(f"unexpected path: {path}")

    doc_id = "18b73058-a651-4eed-ad62-addb288ce6d8"
    collection_id = "ae317064-a5dd-43aa-9a8c-2e7308523154"
    cache_dir = tmp_path / "cache"
    config = Config(
        base_url="https://kb.example.com",
        api_key="test-key",
        cache_dir=cache_dir,
        timeout=30.0,
        env_file=tmp_path / "config.env",
    )
    index = {
        "collections": {
            collection_id: {
                "id": collection_id,
                "name": "IT",
            }
        },
        "documents": {},
    }

    update_cached_document_from_remote(
        index,
        config,
        {
            "id": doc_id,
            "title": "Doc",
            "url": "/doc/doc-1",
            "urlId": "doc-1",
            "collectionId": collection_id,
            "revision": 1,
            "text": "old body",
            "createdAt": "2026-03-27T00:00:00.000Z",
            "updatedAt": "2026-03-27T00:00:00.000Z",
            "publishedAt": "2026-03-27T00:00:00.000Z",
            "archivedAt": None,
            "deletedAt": None,
            "createdBy": {"id": "u1", "name": "Tester"},
            "updatedBy": {"id": "u1", "name": "Tester"},
            "collaboratorIds": [],
        },
        metadata_only=False,
        force=True,
    )
    entry = index["documents"][doc_id]
    local_path = cache_dir / entry["path"]
    local_path.write_text("new body\n", encoding="utf-8")
    assert current_state(entry, cache_dir)["modified"] is True

    result = push_single_document(index, config, FakeClient(), entry)

    assert result["status"] == "updated"
    assert index["documents"][doc_id]["revision"] == 2
    assert current_state(index["documents"][doc_id], cache_dir)["modified"] is False


def test_cache_operation_lock_times_out_while_other_process_holds_it(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    ready = tmp_path / "ready"
    release = tmp_path / "release"
    proc = Process(
        target=_hold_cache_lock,
        args=(str(cache_dir), str(ready), str(release)),
    )
    proc.start()
    try:
        deadline = time.time() + 5
        while time.time() < deadline and not ready.exists():
            time.sleep(0.05)
        assert ready.exists()

        with pytest.raises(KBError, match="Cache is busy with another outline-edit command"):
            with cache_operation_lock(cache_dir, timeout=0.2):
                pass
    finally:
        release.write_text("release", encoding="utf-8")
        proc.join(timeout=5)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=5)

    assert proc.exitcode == 0


def test_cache_operation_lock_reacquires_without_manual_cleanup(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    ready = tmp_path / "ready"
    proc = Process(
        target=_acquire_cache_lock_once,
        args=(str(cache_dir), str(ready)),
    )
    proc.start()
    proc.join(timeout=5)
    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=5)

    assert proc.exitcode == 0
    assert ready.exists()
    assert (cache_dir / ".cache.lock").exists()

    with cache_operation_lock(cache_dir, timeout=0.2):
        pass
