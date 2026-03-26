# outline-edit Agent Guide

`outline-edit` is a small Python packaging repo for a public-facing CLI. Keep changes compact, keep docs public-safe, prioritize packaging clarity over internal project sprawl, and commit completed work promptly.

## Project Shape

- `src/outline_edit/cli.py`: main CLI implementation
- `src/outline_edit/__main__.py`: `python -m outline_edit` entry point
- `pyproject.toml`: packaging metadata and console script definition
- `README.md`: user-facing install and usage guide
- `tests/`: automated tests
- `docs/PUBLISH.md`: release checklist and PyPI publishing gate

## Working Rules

- Run `git status -sb` before editing and before committing.
- Keep the public package generic. Do not hardcode org-specific URLs, collection names, team names, or secrets.
- Do not commit API keys, env files, local caches, build artifacts, or virtualenvs.
- Prefer changes that improve `pip`, `pipx`, `uv tool install`, and `uvx` usability.
- Keep dependency and build-tool versions pinned exactly in `pyproject.toml` and synchronized with `uv.lock`.
- When changing any dependency, rebuild the lockfile and rerun the relevant tests before calling the new version set "tested".
- Treat the minimum supported Python version in `.python-version` as the default development and validation target.
- Leave unrelated files alone, especially in a dirty worktree.
- When a logical task is complete and validation has passed, commit it immediately. Do not leave finished work uncommitted.

## Documentation Rules

- `README.md` must stay free of personal or company-specific operational details.
- Installation and usage docs must match the actual CLI entry point and environment variables.
- If behavior changes, update `README.md` in the same change.

## Testing Expectations

Run the smallest relevant checks for the files you changed.

Minimum expectations:

- Python changes: `python3 -m py_compile src/outline_edit/*.py`
- CLI wiring or packaging changes: `PYTHONPATH=src python3 -m outline_edit --help`
- If tests exist for the changed area: `pytest`
- Dependency or packaging version changes: `uv lock`, `uv run pytest`, and `python3 -m build`
- Compatibility-sensitive changes: run the relevant checks with `uv run --python 3.10 ...`

If a stronger packaging check is relevant and the tooling is available, also run:

- `python3 -m build`

If you cannot run a needed check, say so explicitly.

## Release And Packaging

- Follow `docs/PUBLISH.md` for release preparation and PyPI publishing.
- Keep package metadata, README install instructions, and console entry points synchronized.
- Keep version strings synchronized anywhere they are user-visible or emitted at runtime.
- Do not claim the package is PyPI-ready unless the build metadata, import path, and install paths all work.
- Avoid adding runtime dependencies unless they materially improve the tool.
- Prefer exact tested versions over floating ranges for build and development tooling.

## Git

- Commit completed logical units promptly after the relevant checks pass. Do not wait to be asked to commit once the task is done.
- Never use `git add .`, `git add -A`, or `git commit -a`.
- Stage only the files for the current task.
- Review staged changes with `git diff --staged --name-only` and `git diff --staged`.
- Use conventional commit prefixes such as `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, or `chore:`.
