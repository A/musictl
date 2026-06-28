---
title: E2E Beets Test Harness + De-mocking
type: refactoring
status: awaiting-plan-review
sp: 21
split_from: null
created: 2026-06-28
planned: 20260628 16:29
started: null
completed: null
retro: null
goal: null
summary: "Dockerized real-beets test harness; replace mocked beets adapter tests with
  e2e; regression for the Inbox-enrichment bug"
commit: 011978356309f3ef5741ab5bc395cf878fc4f965
---

# E2E Beets Test Harness + De-mocking

## Context

Two production bugs shipped despite a green suite, because the tests **mocked the thing that broke**:

1. **Inbox-enrichment bug** — `BeetsAdapter.query("path:...")` compared an absolute MPD path against beets' stored path. beets stores music_dir-**relative** paths here, and beets **2.12** reports them absolutized against `$HOME` (not music_dir), while **2.7** reports them relative. The string compare missed, `current_track` returned no folder/playlists, and waybar rendered every track as **Inbox**. `tests/test_adapters/test_beets.py` used a `MagicMock` `_lib` whose `item.path` returned whatever the test set — so it asserted the bug's *assumptions* instead of catching it (`TestPathQuery` literally hard-codes the per-version path strings).
2. **Pango `&` bug** — waybar text containing `&`/`<`/`>` ("Kavinsky & Lovefoxxx") broke Pango markup → blank module. Already fixed and covered by `tests/test_commands/test_waybar.py` (fake-based, no mock smell). In scope here only as a regression to preserve.

