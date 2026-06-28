import logging
import os
import subprocess
from pathlib import Path

from beets.library import Item, Library

from musictl.config import settings

logger = logging.getLogger(__name__)


def _item_path(item: Item) -> str:
    raw = item.path
    return raw.decode() if isinstance(raw, bytes) else str(raw)


class BeetsAdapter:
    def __init__(self) -> None:
        self._lib = Library(str(settings.beets_db_path))
        logger.debug("Opened beets DB: %s", settings.beets_db_path)

    def _abs_path(self, path: str) -> str:
        """Resolve a path to a normalized absolute path.

        beets may store paths relative to music_dir (depending on the
        `directory`/import config on a given machine), while callers pass
        absolute paths from MPD. Normalizing both sides through this helper
        makes matching robust regardless of which form either side uses, or
        of `~`, redundant separators, or `..` segments.
        """
        p = Path(path).expanduser()
        abs_path = p if p.is_absolute() else settings.music_dir / p
        return os.path.normpath(str(abs_path))

    def query(self, query: str) -> list[dict[str, str]]:
        logger.debug("Querying: %s", query or "(all)")
        if query.startswith("path:"):
            # Exact path match in Python to avoid beets query parser issues
            # with special characters (commas, colons, etc.) in file paths.
            # Both the stored path and the target are normalized to absolute
            # so a relative DB path matches an absolute MPD path (and vice versa).
            target = self._abs_path(query[5:])
            items = [item for item in self._lib.items("") if self._abs_path(_item_path(item)) == target]
        else:
            items = self._lib.items(query)
        results = [
            {
                "id": str(item.id),
                "path": self._abs_path(_item_path(item)),
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
        cmd = ["beet", "remove", "-f", query]
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

    def all_playlists(self) -> dict[str, int]:
        items = self._lib.items("")
        counts: dict[str, int] = {}
        for item in items:
            raw = str(getattr(item, "playlists", "") or "")
            for name in raw.split(","):
                name = name.strip()
                if name and name not in ("TRUE", "FALSE"):
                    counts[name] = counts.get(name, 0) + 1
        logger.debug("Found %d playlists", len(counts))
        return counts
