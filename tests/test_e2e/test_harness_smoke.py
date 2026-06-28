"""Smoke test for the e2e harness: real beets Library + seeders + isolation.

Verifies M1/M2 wiring end to end: a tmp-isolated `BeetsAdapter`, a DB-only
seeded row, and a generated silent track all read back through the real beets
Library, and the silent file is importable by the `beet` CLI offline.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from musictl.adapters.beets import BeetsAdapter
from tests.conftest import BeetsEnv
from tests.support.seeding import make_track, seed_item

pytestmark = pytest.mark.e2e


def test_harness_smoke(
    beets_adapter: BeetsAdapter,
    beets_env: BeetsEnv,
    track_factory: Callable[..., Path],
) -> None:
    lib = beets_adapter._lib

    seed_item(lib, path="Folder/db_only.flac", folder="rock", playlists="chill,workout")
    track = track_factory(beets_env.music_dir, "Ambient/silent.flac", artist="A", title="T", album="Al")
    seed_item(lib, path="Ambient/silent.flac", folder="ambient", playlists="focus")

    results = beets_adapter.query("")

    assert len(results) == 2
    assert {r["folder"] for r in results} == {"rock", "ambient"}
    assert {r["playlists"] for r in results} == {"chill,workout", "focus"}

    assert track.exists()

    # The generated silent file is importable by the real beet CLI, offline
    # (autotag: no from the fixture config; BEETSDIR points at the tmp library).
    inbox = beets_env.home / "inbox"
    make_track(inbox, "import_me.flac", artist="I", title="IT", album="IA")
    beets_adapter.import_tracks("-q", str(inbox))

    # The import added a third row to the same tmp library.
    assert len(beets_adapter.query("")) == 3
