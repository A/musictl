#!/usr/bin/env python3
import subprocess
from pathlib import Path


class Player:
    """Handles music playback."""

    @staticmethod
    def play_playlist(playlist_path: Path, player_command: str = "deadbeef"):
        """Play playlist file."""
        try:
            subprocess.Popen(
                [player_command, str(playlist_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"Started {player_command} with playlist: {playlist_path}")

        except FileNotFoundError:
            print(f"Player '{player_command}' not found")
        except Exception as e:
            print(f"Error starting player: {e}")
