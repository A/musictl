"""Real-library + real-CLI tests for BeetsAdapter.

No mocks: query/get_field/collection logic runs against a real seeded
`beets.library.Library`, and the file-op commands run the real `beet` CLI
against silent fixture tracks in an isolated `BEETSDIR`.
"""

import os
from pathlib import Path

import pytest
from beets.library import Library

from musictl.adapters.beets import BeetsAdapter, _item_path
from musictl.config import Settings
from tests.conftest import BeetsEnv, assert_isolated
from tests.support.seeding import make_track, seed_item


class TestQuery:
    def test_returns_item_dicts(self, beets_adapter: BeetsAdapter):
        seed_item(
            beets_adapter._lib,
            path="rock/song.flac",
            folder="rock",
            playlists="chill,workout",
            artist="Rocker",
            title="Anthem",
            album="LP",
        )

        result = beets_adapter.query("artist:Rocker")

        assert len(result) == 1
        assert result[0]["artist"] == "Rocker"
        assert result[0]["folder"] == "rock"
        assert result[0]["playlists"] == "chill,workout"

    def test_returns_empty_list(self, beets_adapter: BeetsAdapter):
        seed_item(beets_adapter._lib, path="rock/song.flac", artist="Rocker")

        assert beets_adapter.query("artist:Nonexistent") == []

    def test_handles_missing_custom_fields(self, beets_adapter: BeetsAdapter):
        seed_item(beets_adapter._lib, path="x/song.flac", artist="Plain")

        result = beets_adapter.query("artist:Plain")

        assert result[0]["folder"] == ""
        assert result[0]["playlists"] == ""


class TestPathQuery:
    """`path:` queries must match regardless of how beets reports item paths.

    A DB storing music_dir-relative paths is reported differently per beets
    version (2.7 passes them through relative; 2.12 absolutizes them against the
    library `directory`, which the fixture deliberately sets != `music_dir`).
    MPD always passes an absolute music_dir path. All forms must reduce to the
    same music_dir-relative tail, or the current track is left un-enriched (no
    folder/playlists -> "Inbox"). Expectations are derived from the seeded item
    at runtime, never hard-coded per version.
    """

    REL = "Ambient/Kavinsky & Lovefoxxx - Wrong Floor.flac"

    def test_relative_db_path_matched_by_absolute_query(self, beets_adapter: BeetsAdapter, tmp_settings: Settings):
        item = seed_item(beets_adapter._lib, path=self.REL, folder="Ambient", playlists="drive")

        abs_query_target = str(tmp_settings.music_dir / self.REL)

        # Discriminating check: the raw reported path does NOT string-equal the
        # absolute MPD-constructed target, so a naive string compare would miss
        # it (this is exactly the Inbox-enrichment bug condition).
        reported = _item_path(item)
        assert reported != abs_query_target

        result = beets_adapter.query(f"path:{abs_query_target}")

        assert len(result) == 1
        assert result[0]["folder"] == "Ambient"
        assert result[0]["playlists"] == "drive"
        # Returned path is normalized back under music_dir.
        assert result[0]["path"] == os.path.normpath(abs_query_target)

    def test_no_match_returns_empty(self, beets_adapter: BeetsAdapter, tmp_settings: Settings):
        seed_item(beets_adapter._lib, path="Ambient/Other.flac", folder="Ambient")

        abs_query_target = str(tmp_settings.music_dir / self.REL)

        assert beets_adapter.query(f"path:{abs_query_target}") == []


class TestGetField:
    def test_returns_field_value(self, beets_adapter: BeetsAdapter):
        seed_item(beets_adapter._lib, path="jazz/song.flac", folder="jazz", artist="Miles")

        assert beets_adapter.get_field("artist:Miles", "folder") == "jazz"

    def test_returns_empty_when_no_match(self, beets_adapter: BeetsAdapter):
        seed_item(beets_adapter._lib, path="jazz/song.flac", artist="Miles")

        assert beets_adapter.get_field("artist:Nobody", "folder") == ""


