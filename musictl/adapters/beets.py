import logging
import subprocess

from beets.library import Library

from musictl.config import settings

logger = logging.getLogger(__name__)


class BeetsAdapter:
    def __init__(self) -> None:
        self._lib = Library(str(settings.beets_db_path))
        logger.debug("Opened beets DB: %s", settings.beets_db_path)

    def query(self, query: str) -> list[dict[str, str]]:
        logger.debug("Querying: %s", query or "(all)")
        items = self._lib.items(query)
        results = [
            {
                "id": str(item.id),
                "path": item.path.decode() if isinstance(item.path, bytes) else str(item.path),
                "artist": str(item.artist),
                "title": str(item.title),
                "album": str(item.album),
                "folder": str(getattr(item, "folder", "") or ""),
                "playlists": str(getattr(item, "playlists", "") or ""),
            }
            for item in items
        ]
        logger.debug("Query returned %d items", len(results))
        return results

    def get_field(self, query: str, field: str) -> str:
        items = self._lib.items(query)
        for item in items:
            return str(getattr(item, field, ""))
        return ""

    def modify(self, query: str, **fields: str) -> None:
        logger.info("Modify %s: %s", query, fields)
        cmd = ["beet", "modify", "-y", "-m", query]
        for key, value in fields.items():
            cmd.append(f"{key}={value}")
        subprocess.run(cmd, check=True)

    def move(self, query: str) -> None:
        logger.info("Move: %s", query)
        subprocess.run(["beet", "move", query], check=True)

    def remove(self, query: str, delete: bool = False) -> None:
        logger.info("Remove: %s (delete=%s)", query, delete)
        cmd = ["beet", "remove", "-y", query]
        if delete:
            cmd.insert(2, "-d")
        subprocess.run(cmd, check=True)

    def import_tracks(self, *args: str) -> None:
        logger.info("Import: %s", args)
        subprocess.run(["beet", "import", *args], check=True)

    def all_folders(self) -> list[str]:
        items = self._lib.items("")
        folders: set[str] = set()
        for item in items:
            folder = str(getattr(item, "folder", "") or "")
            if folder:
                folders.add(folder)
        logger.debug("Found %d folders", len(folders))
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
        logger.debug("Found %d playlists", len(playlists))
        return sorted(playlists)
