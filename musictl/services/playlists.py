from pathlib import Path

from musictl.config import Settings
from musictl.protocols import BeetsBackend, MpdBackend


class PlaylistService:
    def __init__(self, mpd: MpdBackend, beets: BeetsBackend, settings: Settings) -> None:
        self._mpd = mpd
        self._beets = beets
        self._music_dir = settings.music_dir
        self._playlists_dir = settings.playlists_dir

    def load(self, name: str) -> None:
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

        written: list[str] = []

        if inbox:
            written.append(self._write_m3u("inbox", inbox))

        for folder, paths in sorted(by_folder.items()):
            written.append(self._write_m3u(folder, paths))

        for name, paths in sorted(by_playlist.items()):
            written.append(self._write_m3u(f"playlist_{name}", paths))

        if no_playlist:
            written.append(self._write_m3u("no_playlist", no_playlist))

        return written

    def rename(self, old_name: str, new_name: str) -> None:
        """Rename a playlist: update playlists field on matching tracks, sync comments."""
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

    def _write_m3u(self, name: str, paths: list[str]) -> str:
        filepath = self._playlists_dir / f"{name}.m3u"
        filepath.write_text("\n".join(sorted(paths)) + "\n")
        return str(filepath)