class TestCollections:
    def test_all_folders(self, beets_adapter: BeetsAdapter):
        seed_item(beets_adapter._lib, path="a.flac", folder="rock", artist="A")
        seed_item(beets_adapter._lib, path="b.flac", folder="jazz", artist="B")
        seed_item(beets_adapter._lib, path="c.flac", folder="rock", artist="C")
        seed_item(beets_adapter._lib, path="d.flac", folder="", artist="D")

        assert beets_adapter.all_folders() == ["jazz", "rock"]

    def test_all_playlists(self, beets_adapter: BeetsAdapter):
        seed_item(beets_adapter._lib, path="a.flac", playlists="chill,workout", artist="A")
        seed_item(beets_adapter._lib, path="b.flac", playlists="workout,focus", artist="B")
        seed_item(beets_adapter._lib, path="c.flac", playlists="", artist="C")

        assert beets_adapter.all_playlists() == {"chill": 1, "focus": 1, "workout": 2}


def _settings_from_env(beets_env: BeetsEnv) -> Settings:
    return Settings(
        music_dir=beets_env.music_dir,
        beets_db_path=beets_env.db_path,
        playlists_dir=beets_env.music_dir / "playlists",
    )


@pytest.mark.e2e
class TestFileOps:
    """File-op commands run the real `beet` CLI against silent fixtures and are
    asserted by their real effects (DB field + on-disk relocation/deletion),
    not by argv strings. Imports run offline via `autotag: no` + `--quiet`."""

    def _import(self, beets_adapter: BeetsAdapter, src_dir: Path, *flags: str, **tags: str) -> None:
        make_track(src_dir, "song.flac", **tags)
        beets_adapter.import_tracks("--quiet", "--noautotag", *flags, str(src_dir))

    def _real_path(self, beets_env: BeetsEnv, query: str) -> Path:
        """The actual on-disk file path beets stores (placed under the library
        `directory`), read raw via a fresh Library so it reflects subprocess
        commits — distinct from `adapter.query`'s music_dir-normalized path."""
        items = list(Library(str(beets_env.db_path)).items(query))
        assert len(items) == 1
        return Path(_item_path(items[0]))

    def test_modify_changes_field_and_moves_file(self, beets_adapter: BeetsAdapter, beets_env: BeetsEnv):
        inbox = beets_env.home / "inbox"
        self._import(beets_adapter, inbox, artist="Art", title="Original", album="Alb")
        old_path = self._real_path(beets_env, "artist:Art")
        assert old_path.exists()
        assert_isolated(beets_env, old_path)

        # `-m` (modify) moves the file because the default path format includes
        # the changed field ($title).
        beets_adapter.modify("artist:Art", title="Renamed")

        rows = BeetsAdapter(settings=_settings_from_env(beets_env)).query("artist:Art")
        assert len(rows) == 1
        assert rows[0]["title"] == "Renamed"

        new_path = self._real_path(beets_env, "artist:Art")
        assert_isolated(beets_env, new_path)
        assert new_path != old_path
        assert new_path.exists()
        assert not old_path.exists()

    def test_move_relocates_per_path_template(self, beets_adapter: BeetsAdapter, beets_env: BeetsEnv):
        # Import in place (`--nocopy`) so the file starts at a non-template
        # location; `move` must then relocate it per the library path template.
        stray = beets_env.music_dir / "_stray"
        self._import(beets_adapter, stray, "--nocopy", artist="Mover", title="Song", album="Alb")
        stray_path = self._real_path(beets_env, "artist:Mover")
        assert stray_path.parent == stray
        assert stray_path.exists()

        beets_adapter.move("artist:Mover")

        relocated = self._real_path(beets_env, "artist:Mover")
        assert_isolated(beets_env, relocated)
        assert relocated.parent != stray
        assert relocated.exists()
        assert not stray_path.exists()

    def test_remove_with_delete_drops_row_and_unlinks_file(self, beets_adapter: BeetsAdapter, beets_env: BeetsEnv):
        inbox = beets_env.home / "inbox"
        self._import(beets_adapter, inbox, artist="Doomed", title="Bye", album="Alb")
        path = self._real_path(beets_env, "artist:Doomed")
        assert path.exists()
        assert_isolated(beets_env, path)

        beets_adapter.remove("artist:Doomed", delete=True)

        rows = BeetsAdapter(settings=_settings_from_env(beets_env)).query("artist:Doomed")
        assert rows == []
        assert not path.exists()
