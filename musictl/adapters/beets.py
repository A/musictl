import subprocess

from beets.library import Library

from musictl.config import settings


class BeetsAdapter:
    def __init__(self) -> None:
        self._lib = Library(str(settings.beets_db_path))

    def query(self, query: str) -> list[dict[str, str]]:
        items = self._lib.items(query)
        return [
            {
                "id": str(item.id),
                "path": item.path.decode() if isinstance(item.path, bytes) else str(item.path),
                "artist": str(item.artist),
                "title": str(item.title),
                "album": str(item.album),
                "folder": str(getattr(item, "folder", "") or ""),
                "playlists": str(getattr(item, "playlists", "") or ""),
                "genre": str(item.genre),
            }
            for item in items
        ]

    def get_field(self, query: str, field: str) -> str:
        items = self._lib.items(query)
        for item in items:
            return str(getattr(item, field, ""))
        return ""

    def modify(self, query: str, **fields: str) -> None:
        items = self._lib.items(query)
        for item in items:
            for key, value in fields.items():
                setattr(item, key, value)
            item.store()

    def move(self, query: str) -> None:
        subprocess.run(["beet", "move", query], check=True)

    def remove(self, query: str, delete: bool = False) -> None:
        cmd = ["beet", "remove", "-y", query]
        if delete:
            cmd.insert(2, "-d")
        subprocess.run(cmd, check=True)

    def import_tracks(self, *args: str) -> None:
        subprocess.run(["beet", "import", *args], check=True)

    def all_folders(self) -> list[str]:
        items = self._lib.items("")
        folders: set[str] = set()
        for item in items:
            folder = str(getattr(item, "folder", "") or "")
            if folder:
                folders.add(folder)
        return sorted(folders)

    def all_playlists(self) -> list[str]:
        items = self._lib.items("")
        playlists: set[str] = set()
        for item in items:
            raw = str(getattr(item, "playlists", "") or "")
            for name in raw.split(","):
                name = name.strip()
                if name:
                    playlists.add(name)
        return sorted(playlists)

    def random(self, count: int, query: str = "") -> list[str]:
        cmd = ["beet", "random", "-n", str(count)]
        if query:
            cmd.append(query)
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return [line for line in result.stdout.strip().splitlines() if line]
