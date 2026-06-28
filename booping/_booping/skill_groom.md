# groom (project extension)

Project-local facts for grooming.

## Available validations

Commands available in this project to validate changes. When writing a milestone's `Verify` block or the plan's `Final Verification` section, pick the subset that actually exercises what the milestone changed — don't blanket-run everything.

- `just test` — full pytest suite (`uv run pytest`)
- `just check` — lint + typecheck (ruff check + ruff format --check + basedpyright musictl)
- `just lint` — `uv run ruff check .` + `uv run ruff format --check .`
- `just typecheck` — `uv run basedpyright musictl`
- `just fmt` — auto-fix: `ruff check --fix` + `ruff format` (use before committing, not as a gate)
- `pre-commit run --all-files` — full hook suite (ruff, ruff-format, basedpyright on `musictl/`, pytest on `tests/`)

## Sizing calibration

(default — see `src/config.yaml` → `sprint.default_threshold_sp`)
