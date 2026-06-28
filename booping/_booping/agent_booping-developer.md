# booping-developer (project extension)

Project-local stack and conventions for the developer agent.

## Stack

Python 3.13 — cyclopts CLI for MPD + beets. Clean architecture: Adapters → Services → Commands, all adapter deps flow through Protocol interfaces (`musictl/protocols.py`). Managed by `uv`.

- `musictl/adapters/` — thin wrappers (mpd via python-mpd2, beets via beets.library + subprocess, ffmpeg via ffcuesplitter, yad via subprocess)
- `musictl/services/` — business logic, receives adapters via protocol types
- `musictl/commands/` — cyclopts entry points, wired in `__main__.py`
- `stubs/` — type stubs for untyped third-party libs

## Conventions

- **Always `uv run`** — never invoke `python`/venv scripts directly (`uv run pytest`, `uv run musictl`, etc.).
- ruff for lint + format (line-length 120, py313), basedpyright (standard mode) for typing, pytest for tests.
- **Never suppress type errors** with `# pyright: ignore` or file-level overrides — fix the root cause. For untyped libs, add stubs in `stubs/` (search PyPI for `types-{pkg}`/`{pkg}-stubs` first).
- Pyright already disables noisy rules — don't add suppressions without good reason.
- Adapters tested via mocks in `tests/test_adapters/`. Services/commands tested with protocol fakes, not real backends.
- Match surrounding code style: comment density, naming, idiom.

## Notes

- If a task touches areas outside the stack above, stop and escalate to the orchestrator before implementing.
- Always prefer the project's own commands (`just …`) over ad-hoc invocations. If the task specifies a Verify command, run that — don't substitute.
