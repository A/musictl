from mpd import ConnectionError as MpdConnectionError
from mpd import MPDClient

from musictl.config import settings


class MpdAdapter:
    def __init__(self) -> None:
        self._client = MPDClient()
        self._connected = False

    def connect(self) -> None:
        if not self._connected:
            self._client.connect(settings.mpd_host, settings.mpd_port)
            self._connected = True

    def _ensure_connected(self) -> None:
        try:
            self._client.ping()
        except (MpdConnectionError, ConnectionError, BrokenPipeError, OSError):
            self._connected = False
            self._client = MPDClient()
            self.connect()

    def current_song(self) -> dict[str, str] | None:
        self._ensure_connected()
        song = self._client.currentsong()
        return song if song else None

    def add(self, uri: str) -> None:
        self._ensure_connected()
        self._client.add(uri)

    def play(self, pos: int = 0) -> None:
        self._ensure_connected()
        self._client.play(pos)

    def clear(self) -> None:
        self._ensure_connected()
        self._client.clear()

    def delete(self, pos: int) -> None:
        self._ensure_connected()
        self._client.delete(pos)

    def load_playlist(self, name: str) -> None:
        self._ensure_connected()
        self._client.load(name)

    def list_playlists(self) -> list[str]:
        self._ensure_connected()
        return [p["playlist"] for p in self._client.listplaylists()]

    def list_playlist_tracks(self, name: str) -> list[str]:
        self._ensure_connected()
        return self._client.listplaylist(name)

    def search(self, query: str) -> list[dict[str, str]]:
        self._ensure_connected()
        return self._client.search("any", query)

    def update(self) -> None:
        self._ensure_connected()
        self._client.update()

    def current_position(self) -> int | None:
        self._ensure_connected()
        status = self._client.status()
        song = status.get("song")
        return int(song) if song is not None else None

    def queue_count(self) -> int:
        self._ensure_connected()
        status = self._client.status()
        return int(status.get("playlistlength", 0))
