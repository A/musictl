#!/usr/bin/env python3
import random
import tempfile
from pathlib import Path
from typing import List, Tuple


class PlaylistManager:
    """Creates playlists from list of files."""
    
    @staticmethod
    def create_playlist(music_files: List[Path], track_count: str, name: str = "playlist") -> Tuple[Path, int]:
        """Create temporary playlist file from list of music files."""
        if not music_files:
            raise ValueError("No music files provided")
        
        # Select files
        if track_count == 'ALL':
            selected_files = music_files
        else:
            count = int(track_count)
            selected_files = random.sample(music_files, min(count, len(music_files)))
        
        # Create playlist
        playlist_path = Path(tempfile.gettempdir()) / f"{name}.m3u"
        
        with open(playlist_path, 'w') as f:
            for file_path in selected_files:
                f.write(f"{file_path}\n")
        
        return playlist_path, len(selected_files)
