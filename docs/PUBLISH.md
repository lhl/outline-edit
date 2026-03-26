# Publishing Checklist

Use this as the release checklist for cutting a new `outline-edit` version and publishing it to PyPI.

## Versioning

Use semver-style bumps:

- Patch (`0.1.1`): bug fixes, packaging/docs fixes, non-breaking UX cleanup
- Minor (`0.2.0`): new commands, new flags, or significant cache/API workflow additions
- Major (`1.0.0`): intentional breaking changes to CLI behavior, config/env names, or cache/index layout

## Release Punch List

- [ ] Start from a clean release scope: `git status -sb`
- [ ] Sync the release base: `git fetch --tags origin` and `git pull --ff-only`
- [ ] Pick the next version number
- [ ] Update version metadata in:
      `pyproject.toml`
- [ ] Update version metadata in:
      `src/outline_edit/__init__.py`
- [ ] Update version metadata in:
      `src/outline_edit/cli.py` (`USER_AGENT`)
- [ ] Re-read `README.md` and confirm install, config, and command examples still match the code
- [ ] Update `README.md` and any user-facing docs if install steps, config behavior, or CLI workflows changed
- [ ] Update `integrations/skills/outline-edit/SKILL.md` if the recommended agent workflow changed
- [ ] Run release validation:
      `python3 -m py_compile src/outline_edit/*.py`
- [ ] Run release validation:
      `PYTHONPATH=src python3 -m outline_edit --help`
- [ ] Run release validation:
      `PYTHONPATH=src python3 -m outline_edit init --help`
- [ ] Run release validation:
      `pytest`
- [ ] Run release validation against the minimum supported Python:
      `uv run --python 3.10 pytest`
- [ ] Remove stale build artifacts before rebuilding:
      `rm -f dist/outline_edit-*`
- [ ] Build fresh artifacts:
      `uv run python -m build`
- [ ] Verify package metadata/rendering:
      `uvx --from twine twine check dist/*`
- [ ] Smoke-test the built wheel before upload:
      `uv run --isolated --with dist/outline_edit-X.Y.Z-py3-none-any.whl outline-edit --help`
- [ ] Stage only release files explicitly and review them:
      `git add ...`, `git diff --staged --name-only`, `git diff --staged`
- [ ] Commit release metadata:
      `git commit -m "chore: prepare vX.Y.Z release"`
- [ ] Create an annotated tag:
      `git tag -a vX.Y.Z -m "vX.Y.Z"`
- [ ] Push the release commit and tag:
      `git push origin main`, `git push origin vX.Y.Z`
- [ ] Publish to PyPI with configured credentials:
      `uv publish dist/outline_edit-X.Y.Z-py3-none-any.whl dist/outline_edit-X.Y.Z.tar.gz`
- [ ] If `uv publish` is not configured, use the fallback upload path:
      `uvx --from twine twine upload dist/outline_edit-X.Y.Z-py3-none-any.whl dist/outline_edit-X.Y.Z.tar.gz`
- [ ] Verify the published install path from PyPI:
      `uvx --refresh --from "outline-edit==X.Y.Z" outline-edit --help`
- [ ] Verify the PyPI project page and Git tag both show the new version correctly
- [ ] Confirm the tree is clean again:
      `git status -sb`

## Notes

- Do not publish from a dirty tree.
- Do not reuse old `dist/` artifacts blindly; rebuild for every release.
- `uv publish` defaults to `dist/*`; either clear old artifacts first or pass the exact wheel and sdist paths for the version you are cutting.
- Keep the public docs generic. Do not add private Outline instance URLs, collection names, or operational details to release docs.
- This repo does not currently maintain a dedicated changelog. Until that changes, put the human-readable release summary in the annotated tag message and the GitHub release notes.
- If release work changes config paths, environment variables, or cache/index semantics, update both `README.md` and `integrations/skills/outline-edit/SKILL.md` in the same release.
