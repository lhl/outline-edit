---
name: outline-edit
description: Use for Outline knowledge base work that should go through the outline-edit local cache and raw API workflow instead of repeated remote reads. Covers init, auth, pull, search, read, diff, push, publish, archive, restore, delete, history, revdiff, and log.
---

# outline-edit

Use this skill when working with an Outline knowledge base through `outline-edit`, especially if the task involves repeated reads, local edits, revision history, or document lifecycle operations.

## Commands

- `auth`: validate API access and show the current user/team
- `init`: create a starter config file, optionally interactively
- `pull`: fetch remote documents into the local cache (defaults to all documents when no scope flag is given)
- `status`: show local cache state, including modified, stale, or missing docs
- `list`: list cached documents (local only, no API call)
- `read`: print a cached document's markdown content
- `create`: create a document through the raw Outline API (publishes by default — pass `--draft` to create an unpublished draft instead)
- `search`: search cached metadata and content (local only — must `pull` first)
- `diff`: compare a cached document with its last synced snapshot
- `push`: send local cached edits back to Outline
- `publish`: publish a cached draft
- `archive`: archive a remote document
- `restore`: restore an archived or deleted document, or restore content from a revision
- `delete`: delete a remote document, optionally permanently
- `history`: show remote revision history for a document
- `revdiff`: diff two remote revisions
- `log`: show remote Outline activity events

## Gotchas

### `pull` defaults to all documents

Bare `outline-edit pull` fetches all accessible documents. Use `--collection`, `--query`, or `--document-id` to narrow scope. On a large workspace, prefer a scoped pull to avoid fetching everything:

```
outline-edit pull --metadata-only              # all docs, metadata only
outline-edit pull --collection "Engineering"   # one collection, full content
outline-edit pull --query "deployment"         # search results
```

### Document selectors: titles, UUIDs, and ambiguity

Commands that take a document `selector` (read, diff, push, publish, archive, restore, delete, history) accept:
- **Full UUID**: `4a16e5a1-a7bd-40e4-8a28-25338a485519`
- **Short hex prefix**: `4a16e5a1` (first 8 chars of the UUID — shown in `list` output)
- **Title substring**: `"My Doc"` — but this will **error if ambiguous** (matches multiple docs)

When a title selector is ambiguous, the error message lists all matches with their UUIDs. Use the full UUID or short prefix to disambiguate.

**Best practice**: Use `list` or `search --title-only` first to find the short hex prefix, then use that for subsequent commands.

### `--collection` filter does substring matching on slugs

The `--collection` flag on `list`, `search`, `status`, and `push` does case-insensitive substring matching on the slug form of collection names. Short names will over-match:

```
# GOTCHA: "IT" matches slugs containing "it": it, compet-it-ive-landscape, etc.
outline-edit list --collection "IT"
# May return: IT, Competitive Landscape, Grants and Credits

# SAFER: use a longer, unambiguous name
outline-edit list --collection "Competitive Landscape"
```

For short collection names, verify results or use `--json` and filter by `collectionName` for exact matching.

### `list` and `search` are local-only

They only see documents already in the local cache. If the cache is empty or stale, results will be incomplete. Always `pull` first. Full-text `search` requires content pulled (not just `--metadata-only`).

### Listing collections

There is no dedicated `collections` command. To get a clean list of all collection names:
`outline-edit list --json | python3 -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(sorted(set(x['collectionName'] for x in d['documents']))))"`

### Renaming a document

There is no `rename` command. To change a document's title, edit the title via the Outline API:

```
curl -s -X POST https://YOUR_OUTLINE/api/documents.update \
  -H "Authorization: Bearer $OUTLINE_CLI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"id": "FULL-UUID", "title": "New Title"}'
```

Then re-pull to sync the local cache: `outline-edit pull --document-id FULL-UUID --force`

Get the full UUID from `outline-edit list SELECTOR --json`.

### `create --text` and long content

For documents longer than a few lines, use `--file` instead of `--text` to avoid shell quoting issues:
`outline-edit create --title "My Doc" --collection "Eng" --file /tmp/draft.md`

### `--force` pull overwrites local edits

If you have unpushed local changes and run `pull --force`, they will be lost. Check `status --modified` before force-pulling.

## Default workflow

1. If config is missing, create it:
   `outline-edit init`
   or
   `outline-edit init --interactive`
2. Validate config and auth before remote operations:
   `outline-edit auth`
3. Bootstrap the cache (first time or periodic refresh):
   `outline-edit pull --metadata-only`
4. Pull content for what you need:
   `outline-edit pull --collection ...`
   `outline-edit pull --query ...`
   `outline-edit pull --document-id ...`
5. Work from the local cache when possible:
   `outline-edit status`
   `outline-edit list`
   `outline-edit read ...`
   `outline-edit search ...`
   `outline-edit diff ...`
6. Mutate remotely only when needed:
   `outline-edit create --title "..." --collection "..." --text "..."`
   `outline-edit push ...`
   `outline-edit publish ...`
   `outline-edit archive ...`
   `outline-edit restore ...`
   `outline-edit delete ...`
7. Use remote audit/revision commands for history:
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
- Default cache path is XDG state and scoped by Outline host: `~/.local/state/outline-edit/cache/<host-slug>/`.
- When a selector is ambiguous, use the 8-char hex prefix from `list` output, not the title.

## Common patterns

- List all collections:
  `outline-edit list --json | python3 -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(sorted(set(x['collectionName'] for x in d['documents']))))"`
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
- Rename a document:
  Get UUID: `outline-edit list SELECTOR --json`
  Then: `curl -s -X POST https://YOUR_OUTLINE/api/documents.update -H "Authorization: Bearer $OUTLINE_CLI_API_KEY" -H "Content-Type: application/json" -d '{"id":"UUID","title":"New Title"}'`
  Then: `outline-edit pull --document-id UUID --force`
- Recently viewed docs or who viewed a doc:
  not exposed as a first-class `outline-edit` command yet; do not promise this workflow without adding support first.

## In Repo

From a checkout, use:

`PYTHONPATH=src python3 -m outline_edit ...`
