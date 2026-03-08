# Musictl

Music control CLI for MPD + beets. Clean architecture: adapters → services → commands.

## Commands

```bash
just check      # lint + typecheck
just fmt         # auto-format
uv run pytest    # run tests
```

## Lint & Type Errors

- Never suppress type errors with `# pyright: ignore` or file-level overrides. Fix the root cause.
- For untyped third-party libraries (e.g. python-mpd2, ffcuesplitter), create type stubs in `stubs/` directory.
  - First search PyPI/web for existing stubs (`types-{pkg}` or `{pkg}-stubs`) before writing custom ones.
  - Stubs are configured via `stubPath = "stubs"` in `[tool.basedpyright]` in pyproject.toml.
- Pyright config in pyproject.toml already disables noisy rules (reportAny, reportUnknownMemberType, etc.) — don't add more suppressions without good reason.
- Ruff handles import sorting and unused import detection. Run `just fmt` to auto-fix.

## Architecture

- `musictl/adapters/` — thin wrappers around external libraries (mpd, beets, ffmpeg, yad)
- `musictl/services/` — business logic, depends on adapter protocols
- `musictl/commands/` — CLI entry points via cyclopts
- `musictl/protocols.py` — Protocol interfaces for adapters
- `stubs/` — type stubs for untyped third-party libraries
