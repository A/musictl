import logging
from pathlib import Path

from musictl.config import Settings
from musictl.protocols import BeetsBackend, MpdBackend

logger = logging.getLogger(__name__)


class PlaylistService:
    def __init__(self, mpd: MpdBackend, beets: BeetsBackend, settings: Settings) -> None:
        self._mpd = mpd
        self._beets = beets
        self._music_dir = settings.music_dir
        self._playlists_dir = settings.playlists_dir

    def load(self, name: str) -> None:
        logger.info("Loading playlist: %s", name)
        self._mpd.clear()
        self._mpd.load_playlist(name)

    def generate_all(self) -> list[str]:
        """Generate all playlist .m3u files, overwriting everything."""
        desired = self._build_playlists()
        self._playlists_dir.mkdir(parents=True, exist_ok=True)
        written: list[str] = []
        for name, paths in sorted(desired.items()):
            written.append(self._write_m3u(name, paths))
        return written

    def regenerate(self) -> list[str]:
        """Regenerate playlists, only writing changed files and removing empty ones."""
        desired = self._build_playlists()
        self._playlists_dir.mkdir(parents=True, exist_ok=True)
        written: list[str] = []
        existing = {p.stem for p in self._playlists_dir.glob("*.m3u")}

        for name, paths in sorted(desired.items()):
            slug = self._slugify(name)
            m3u = self._playlists_dir / f"{slug}.m3u"
            content = "\n".join(sorted(paths)) + "\n"
            if not m3u.exists() or m3u.read_text() != content:
                written.append(self._write_m3u(name, paths))
            existing.discard(slug)

        for stale in existing:
            (self._playlists_dir / f"{stale}.m3u").unlink()
            logger.info("Removed stale playlist: %s.m3u", stale)

        return written

    def _build_playlists(self) -> dict[str, list[str]]:
        """Build the full set of playlist name -> relative paths."""
        tracks = self._beets.query("")
        result: dict[str, list[str]] = {}
        all_paths: list[str] = []
        collection: list[str] = []

        for track in tracks:
            rel_path = self._relative_path(track.get("path", ""))
            folder = track.get("folder", "")
            playlists_raw = track.get("playlists", "")
            all_paths.append(rel_path)

            if not folder:
                result.setdefault("inbox", []).append(rel_path)
            else:
                collection.append(rel_path)
                result.setdefault(folder, []).append(rel_path)
                playlist_names = [p.strip() for p in playlists_raw.split(",") if p.strip()]
                if playlist_names:
                    for name in playlist_names:
                        result.setdefault(f"playlist_{name}", []).append(rel_path)
                else:
                    result.setdefault("no_playlist", []).append(rel_path)

        if collection:
            result["collection"] = collection
        if all_paths:
            result["all"] = all_paths

        logger.info("Built %d playlists from %d tracks", len(result), len(tracks))
        return result

    def rename(self, old_name: str, new_name: str) -> None:
        """Rename a playlist: update playlists field on matching tracks, sync comments."""
        logger.info("Renaming playlist: %s -> %s", old_name, new_name)
        tracks = self._beets.query(f"playlists:{old_name}")
        for track in tracks:
            playlists_raw = track.get("playlists", "")
            names = [p.strip() for p in playlists_raw.split(",") if p.strip()]
            updated = [new_name if n == old_name else n for n in names]
            new_playlists = ",".join(updated)
            query = f"path:{track['path']}"
            self._beets.modify(query, playlists=new_playlists, comments=f"playlists:{new_playlists}")
        self.generate_all()

    def _relative_path(self, absolute_path: str) -> str:
        try:
            return str(Path(absolute_path).relative_to(self._music_dir))
        except ValueError:
            return absolute_path

    def _slugify(self, name: str) -> str:
        return name.lower().replace(" ", "_")

    def _write_m3u(self, name: str, paths: list[str]) -> str:
        slug = self._slugify(name)
        filepath = self._playlists_dir / f"{slug}.m3u"
        filepath.write_text("\n".join(sorted(paths)) + "\n")
        logger.debug("Wrote %s (%d tracks)", filepath, len(paths))
        return str(filepath)
