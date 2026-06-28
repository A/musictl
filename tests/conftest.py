"""Shared e2e fixtures: a tmp-isolated, real beets library.

Isolation is safety-critical: every e2e fixture points BOTH `BEETSDIR` and
`HOME` at tmp dirs so no test ever reads or writes the real `~/Music` or
`~/.config/beets`.

Bug-reproducing invariant: beets `directory` MUST differ from
`Settings.music_dir`. beets 2.12 returns DB paths absolutized against the
library `directory`; if `directory == music_dir` that absolutized path equals
the MPD-constructed path and the Inbox-enrichment regression would be
green-but-inert. We set `directory = HOME` and `music_dir = HOME/Music`, which
reproduces the real mismatch and lines up with `_music_rel`'s two reduction
bases (music_dir and `Path.home()`).
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from musictl.adapters.beets import BeetsAdapter
from musictl.config import Settings
from tests.support.seeding import make_track


@dataclass
class BeetsEnv:
    home: Path
    beetsdir: Path
    directory: Path
    music_dir: Path
    db_path: Path


def assert_isolated(beets_env: BeetsEnv, path: Path | None = None) -> None:
    """Shared isolation guard for e2e tests (service + adapter).

    The one safety-critical invariant: no test may read or write the real
    `~/Music` / `~/.config/beets`. HOME and BEETSDIR are fixture-patched to tmp
    dirs, so `~/Music` must resolve to the tmp music dir and BEETSDIR must point
    at the tmp config. Optionally assert a concrete file path stays under the
    tmp HOME.
    """
    assert Path("~/Music").expanduser().resolve() == beets_env.music_dir.resolve()
    assert os.environ.get("BEETSDIR") == str(beets_env.beetsdir)
    if path is not None:
        assert str(path.resolve()).startswith(str(beets_env.home.resolve()))


@pytest.fixture
def beets_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BeetsEnv:
    home = tmp_path / "home"
    beetsdir = home / ".config" / "beets"
    directory = home
    music_dir = home / "Music"
    db_path = beetsdir / "library.db"

    beetsdir.mkdir(parents=True)
    music_dir.mkdir(parents=True)

    config = "\n".join(
        [
            f"directory: {directory}",
            f"library: {db_path}",
            "import:",
            "    autotag: no",
            "",
        ]
    )
    (beetsdir / "config.yaml").write_text(config)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("BEETSDIR", str(beetsdir))

    return BeetsEnv(
        home=home,
        beetsdir=beetsdir,
        directory=directory,
        music_dir=music_dir,
        db_path=db_path,
    )


@pytest.fixture
def tmp_settings(beets_env: BeetsEnv) -> Settings:
    settings = Settings(
        music_dir=beets_env.music_dir,
        beets_db_path=beets_env.db_path,
        playlists_dir=beets_env.music_dir / "playlists",
    )
    # Make-or-break invariant: beets directory != music_dir so beets 2.12
    # absolutizes DB paths to something that does NOT equal the MPD path.
    assert beets_env.directory != settings.music_dir
    return settings


@pytest.fixture
def beets_adapter(tmp_settings: Settings) -> BeetsAdapter:
    return BeetsAdapter(settings=tmp_settings)


@pytest.fixture
def track_factory() -> Callable[..., Path]:
    """Expose the silent-track generator (session-cached base file)."""
    return make_track
