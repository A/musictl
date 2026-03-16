import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

CONFIG_PATH = Path.home() / ".config" / "musictl" / "config.yml"


@dataclass
class Settings:
    music_dir: Path = field(default_factory=lambda: Path.home() / "Music")
    mpd_host: str = "localhost"
    mpd_port: int = 6600
    beets_db_path: Path = field(default_factory=lambda: Path.home() / ".config" / "beets" / "library.db")
    playlists_dir: Path = field(default_factory=lambda: Path.home() / "Music" / "playlists")
    audio_extensions: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {".flac", ".mp3", ".ogg", ".opus", ".m4a", ".wav", ".wma", ".aac", ".ape", ".wv"}
        )
    )


def load_settings() -> Settings:
    if not CONFIG_PATH.exists():
        logger.warning("Config file not found: %s, using defaults", CONFIG_PATH)
        return Settings()

    with CONFIG_PATH.open() as f:
        data = yaml.safe_load(f) or {}

    defaults = Settings()
    music_dir = Path(data["music_dir"]).expanduser() if "music_dir" in data else defaults.music_dir
    beets_db_path = Path(data["beets_db_path"]).expanduser() if "beets_db_path" in data else defaults.beets_db_path
    playlists_dir = Path(data["playlists_dir"]).expanduser() if "playlists_dir" in data else defaults.playlists_dir
    mpd_host = str(data["mpd_host"]) if "mpd_host" in data else defaults.mpd_host
    mpd_port = int(data["mpd_port"]) if "mpd_port" in data else defaults.mpd_port
    audio_extensions = frozenset(data["audio_extensions"]) if "audio_extensions" in data else defaults.audio_extensions

    return Settings(
        music_dir=music_dir,
        beets_db_path=beets_db_path,
        playlists_dir=playlists_dir,
        mpd_host=mpd_host,
        mpd_port=mpd_port,
        audio_extensions=audio_extensions,
    )


settings = load_settings()