The fixes for both already shipped (PR #4). This plan hardens the **test strategy** so this class of bug is caught: run the real `beets.library.Library` and the real `beet` CLI against an isolated, seeded library inside a pinned Docker environment, and replace the mock-heavy beets adapter tests with e2e.

**After:** `test_beets.py` runs against a real Library (no `MagicMock`/`patch`/`monkeypatch`); file-op commands run the real `beet` CLI against silent fixture tracks; a service-level regression reproduces the Inbox bug via real-beets + fake-MPD; everything runs reproducibly in `docker compose`.

## Decisions

- **Isolation = Docker Compose** (user choice) — a `test` service pinning python + beets + ffmpeg + `beet` CLI gives reproducible system deps and prod parity. Trade-off accepted: a single image pins **one** beets version, so it does not catch version-drift by itself. Mitigation: pin the image to the **deployed** beets version (**2.12.0**) so tests run what production runs, and expose a `BEETS_VERSION` build-arg so a second run (e.g. 2.7.x) is possible if drift coverage is later wanted.
- **MPD stays mocked** (user choice: "replace beets mocks, keep the rest") — so the image needs **no mpd daemon**. The enrichment regression uses a **fake MPD + real beets**, which is exactly the seam where both bugs lived. `test_mpd.py` passthrough mocks remain as-is.
- **Seeding = both tiers** — DB-only (`Library.add(Item)`) for query/enrichment/collection logic (fast, deterministic), and **silent audio** (ffmpeg `anullsrc` + tags) for the import/move/delete file-op paths that need real files on disk.
- **Settings injection over `monkeypatch`** — `BeetsAdapter` currently reads module-global `settings`, forcing `patch("...settings")` in tests. Add optional constructor injection (default = global settings) so e2e fixtures pass a tmp-dir `Settings` cleanly. Removes the monkeypatch smell at the root rather than papering over it.
- **Isolation knob = `BEETSDIR` + `HOME` + tmp `Settings`** — each test gets a `tmp_path` library; `BEETSDIR` **and** `HOME` point at tmp (Confuse, beets' config layer, reads `$HOME`; beets' own test helper sets both) so subprocess + Python-API calls **never touch the real `~/Music` / `~/.config/beets`**. This is the one safety-critical invariant.
- **Bug-reproducing invariant: beets `directory` ≠ `music_dir`** — beets 2.12 stores DB paths relative to its library root but the Python API returns them **absolutized against `directory`**. If the fixture sets beets `directory` == `music_dir`, the absolutized path equals the MPD-constructed path and even the *pre-fix* naive compare would match — the regression tests would be green-but-inert. The fixture must set beets `directory` to a **different** base than `Settings.music_dir` (and account for `HOME`, since `_music_rel` strips `Path.home()`), so 2.12 reproduces the real mismatch. This is the make-or-break detail flagged by cross-validation.

## Architecture

```
docker compose run --rm test  ->  uv run pytest
                                     |
   ┌─────────────────────────────────┼──────────────────────────────────┐
   │ in-process (real beets.Library)  │ subprocess (real `beet` CLI)      │
   │  BeetsAdapter(settings=tmp)      │  modify / move / import / remove  │
   │  query / get_field / folders     │  BEETSDIR=tmp config              │
   └─────────────────────────────────┴──────────────────────────────────┘
        seeded by: DB-only Item rows  +  silent ffmpeg tracks

   service regression: TrackService(current_track) = FakeMpd + real BeetsAdapter
```

Image contains: python 3.13, uv, project deps (incl. beets pinned), ffmpeg, `beet` CLI. No mpd, no yad, no real audio. Tests marked `e2e` so they can be selected/deselected; the existing fast unit/fake tests keep running via plain `just test` outside Docker.

## Milestones

### M1: Dockerized test harness + isolated beets fixtures — 6 SP | pending

**Goal**: `docker compose run --rm test` runs the suite against a real, tmp-isolated beets Library, and `BeetsAdapter` accepts an injected `Settings`.

**Verify**: `docker compose run --rm test uv run pytest tests/ -q` is green; `just test` still green on host; a throwaway test constructing `BeetsAdapter(settings=tmp_settings)` against an empty tmp Library returns `[]` from `query("")`.

| Task | Description | Files | SP | Status |
|------|-------------|-------|----|--------|
| 1.1 | Add optional `settings: Settings \| None = None` to `BeetsAdapter.__init__` (default to module global); use `self._settings` everywhere it reads `settings.*`. **Audit all module-global deps**: `_music_rel`/`_abs_path` read both `settings.music_dir` *and* `Path.home()` — resolve both as part of this task (document the `Path.home()` dependency; it's driven by the `HOME` env the fixture sets). No caller changes required. | `musictl/adapters/beets.py` | 2 | pending |
| 1.2 | `Dockerfile.test` (python 3.13 + uv + ffmpeg + `ARG BEETS_VERSION=2.12.0`) and `docker-compose.yml` `test` service mounting the repo, default cmd `uv run pytest tests/`. Add `just test-e2e` wrapper. | `Dockerfile.test`, `docker-compose.yml`, `Justfile` | 2 | pending |
| 1.3 | `conftest.py` fixtures: `beets_env` (tmp `BEETSDIR` **and** `HOME` env, minimal beets `config.yaml` with **`directory` set to a base distinct from `music_dir`** and `autotag: no`), `tmp_settings` (`Settings` with `music_dir` ≠ beets `directory`), `beets_adapter` (`BeetsAdapter(settings=tmp_settings)`). Register `e2e` marker. | `tests/conftest.py`, `pyproject.toml` | 2 | pending |

#### Task 1.1 DoD
- [ ] `BeetsAdapter()` (no args) behaves identically to today (uses global `settings`).
- [ ] `BeetsAdapter(settings=tmp)` reads/writes only the tmp library + db.
- [ ] `just check` clean (no new pyright/ruff findings).

#### Task 1.2 DoD
- [ ] `docker compose run --rm test` builds and runs `pytest`, exit 0 on the current suite.
- [ ] Image contains `beet --version` == the `BEETS_VERSION` arg (default 2.12.0).
- [ ] `just test-e2e` invokes the compose run.

#### Task 1.3 DoD
- [ ] `beets_env` sets `BEETSDIR` **and** `HOME` to tmp dirs with a valid beets config; no test reads `~/.config/beets` or `~/Music`.
- [ ] beets `directory` is a **different** base than `tmp_settings.music_dir`, verified by a fixture-level assertion (so beets 2.12 absolutizes to a path that does NOT equal the MPD-constructed path — the bug condition).
- [ ] `beets_adapter` fixture yields an adapter bound to the tmp library.
- [ ] `pytest -m e2e` selects only the new e2e tests; `pytest -m "not e2e"` runs the existing fast suite.

---

### M2: Track seeding helpers (DB-only + silent audio) — 4 SP | pending

**Goal**: two reusable seeders — one inserting beets `Item` rows with a chosen path form, one generating tiny tagged silent tracks — usable from any e2e test.

**Verify**: a smoke test seeds one DB-only item (relative path form) + one silent track, then `beets_adapter.query("")` returns both with correct `folder`/`playlists`; the silent file exists on disk and is importable by `beet`.

| Task | Description | Files | SP | Status |
|------|-------------|-------|----|--------|
| 2.1 | DB-only seeder `seed_item(lib, *, path, folder, playlists, artist, title, album)` building a beets `Item` and `lib.add()`-ing it. Cross-validation confirmed: beets 2.7 stores/returns relative bytes unchanged; **beets 2.12 returns paths absolutized against the library `directory`** — so the discriminating condition is achieved by the `directory` ≠ `music_dir` fixture split (Task 1.3), not by fighting `Item.add`. Document the resulting on-read path form per version in a module docstring. | `tests/support/seeding.py` | 2 | pending |
| 2.2 | Silent-track generator `make_track(dir, rel_path, **tags)` via `ffmpeg -f lavfi -i anullsrc -t 1` + tag write (mutagen, already transitive via beets). Session-scoped cache for the base silent file; per-test copy + tag. | `tests/support/seeding.py`, `tests/conftest.py` | 2 | pending |

#### Task 2.1 DoD
- [ ] `seed_item` inserts a row queryable via `beets_adapter.query`.
- [ ] The relative-path form (music_dir-relative in DB) is reproducible and documented in a module docstring — this is the condition the Inbox bug needs.
- [ ] Custom fields `folder`/`playlists` round-trip.

#### Task 2.2 DoD
- [ ] `make_track` produces a file `beet import` accepts without error.
- [ ] Tags (artist/title/album) are readable back via beets.
- [ ] No real audio committed to the repo; files are generated at test time.

---

### M3: Real-Library beets adapter tests (replace mocks) — 4 SP | pending

**Goal**: `test_beets.py` exercises `query`, path-matching, `get_field`, `all_folders`, `all_playlists` against a real Library — zero `MagicMock`/`patch`/`monkeypatch`.

**Verify**: `grep -E "MagicMock|patch\(|monkeypatch" tests/test_adapters/test_beets.py` returns nothing; `docker compose run --rm test uv run pytest tests/test_adapters/test_beets.py -q` green.

| Task | Description | Files | SP | Status |
|------|-------------|-------|----|--------|
| 3.1 | Rewrite `TestQuery`, `TestGetField`, `TestCollections` using `beets_adapter` + `seed_item`. | `tests/test_adapters/test_beets.py` | 2 | pending |
| 3.2 | Rewrite `TestPathQuery` to seed real items in each path form the pinned beets version produces (relative + whatever 2.12 reports), then assert `query("path:<abs music_dir path>")` enriches. Drop the hard-coded per-version path strings. | `tests/test_adapters/test_beets.py` | 2 | pending |

#### Task 3.1 DoD
- [ ] All assertions run against a real seeded Library.
- [ ] No mock/patch/monkeypatch symbols remain in the file.
- [ ] Coverage of `query`/`get_field`/`all_folders`/`all_playlists` is preserved or improved.

#### Task 3.2 DoD
- [ ] **Discriminating check**: assert the seeded item's raw reported path (`_item_path(item)`) does NOT string-equal the `path:` query target — i.e. the fixture genuinely reproduces the mismatch, so the test would fail against a naive compare (not just the happy path).
- [ ] A track seeded with a music_dir-relative path is matched by an absolute `path:` query (the Inbox bug condition).
- [ ] A non-matching path returns `[]`.
- [ ] The returned `path` field is normalized under music_dir.

---

### M4: Real subprocess file-op tests — 3 SP | pending

**Goal**: `modify`, `move`, `import_tracks`, `remove` are tested by running the real `beet` CLI against silent fixtures in an isolated `BEETSDIR`, asserting real effects — not argv strings.

**Verify**: `docker compose run --rm test uv run pytest tests/test_adapters/test_beets.py -k "subprocess or fileop" -q` green; assertions check DB field changes / file relocation / file deletion on disk.

| Task | Description | Files | SP | Status |
|------|-------------|-------|----|--------|
| 4.1 | Replace `TestSubprocessCommands` argv-assert mocks with real runs: `modify` changes a field + moves the file; `move` relocates per path template; `remove(delete=True)` removes row + unlinks file. Uses `make_track` + `BEETSDIR`. **Imports must run offline** — pass `--noautotag --quiet --nowrite` (or rely on `autotag: no` from the fixture config) so `beet import` makes no MusicBrainz calls in the no-network image. | `tests/test_adapters/test_beets.py` | 3 | pending |

#### Task 4.1 DoD
- [ ] `modify` test asserts the new field value via a fresh query and the moved file path on disk.
- [ ] `remove(delete=True)` test asserts the row is gone and the file no longer exists.
- [ ] All runs use the tmp `BEETSDIR`; a guard asserts the real `~/Music` is never referenced.

---

### M5: End-to-end enrichment regression — 2 SP | pending

**Goal**: a service-level test reproduces the original Inbox bug — `TrackService.current_track` with a **fake MPD** (returns a music_dir-relative `file`) + a **real `BeetsAdapter`** (seeded) enriches the track with folder/playlists.

**Verify**: `docker compose run --rm test uv run pytest tests/test_services/test_tracks.py -k enrichment -q` green; the test is shaped so the pre-fix matching logic would fail it (documented in a comment, not requiring a git revert).

| Task | Description | Files | SP | Status |
|------|-------------|-------|----|--------|
| 5.1 | `test_current_track_enriches_relative_path`: reuse the existing `FakeMpd` in this file (returns `{"file": "<rel>"}`), wire it with a real seeded `BeetsAdapter`, assert `current_track()` returns `folder`/`playlists`. Note in-file that this is the Inbox-bug regression and that waybar Pango escaping is covered by `test_waybar.py`. | `tests/test_services/test_tracks.py` | 1 | pending |
| 5.2 | Add a `BEETSDIR`/real-lib guard helper shared by service e2e and adapter e2e to assert isolation (no real-library access). | `tests/support/seeding.py` or `tests/conftest.py` | 1 | pending |

#### Task 5.1 DoD
- [ ] Test fails if `query` path-matching regresses to naive string compare (asserted via the relative-vs-absolute mismatch the bug had).
- [ ] Uses a fake MPD (no real daemon) and a real seeded beets library.
- [ ] Comment links the test to the Inbox bug + the waybar Pango regression location.

---

### M6: Version pinning + CI wiring — 2 SP | pending

**Goal**: beets is pinned to the deployed version with a documented rationale, and the Docker e2e run is wired into CI + CLAUDE.md.

**Verify**: CI workflow runs `docker compose run --rm test`; `pyproject.toml` pins beets; `CLAUDE.md` Testing section names the e2e harness + how to run it.

| Task | Description | Files | SP | Status |
|------|-------------|-------|----|--------|
| 6.1 | Pin `beets` in `pyproject.toml` to the deployed version (`>=2.12,<3` with a comment on the path-reporting behavior); ensure compose `BEETS_VERSION` matches. | `pyproject.toml`, `docker-compose.yml` | 1 | pending |
| 6.2 | CI job (GitHub Actions, matching existing workflows) running the compose e2e suite; update `CLAUDE.md` `## Testing` with `just test` (fast) vs `just test-e2e` (Docker e2e) and the isolation/seeding notes. | `.github/workflows/*`, `CLAUDE.md` | 1 | pending |

#### Task 6.1 DoD
- [ ] `pyproject.toml` constrains beets with a comment explaining the version-sensitive `item.path` behavior.
- [ ] Compose build-arg and the dependency constraint agree.

#### Task 6.2 DoD
- [ ] CI runs the Docker e2e suite on PRs.
- [ ] `CLAUDE.md` Testing section documents both test tiers + the `BEETSDIR` safety invariant.

---

## Test harness contract

- **Selection**: `pytest -m e2e` (Docker, real beets) vs `pytest -m "not e2e"` (host, fast). `just test` = fast; `just test-e2e` = Docker.
- **Isolation invariant**: every e2e test binds beets to a `tmp_path` library and sets `BEETSDIR` to a tmp config. No test may read/write `~/Music` or `~/.config/beets`. A shared guard asserts this.
- **Seeding inputs**: DB-only `seed_item(...)` (rows, no files) + `make_track(...)` (silent ffmpeg files with tags).
- **Determinism**: no real audio, no network, no real daemon; ffmpeg-generated silence is byte-stable per tags.

## Final Verification

- [ ] `docker compose run --rm test uv run pytest tests/ -q` green.
- [ ] `just test` (host, `not e2e`) green and fast.
- [ ] `test_beets.py` contains no `MagicMock`/`patch`/`monkeypatch`.
- [ ] Enrichment regression present and tied to the Inbox bug.
- [ ] CI runs the e2e suite; CLAUDE.md documents both tiers.
- [ ] No e2e test can touch the real beets library (isolation guard passes).

## Out of scope

- Real MPD daemon / MPD integration tests — MPD stays mocked per decision; enrichment uses a fake MPD.
- yad GUI tests — remain mocked.
- A multi-version beets matrix in CI — image is pinned to the deployed version; build-arg leaves the door open but no matrix job is added now.
- Re-testing the waybar Pango fix — already covered by `test_waybar.py`.
- Replacing ffmpeg/tagger adapter mocks — explicitly kept (only beets is de-mocked).

## CLAUDE.md impact

Update `## Testing` to document: `just test` (fast, fakes) vs `just test-e2e` (Docker, real beets); the DB-only + silent-audio seeders; and the `BEETSDIR`/tmp-library isolation invariant. (Handled in Task 6.2.)
