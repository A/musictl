#!/usr/bin/env python3
import yaml
from pathlib import Path
from typing import List


class Config:
    """Configuration manager for musictl."""

    _config = None
    _config_path = Path.home() / ".config" / "musictl" / "config.yml"

    @classmethod
    def _load_config(cls):
        """Load config from file, create default if missing."""
        if cls._config is not None:
            return

        if cls._config_path.exists():
            with open(cls._config_path, "r") as f:
                cls._config = yaml.safe_load(f) or {}
        else:
            cls._config = cls._get_default_config()
            cls._save_config()

    @classmethod
    def _get_default_config(cls) -> dict:
        """Get default configuration."""
        return {
            "track_count_options": [10, 50, 100, "ALL"],
            "music_directories": ["collection", "inbox", "dj"],
            "base_path": "~/Dropbox",
            "player_command": "deadbeef",
            "ignored_dirs": ["downloads", ".git", "__pycache__"],
            "music_extensions": [".mp3", ".flac", ".wav", ".ogg", ".m4a"],
        }

    @classmethod
    def _save_config(cls):
        """Save config to file."""
        cls._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cls._config_path, "w") as f:
            yaml.dump(cls._config, f, default_flow_style=False)

    @classmethod
    def get_track_count_options(cls) -> List[str]:
        cls._load_config()
        return cls._config["track_count_options"]

    @classmethod
    def get_music_directories(cls) -> List[str]:
        cls._load_config()
        return cls._config["music_directories"]

    @classmethod
    def get_base_path(cls) -> Path:
        cls._load_config()
        return Path(cls._config["base_path"]).expanduser()

    @classmethod
    def get_player_command(cls) -> str:
        cls._load_config()
        return cls._config["player_command"]

    @classmethod
    def get_ignored_dirs(cls) -> set:
        cls._load_config()
        return set(cls._config["ignored_dirs"])

    @classmethod
    def get_music_extensions(cls) -> List[str]:
        cls._load_config()
        return cls._config["music_extensions"]
