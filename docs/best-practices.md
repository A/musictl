# Development Best Practices

## Tooling

### uv — Package & Project Manager

[uv](https://docs.astral.sh/uv/) replaces pip, pip-tools, poetry, and pyenv in a single fast tool.

- `uv sync` — install dependencies from `uv.lock`
- `uv add <package>` — add a dependency
- `uv add --dev <package>` — add a dev dependency
- `uv run <command>` — run a command in the project's virtualenv
- `uv lock` — update the lockfile

uv manages the `.venv` and `.python-version` automatically.

### ruff — Linter & Formatter

[ruff](https://docs.astral.sh/ruff/) is an extremely fast Python linter and formatter that replaces flake8, isort, black, and pyupgrade.

- `uv run ruff check .` — lint the codebase
- `uv run ruff check --fix .` — auto-fix lint issues
- `uv run ruff format .` — format code
- `uv run ruff format --check .` — check formatting without changes

Configured in `pyproject.toml` under `[tool.ruff]`.

### basedpyright — Type Checker

[basedpyright](https://docs.basedpyright.com/) is a fork of pyright with stricter defaults and better error messages.

- `uv run basedpyright` — run type checking

Configured in `pyproject.toml` under `[tool.pyright]`.

### just — Task Runner

[just](https://just.systems/) is a command runner (like make, but simpler).

- `just check` — run all checks (lint + format check + typecheck)
- `just lint` — run linter
- `just fmt` — format code
- `just typecheck` — run type checker
- `just sync` — install dependencies

Recipes are defined in `Justfile`.

### pre-commit — Git Hooks

[pre-commit](https://pre-commit.com/) runs checks automatically before each commit.

Configured in `.pre-commit-config.yaml`. Hooks:

- **ruff** — lint and format check
- **basedpyright** — type checking
- **pytest** — run tests

Install hooks after cloning:

```sh
uv run pre-commit install
```

Hooks run automatically on `git commit`. To run manually on all files:

```sh
uv run pre-commit run --all-files
```

## Workflow

1. **Before committing**: run `just check` to ensure lint, formatting, and types are clean.
2. **Adding dependencies**: use `uv add <package>` — never edit `pyproject.toml` manually for deps.
3. **Type annotations**: annotate function signatures. Use modern syntax (`str | None` instead of `Optional[str]`).
