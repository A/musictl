import logging

from mutagen import File

logger = logging.getLogger(__name__)


class TaggerAdapter:
    def read_tags(self, path: str) -> dict[str, str]:
        logger.debug("Reading tags: %s", path)
        audio = File(path, easy=True)
        if audio is None:
            return {}
        tags: dict[str, str] = {}
        for key in ("artist", "album", "genre", "title"):
            values = audio.get(key)
            if values:
                tags[key] = values[0]
        return tags

    def write_tags(self, path: str, tags: dict[str, str]) -> None:
        logger.debug("Writing tags to %s: %s", path, tags)
        audio = File(path, easy=True)
        if audio is None:
            return
        for key, value in tags.items():
            audio[key] = value
        audio.save()
