"""Tests for CLI default flags and push smart-conflict detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from outline_edit.cli import (
    Config,
    build_parser,
    current_state,
    file_sha256,
    push_single_document,
    save_index,
    snapshot_path,
    write_snapshot,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_config(tmp_path: Path) -> Config:
    return Config(
        base_url="https://kb.example.com",
        api_key="test-key",
        cache_dir=tmp_path / "cache",
        timeout=30.0,
        env_file=tmp_path / "config.env",
    )


def make_index(base_url: str = "https://kb.example.com") -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "baseUrl": base_url,
        "documents": {},
        "collections": {},
    }


DOC_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
DOC_TEXT = "# Hello\n\nSome content.\n"


def seed_cached_document(
    index: dict[str, Any],
    config: Config,
    *,
    text: str = DOC_TEXT,
    revision: int = 3,
) -> dict[str, Any]:
    """Write a cached document, snapshot, and index entry.  Returns the entry."""
    rel_path = f"collections/test/{DOC_ID}.md"
    abs_path = config.cache_dir / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(text, encoding="utf-8")
    write_snapshot(config.cache_dir, DOC_ID, text)

    entry = {
        "id": DOC_ID,
        "title": "Test Doc",
        "path": rel_path,
        "revision": revision,
        "contentRevision": revision,
        "sha256": file_sha256(abs_path),
        "url": f"https://kb.example.com/doc/test-doc-abc",
    }
    index["documents"][DOC_ID] = entry
    return entry


def make_remote_document(
    *,
    text: str = DOC_TEXT,
    revision: int = 3,
) -> dict[str, Any]:
    return {
        "id": DOC_ID,
        "title": "Test Doc",
        "text": text,
        "revision": revision,
        "url": "/doc/test-doc-abc",
        "urlId": "abc",
        "updatedAt": "2026-01-01T00:00:00.000Z",
        "updatedBy": {"id": "user1", "name": "Someone"},
        "createdAt": "2026-01-01T00:00:00.000Z",
        "createdBy": {"id": "user1", "name": "Someone"},
        "collaboratorIds": [],
        "publishedAt": "2026-01-01T00:00:00.000Z",
        "archivedAt": None,
        "deletedAt": None,
        "parentDocumentId": None,
        "collectionId": "col1",
    }


def mock_client(remote_doc: dict[str, Any]) -> MagicMock:
    """Return a mock OutlineClient that responds to documents.info and documents.update."""
    client = MagicMock()

    def post_json(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        if endpoint == "documents.info":
            return {"data": {"document": remote_doc}}
        if endpoint == "documents.update":
            bumped = dict(remote_doc)
            bumped["revision"] = remote_doc["revision"] + 1
            return {"data": bumped}
        raise ValueError(f"unexpected endpoint: {endpoint}")

    client.post_json = MagicMock(side_effect=post_json)
    return client


# ---------------------------------------------------------------------------
# create defaults
# ---------------------------------------------------------------------------


class TestCreateDefaults:
    def test_create_publishes_by_default(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["create", "--title", "A Doc"])
        assert not args.draft

    def test_create_draft_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["create", "--title", "A Doc", "--draft"])
        assert args.draft


# ---------------------------------------------------------------------------
# pull defaults
# ---------------------------------------------------------------------------


class TestPullDefaults:
    def test_pull_accepts_no_scope_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["pull"])
        assert not args.all
        assert args.collection is None
        assert args.query is None
        assert args.document_id is None

    def test_pull_accepts_metadata_only_without_all(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["pull", "--metadata-only"])
        assert args.metadata_only
        assert not args.all

    def test_pull_all_still_works(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["pull", "--all"])
        assert args.all


# ---------------------------------------------------------------------------
# Smart conflict detection in push_single_document
# ---------------------------------------------------------------------------


class TestPushSmartConflict:
    def test_no_conflict_when_revisions_match(self, tmp_path: Path) -> None:
        """Baseline: matching revisions should push normally."""
        config = make_config(tmp_path)
        index = make_index()
        entry = seed_cached_document(index, config, revision=3)

        # Locally modify the file
        local_path = config.cache_dir / entry["path"]
        local_path.write_text("# Updated\n", encoding="utf-8")

        remote = make_remote_document(revision=3)
        client = mock_client(remote)

        result = push_single_document(index, config, client, entry)
        assert result["status"] == "updated"

    def test_metadata_only_bump_skips_false_conflict(self, tmp_path: Path) -> None:
        """When remote revision advanced but content is unchanged (e.g. publish),
        push should detect the metadata-only bump and proceed."""
        config = make_config(tmp_path)
        index = make_index()
        entry = seed_cached_document(index, config, revision=3)

        # Locally modify the file
        local_path = config.cache_dir / entry["path"]
        local_path.write_text("# Updated\n", encoding="utf-8")

        # Remote bumped to rev 4 but content is identical to snapshot
        remote = make_remote_document(text=DOC_TEXT, revision=4)
        client = mock_client(remote)

        result = push_single_document(index, config, client, entry)
        assert result["status"] == "updated"
        # contentRevision should have been advanced to 4 before the push
        # (the mock bumps it to 5 on update)
        assert result["revision"] == 5

    def test_real_conflict_when_remote_content_differs(self, tmp_path: Path) -> None:
        """When remote revision advanced AND content changed, push should
        report a real conflict."""
        config = make_config(tmp_path)
        index = make_index()
        entry = seed_cached_document(index, config, revision=3)

        # Locally modify the file
        local_path = config.cache_dir / entry["path"]
        local_path.write_text("# Updated locally\n", encoding="utf-8")

        # Remote bumped to rev 4 with different content
        remote = make_remote_document(text="# Changed remotely\n", revision=4)
        client = mock_client(remote)

        result = push_single_document(index, config, client, entry)
        assert result["status"] == "conflict"
        assert result["localBaseRevision"] == 3
        assert result["remoteRevision"] == 4

    def test_missing_snapshot_stays_conservative(self, tmp_path: Path) -> None:
        """When no snapshot exists (e.g. metadata-only pull), a revision
        mismatch should be treated as a conflict."""
        config = make_config(tmp_path)
        index = make_index()
        entry = seed_cached_document(index, config, revision=3)

        # Delete the snapshot to simulate a metadata-only pull
        snap = snapshot_path(config.cache_dir, DOC_ID)
        snap.unlink()
        assert not snap.exists()

        # Locally modify the file
        local_path = config.cache_dir / entry["path"]
        local_path.write_text("# Updated\n", encoding="utf-8")

        # Remote bumped to rev 4 (content unchanged, but we can't verify)
        remote = make_remote_document(text=DOC_TEXT, revision=4)
        client = mock_client(remote)

        result = push_single_document(index, config, client, entry)
        assert result["status"] == "conflict"
