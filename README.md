# outline-edit

`outline-edit` is a Python command-line tool for working with an [Outline](https://www.getoutline.com/) knowledge base through the raw Outline API while keeping a local markdown cache on disk.

It is designed for agent and automation workflows that need cheaper repeated reads than full remote document fetches, plus predictable local diff, push, and lifecycle operations.

## Why Not Just Use MCP?

Outline ships an MCP server, and MCP is usually the right choice for one-off interactive queries. But the MCP surface has structural inefficiencies that compound in agent and automation workflows:

| Operation | What MCP does | Cost |
|---|---|---|
| List 50 recent docs | Returns full ProseMirror JSON body for every doc | ~1 MB of tokens |
| Read one document | Searches by title, returns full content of all matches | N x full doc bodies |
| Fix a typo | Fetch full doc, generate full replacement, send full doc, re-fetch to verify | 4 x full doc body |
| Browse a collection | Returns full content of every doc in the collection | Entire collection |
| Check what changed this week | Fetch all docs just to read timestamps | All content for metadata |

Root causes (verified against Outline v1.6.1):

- **No metadata-only mode.** `list_documents` always includes full document bodies. There is no way to request titles or timestamps without content.
- **No partial content.** You cannot request a section or a summary — it is always the full document.
- **No diff or patch on update.** `update_document` requires sending the entire body as a replacement. The only alternatives are `append` and `prepend`.
- **No revision history.** The MCP does not expose `revisions.*` endpoints. You cannot retrieve past versions or compare revisions.
- **No event or audit log.** The MCP does not expose `events.list`. You cannot ask "what changed this week" without fetching every document.
- **No reliable document read by ID.** MCP resource URIs are registered but return authorization errors in practice.

`outline-edit` sidesteps these costs by maintaining a local markdown cache:

```
With outline-edit:
  Read a doc      →  local file read           (~0 API tokens)
  Edit a doc      →  local file edit           (~0 API tokens)
  Push edits      →  one API call              (1x full doc)
  Pull fresh copy →  one API call, cached      (1x full doc)

With MCP:
  Read a doc      →  search by title           (Nx full docs in results)
  Edit a doc      →  generate full replacement (1x full doc in context)
  Push edits      →  send full doc             (1x full doc)
  Verify the push →  search by title again     (Nx full docs)
```

Additional capabilities that MCP does not provide at all:

- Revision history and revision-to-revision diff via the raw API
- Activity and audit log queries
- Document archive, restore, and delete operations
- Optimistic-locking push that refuses to overwrite newer remote edits

Use MCP when you want direct tool-mediated interaction with a live Outline workspace. Use `outline-edit` when you want a reproducible local cache, a cheap read path for repeated workflows, or access to revision and audit capabilities.

## Features

- Local markdown cache with index metadata
- Pull by collection, query, document ID, or full crawl
- Local `status`, `list`, `read`, `search`, and `diff`
- Remote `create`, `push`, `publish`, `archive`, `restore`, and `delete`
- Revision history, activity log, and revision-to-revision diff
- Starter config generation with `init`
- Bundled agent skill definition via `outline-edit skill`
- No third-party runtime dependencies

## Requirements

- Python 3.10+
- An Outline instance with API access enabled
- An API token with the scopes needed for your workflow

## Installation

Install from PyPI:

```bash
pip install outline-edit
```

Install as a global tool with `uv`:

```bash
uv tool install outline-edit
```

Install as a global tool with `pipx`:

```bash
pipx install outline-edit
```

Run without installing:

```bash
uvx outline-edit --help
```

Install from a local checkout while developing:

```bash
uv tool install -e .
```

## Configuration

You can configure the CLI with flags, environment variables, or an env file in the XDG config location.

Generate a starter config file:

```bash
outline-edit init
```

Generate and fill the required values interactively:

```bash
outline-edit init --interactive
```

Default config file:

```bash
~/.config/outline-edit/config.env
```

If `XDG_CONFIG_HOME` is set, the CLI uses:

```bash
$XDG_CONFIG_HOME/outline-edit/config.env
```

Example config file:

```bash
OUTLINE_CLI_BASE_URL=https://your-outline.example.com
OUTLINE_CLI_API_KEY=...
```

Optional settings:

```bash
OUTLINE_CLI_CACHE_DIR=/path/to/custom/cache
OUTLINE_CLI_TIMEOUT=30
```

## Quick Start

Generate config and validate auth:

```bash
outline-edit init --interactive
outline-edit auth
```

Pull one collection into the local cache:

```bash
outline-edit pull --collection Engineering
```

Inspect the local cache:

```bash
outline-edit status
outline-edit list --collection Engineering
outline-edit read "Weekly Notes"
outline-edit search incident
```

Edit locally and push changes back:

```bash
outline-edit diff "Weekly Notes"
outline-edit push "Weekly Notes"
```

Create documents (published by default):

```bash
outline-edit create --collection Engineering --title "CLI Test" --text "body text"
outline-edit create --collection Engineering --title "Draft Note" --text "wip" --draft
```

Manage lifecycle and history:

```bash
outline-edit archive "CLI Test"
outline-edit restore "CLI Test"
outline-edit delete "CLI Test"
outline-edit history "Architecture Notes" --limit 10
outline-edit revdiff "Architecture Notes" previous latest
outline-edit log "Architecture Notes" --limit 20
```

## Agent Integration

`outline-edit` ships a built-in skill definition that any AI agent can retrieve at runtime:

```bash
outline-edit skill
```

This prints a structured markdown document describing all commands, recommended workflows, rules, and common patterns. Agents that can run shell commands can use this to learn how to operate the tool without external documentation.

The skill file is also available in the repository at `integrations/skills/outline-edit/SKILL.md`.

## Notes

- The env file defaults to `~/.config/outline-edit/config.env`, or `$XDG_CONFIG_HOME/outline-edit/config.env` when `XDG_CONFIG_HOME` is set.
- `outline-edit init` writes a commented starter config to that path and refuses to overwrite an existing file unless `--force` is passed.
- The cache defaults to `~/.local/state/outline-edit/cache/<host>/`, or `$XDG_STATE_HOME/outline-edit/cache/<host>/` when `XDG_STATE_HOME` is set.
- The default cache path is scoped by Outline host so different instances do not share one index by accident.
- XDG path resolution is implemented directly with the Python standard library; `platformdirs` is intentionally not used so the runtime dependency set stays at zero.
- `push` uses optimistic locking against the last content-synced revision and refuses to overwrite newer remote edits.
- `delete --permanent` depends on the caller having the necessary Outline permission.
- `revdiff` works against remote revisions and does not depend on the local cached file.

## Gotchas

- **Optimistic locking, not merging.** `push` checks the remote revision against your last `pull`. If the revision differs but the remote content is unchanged (e.g. a publish or archive bumped the revision), push automatically rebases and proceeds. If the remote content actually changed, push refuses the update. You must re-pull (which overwrites your local copy) or resolve the conflict manually. There is no three-way merge.
- **`diff` is local-only.** `diff` compares your cached file against the snapshot saved at last `pull`. It does not contact the remote server. Use `revdiff` to compare remote revisions against each other.
- **Search is substring-only.** Local `search` does case-insensitive substring matching on titles, paths, and file content. There is no regex, fuzzy, or ranked full-text search.
- **`pull` defaults to all documents.** On a large Outline workspace a bare `pull` can be slow and write a lot of files. Prefer `pull --collection` or `pull --query` to scope the sync.
- **`delete --permanent` is irreversible.** The document is removed server-side and cannot be restored. This also requires the appropriate Outline permission on the server.
- **No automatic staleness detection.** The cache does not refresh on its own. Run `pull` explicitly to update. `status --stale` shows documents where the remote revision is ahead of the cached content revision, but only based on metadata from the last pull.
- **Cache access is serialized per cache directory.** Cache-touching commands take an OS-managed lock and cache files are replaced atomically. If another `outline-edit` command is already using the same cache, retry the command or use a separate `--cache-dir` for concurrent agents. The `.cache.lock` file itself is inert and should not require manual cleanup.

## Current Limits

### Not currently exposed by `outline-edit`

- Collection create/update/delete operations
- Comments
- Document move and duplicate operations
- Attachment or file upload workflows
- Recently viewed documents or per-document viewer reporting

Some of these exist in the Outline API but `outline-edit` does not wrap them yet.

### Not a first-class primitive in the current workflow

- Section-level patch or merge operations
- Conflict-aware three-way merges
- A structured query layer beyond local substring search plus event/revision inspection

The write path is document-oriented: local edit, `diff`, then `push`.

## Development

Basic smoke checks from a checkout:

```bash
python3 -m py_compile src/outline_edit/*.py
PYTHONPATH=src python3 -m outline_edit --help
```

## Related Projects

- [python-outline](https://pypi.org/project/python-outline/) — Python client library for the Outline API
- [mcp-outline](https://github.com/Vortiago/mcp-outline) — MCP server for Outline
- [outline-agent](https://github.com/visualDust/outline-agent) — AI agent for Outline knowledge bases
- [outline-skills](https://github.com/visualdust/outline-skills) — Skill definitions for Outline agents

## License

Apache 2.0
