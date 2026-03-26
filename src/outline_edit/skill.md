---
name: outline-edit
description: Use for Outline knowledge base work that should go through the outline-edit local cache and raw API workflow instead of repeated remote reads. Covers init, auth, pull, search, read, diff, push, publish, archive, restore, delete, history, revdiff, and log.
---

# outline-edit

Use this skill when working with an Outline knowledge base through `outline-edit`, especially if the task involves repeated reads, local edits, revision history, or document lifecycle operations.

## Commands

- `auth`: validate API access and show the current user/team
- `init`: create a starter config file, optionally interactively
- `pull`: fetch remote documents into the local cache
- `status`: show local cache state, including modified or stale docs
- `list`: list cached documents
- `read`: print a cached document
- `create`: create a document through the raw Outline API
- `search`: search cached metadata and content
- `diff`: compare a cached document with its last synced snapshot
- `push`: send local cached edits back to Outline
- `publish`: publish a cached draft
- `archive`: archive a remote document
- `restore`: restore an archived or deleted document, or restore content from a revision
- `delete`: delete a remote document, optionally permanently
- `history`: show remote revision history for a document
- `revdiff`: diff two remote revisions
- `log`: show remote Outline activity events

## Default workflow

1. If config is missing, create it:
   `outline-edit init`
   or
   `outline-edit init --interactive`
2. Validate config and auth before remote operations:
   `outline-edit auth`
3. Populate or refresh the local cache:
   `outline-edit pull --collection ...`
   `outline-edit pull --query ...`
   `outline-edit pull --document-id ...`
4. Work from the local cache when possible:
   `outline-edit status`
   `outline-edit list`
   `outline-edit read ...`
   `outline-edit search ...`
   `outline-edit diff ...`
5. Mutate remotely only when needed:
   `outline-edit create ...`
   `outline-edit push ...`
   `outline-edit publish ...`
   `outline-edit archive ...`
   `outline-edit restore ...`
   `outline-edit delete ...`
6. Use remote audit/revision commands for history:
   `outline-edit history ...`
   `outline-edit revdiff ...`
   `outline-edit log ...`

## Rules

- Prefer cached reads over repeated remote reads.
- If a remote command fails due to missing config, run `outline-edit init` first.
- Run `diff` before `push` when local content changed.
- Treat `push` conflicts as real remote edits; do not overwrite blindly.
- Use `--json` when you need exact time-window filtering, actor rollups, or other client-side post-processing.
- `delete --permanent` depends on server-side permission.
- Default config path is XDG config: `~/.config/outline-edit/config.env`.
- Default cache path is XDG state and scoped by Outline host.

## Common patterns

- Latest updates in a collection:
  `outline-edit log --collection ... --events documents.create,documents.update,documents.publish --limit 100 --json`
  Filter the returned `createdAt` timestamps client-side for exact windows such as "past week".
- Who changed a document:
  `outline-edit history "..." --limit 20`
  or
  `outline-edit log "..." --events documents.update,documents.publish,documents.archive,documents.delete --limit 50`
- What changed in a document:
  `outline-edit revdiff "..." previous latest`
  Use `outline-edit diff "..."` for local unsynced edits instead.
- Find docs on a topic:
  `outline-edit pull --query "..." --metadata-only`
  then
  `outline-edit search "..." --title-only`
- Find local pending work:
  `outline-edit status --modified`
  and
  `outline-edit status --stale`
- Recently viewed docs or who viewed a doc:
  not exposed as a first-class `outline-edit` command yet; do not promise this workflow without adding support first.

## In Repo

From a checkout, use:

`PYTHONPATH=src python3 -m outline_edit ...`
