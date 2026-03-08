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
        """Generate all playlist .m3u files. Returns list of written playlist paths."""
        tracks = self._beets.query("")
        self._playlists_dir.mkdir(parents=True, exist_ok=True)

        inbox: list[str] = []
        by_folder: dict[str, list[str]] = {}
        by_playlist: dict[str, list[str]] = {}
        no_playlist: list[str] = []

        for track in tracks:
            path = track.get("path", "")
            rel_path = self._relative_path(path)
            folder = track.get("folder", "")
            playlists_raw = track.get("playlists", "")

            if not folder:
                inbox.append(rel_path)
            else:
                by_folder.setdefault(folder, []).append(rel_path)
                playlist_names = [p.strip() for p in playlists_raw.split(",") if p.strip()]
                if playlist_names:
                    for name in playlist_names:
                        by_playlist.setdefault(name, []).append(rel_path)
                else:
                    no_playlist.append(rel_path)

        logger.info(
            "Generating playlists: %d tracks, %d folders, %d playlists",
            len(tracks),
            len(by_folder),
            len(by_playlist),
        )

        written: list[str] = []
        all_tracks: list[str] = []
        collection: list[str] = []

        if inbox:
            written.append(self._write_m3u("inbox", inbox))
            all_tracks.extend(inbox)

        for folder, paths in sorted(by_folder.items()):
            written.append(self._write_m3u(folder, paths))
            all_tracks.extend(paths)
            collection.extend(paths)

        for name, paths in sorted(by_playlist.items()):
            written.append(self._write_m3u(f"playlist_{name}", paths))

        if no_playlist:
            written.append(self._write_m3u("no_playlist", no_playlist))

        if collection:
            written.append(self._write_m3u("collection", collection))
        if all_tracks:
            written.append(self._write_m3u("all", all_tracks))

        return written

    def regenerate(self, folders: list[str], playlists: list[str]) -> list[str]:
        """Regenerate m3u files only for the specified folders and playlists."""
        self._playlists_dir.mkdir(parents=True, exist_ok=True)
        written: list[str] = []

        for folder in folders:
            tracks = self._beets.query(f"folder:{folder}")
            paths = [self._relative_path(t["path"]) for t in tracks]
            if paths:
                written.append(self._write_m3u(folder, paths))
            else:
                self._remove_m3u(folder)

        for name in playlists:
            tracks = self._beets.query(f"playlists:{name}")
            paths = [self._relative_path(t["path"]) for t in tracks]
            if paths:
                written.append(self._write_m3u(f"playlist_{name}", paths))
            else:
                self._remove_m3u(f"playlist_{name}")

        # Rebuild aggregate playlists
        all_tracks_data = self._beets.query("")
        all_paths: list[str] = []
        collection_paths: list[str] = []
        for t in all_tracks_data:
            rel = self._relative_path(t["path"])
            all_paths.append(rel)
            if t.get("folder", ""):
                collection_paths.append(rel)

        if all_paths:
            written.append(self._write_m3u("all", all_paths))
        if collection_paths:
            written.append(self._write_m3u("collection", collection_paths))

        return written

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

    def _remove_m3u(self, name: str) -> None:
        slug = self._slugify(name)
        m3u = self._playlists_dir / f"{slug}.m3u"
        m3u.unlink(missing_ok=True)

    def _slugify(self, name: str) -> str:
        return name.lower().replace(" ", "_")

    def _write_m3u(self, name: str, paths: list[str]) -> str:
        slug = self._slugify(name)
        filepath = self._playlists_dir / f"{slug}.m3u"
        filepath.write_text("\n".join(sorted(paths)) + "\n")
        logger.debug("Wrote %s (%d tracks)", filepath, len(paths))
        return str(filepath)
