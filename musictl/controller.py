#!/usr/bin/env python3
import shutil
import mutagen
from datetime import datetime
from pathlib import Path
from typing import List

from .config import Config
from .file_scanner import FileScanner
from .playlist_manager import PlaylistManager
from .player import Player
from .ui_manager import UIManager
from .mpris import Mpris


class Controller:
    """Main controller orchestrating the application."""

    def __init__(self):
        self.ui = UIManager()
        self.mpris = Mpris()

    def _get_root_items(self) -> List[str]:
        """Get menu items for root directories."""
        base_path = Config.get_base_path()
        root_dirs = Config.get_music_directories()

        items = []
        for root_dir in root_dirs:
            dir_path = base_path / root_dir
            if dir_path.exists():
                scan_result = FileScanner.scan(
                    dir_path,
                    file_patterns=Config.get_music_extensions(),
                    ignored_dirs=Config.get_ignored_dirs(),
                )
                if scan_result["files_total"] > 0:
                    items.append(f"📁 {root_dir} ({scan_result['files_total']} tracks)")

        return items

    def _extract_dir_name(self, item: str) -> str:
        """Extract directory name from menu item."""
        return item.split(" ", 1)[1].split(" (")[0]

    def _play_directory(self, directory: Path):
        """Handle playing music from directory."""
        track_options = [str(option) for option in Config.get_track_count_options()]
        track_count_str = self.ui.select_item(track_options, "Number of tracks")
        if not track_count_str:
            return

        scan_result = FileScanner.scan(
            directory,
            file_patterns=Config.get_music_extensions(),
            ignored_dirs=Config.get_ignored_dirs(),
        )
        if not scan_result["files"]:
            return

        track_count = (
            track_count_str if track_count_str == "ALL" else int(track_count_str)
        )
        playlist_path, _ = PlaylistManager.create_playlist(
            scan_result["files"], str(track_count), directory.name
        )

        Player.play_playlist(playlist_path, Config.get_player_command())

    def _get_target_subdirs(self, target_dir: Path) -> list[str]:
        """Get subdirectories in target directory."""
        if not target_dir.exists():
            return []

        scan_result = FileScanner.scan(
            target_dir, dir_patterns=None, ignored_dirs=Config.get_ignored_dirs()
        )

        return [subdir.name for subdir in scan_result["dirs"]]

    def _move_file(self, source: Path, target_dir: Path, subdir: str) -> bool:
        """Move file to target directory/subdir/YYYY-MM/."""
        try:
            year_month = datetime.now().strftime("%Y-%m")
            final_target_dir = target_dir / subdir / year_month
            final_target_dir.mkdir(parents=True, exist_ok=True)

            target_file = final_target_dir / source.name
            shutil.move(str(source), str(target_file))

            print(f"Moved {source.name} to {final_target_dir}")
            return True
        except Exception as e:
            print(f"Error moving file: {e}")
            return False

    def browse_directory(self, directory: Path):
        """Browse directory and handle user actions."""
        scan_result = FileScanner.scan(
            directory,
            file_patterns=Config.get_music_extensions(),
            ignored_dirs=Config.get_ignored_dirs(),
        )

        items = []
        if scan_result["files_total"] > 0:
            items.append(f"▶ Play ({scan_result['files_total']} tracks)")

        for subdir in scan_result["dirs"]:
            subdir_scan = FileScanner.scan(
                subdir,
                file_patterns=Config.get_music_extensions(),
                ignored_dirs=Config.get_ignored_dirs(),
            )
            if subdir_scan["files_total"] > 0:
                items.append(f"📁 {subdir.name} ({subdir_scan['files_total']} tracks)")

        if not items:
            return

        callbacks = {}

        for item in items:
            if item.startswith("▶ Play"):
                callbacks[item] = lambda _, d=directory: self._play_directory(d)
            elif item.startswith("📁"):
                subdir_name = self._extract_dir_name(item)
                subdir = directory / subdir_name
                callbacks[item] = lambda _, sd=subdir: self.browse_directory(sd)

        self.ui.show_menu(items, callbacks, f"{directory.name}")

    def start(self):
        """Start the application."""
        items = self._get_root_items()

        if not items:
            print("No music directories found")
            return

        callbacks = {}
        base_path = Config.get_base_path()

        for item in items:
            root_name = self._extract_dir_name(item)
            selected_dir = base_path / root_name
            callbacks[item] = lambda _, sd=selected_dir: self.browse_directory(sd)

        self.ui.show_menu(items, callbacks, "Select music directory")

    def pick(self, target_dir_name: str):
        """Pick current track and move it to target directory."""
        music_dirs = Config.get_music_directories()
        if target_dir_name not in music_dirs:
            print(f"Invalid directory. Available: {', '.join(music_dirs)}")
            return

        current_track = self.mpris.get_current_track(Config.get_player_command())
        if not current_track:
            print("No track currently playing or track not found")
            return

        print(f"Current track: {current_track.name}")

        base_path = Config.get_base_path()
        target_dir = base_path / target_dir_name

        if not target_dir.exists():
            print(f"Target directory does not exist: {target_dir}")
            return

        subdirs = self._get_target_subdirs(target_dir)
        if not subdirs:
            print(f"No subdirectories found in {target_dir}")
            return

        selected_subdir = self.ui.select_item(
            subdirs, f"Select subdirectory in {target_dir_name}"
        )
        if not selected_subdir:
            print("No subdirectory selected")
            return

        success = self._move_file(current_track, target_dir, selected_subdir)
        if success:
            print(f"Successfully moved to {target_dir_name}/{selected_subdir}")

    def _extract_metadata(self, file_path: Path) -> tuple[str, str, str, str]:
        """Extract artist, album, track number, and title from file tags."""
        if not mutagen:
            print("Warning: mutagen not installed, using filename fallback")
            return self._extract_from_filename(file_path)

        try:
            audio_file = mutagen.File(file_path)
            if not audio_file:
                return self._extract_from_filename(file_path)

            # Get tags - mutagen returns lists for most formats
            artist = (
                audio_file.get("TPE1") or audio_file.get("ARTIST") or ["Unknown Artist"]
            )
            album = (
                audio_file.get("TALB") or audio_file.get("ALBUM") or ["Unknown Album"]
            )
            track_num = (
                audio_file.get("TRCK") or audio_file.get("TRACKNUMBER") or ["00"]
            )
            title = (
                audio_file.get("TIT2") or audio_file.get("TITLE") or [file_path.stem]
            )

            # Extract first value from lists
            artist = artist[0] if isinstance(artist, list) else str(artist)
            album = album[0] if isinstance(album, list) else str(album)
            track_num = track_num[0] if isinstance(track_num, list) else str(track_num)
            title = title[0] if isinstance(title, list) else str(title)

            # Clean track number (remove "/total" if present)
            if "/" in str(track_num):
                track_num = str(track_num).split("/")[0]

            # Format track number as 2 digits
            try:
                track_num = f"{int(track_num):02d}"
            except (ValueError, TypeError):
                track_num = "00"

            return str(artist), str(album), track_num, str(title)

        except Exception as e:
            print(f"Error reading tags from {file_path}: {e}")
            return self._extract_from_filename(file_path)

    def _extract_from_filename(self, file_path: Path) -> tuple[str, str, str, str]:
        """Fallback: extract metadata from filename and directory structure."""
        # Extract artist from grandparent directory name
        artist_name = file_path.parent.parent.name

        # Extract album from parent directory
        album_dir = file_path.parent.name
        if " - " in album_dir:
            year_part, album_name = album_dir.split(" - ", 1)
        else:
            album_name = album_dir

        # Extract track number and title from filename
        filename = file_path.stem

        if filename.startswith(("01", "02", "03", "04", "05", "06", "07", "08", "09")):
            if " - " in filename:
                track_num, track_title = filename.split(" - ", 1)
            else:
                track_num = filename[:2]
                track_title = filename[2:].strip(" -")
        else:
            track_num = "00"
            track_title = filename

        return artist_name, album_name, track_num, track_title

    def import_tracks(self, target_dir_name: str, source_dir: str):
        """Import tracks from source directory to target directory."""
        source_path = Path(source_dir).resolve()
        if not source_path.exists():
            print(f"Source directory does not exist: {source_path}")
            return

        # Parse target directory (e.g., "collection/indie_inbox")
        target_parts = target_dir_name.split("/")
        if len(target_parts) != 2:
            print(
                "Target format should be: root_dir/subdir (e.g., collection/indie_inbox)"
            )
            return

        root_dir, subdir = target_parts

        # Validate root directory
        music_dirs = Config.get_music_directories()
        if root_dir not in music_dirs:
            print(f"Invalid root directory. Available: {', '.join(music_dirs)}")
            return

        # Create target directory path
        base_path = Config.get_base_path()
        year_month = datetime.now().strftime("%Y-%m")
        target_path = base_path / root_dir / subdir / year_month
        target_path.mkdir(parents=True, exist_ok=True)

        # Find all music files in source directory
        scan_result = FileScanner.scan(
            source_path,
            file_patterns=Config.get_music_extensions(),
            ignored_dirs=Config.get_ignored_dirs(),
        )

        if not scan_result["files"]:
            print(f"No music files found in {source_path}")
            return

        copied_count = 0

        for file_path in scan_result["files"]:
            try:
                # Extract metadata from tags
                artist, album, track_num, title = self._extract_metadata(file_path)

                # Create new filename: Artist - Album - Track - Title.ext
                new_filename = (
                    f"{artist} - {album} - {track_num} - {title}{file_path.suffix}"
                )

                # Copy file to target directory
                target_file = target_path / new_filename

                if target_file.exists():
                    print(f"Skipping existing file: {new_filename}")
                    continue

                shutil.copy2(file_path, target_file)
                copied_count += 1
                print(f"Copied: {new_filename}")

            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue

        print(f"Successfully imported {copied_count} tracks to {target_path}")

    def delete(self):
        """Delete current track."""
        current_track = self.mpris.get_current_track(Config.get_player_command())
        if not current_track:
            print("No track currently playing or track not found")
            return

        print(f"Current track: {current_track.name}")

        confirm_options = ["Yes", "No"]
        confirm = self.ui.select_item(confirm_options, f"Delete {current_track.name}")

        if confirm == "Yes":
            try:
                current_track.unlink()
                print(f"Deleted {current_track.name}")
            except Exception as e:
                print(f"Error deleting file: {e}")
        else:
            print("Deletion cancelled")

    def search(self):
        """Search and play a music file."""
        base_path = Config.get_base_path()
        root_dirs = Config.get_music_directories()

        all_files = []

        for root_dir in root_dirs:
            dir_path = base_path / root_dir
            if dir_path.exists():
                scan_result = FileScanner.scan(
                    dir_path,
                    file_patterns=Config.get_music_extensions(),
                    ignored_dirs=Config.get_ignored_dirs(),
                )
                all_files.extend(scan_result["files"])

        if not all_files:
            print("No music files found")
            return

        # Create searchable strings with relative paths from base directory
        file_options = []
        for f in all_files:
            try:
                relative_path = f.relative_to(base_path)
                file_options.append(str(relative_path))
            except ValueError:
                # If file is not under base_path, use full path
                file_options.append(str(f))

        selected_path = self.ui.select_item(file_options, "Search and select track")

        if not selected_path:
            print("No file selected")
            return

        # Find the corresponding file
        if selected_path.startswith("/"):
            selected_file = Path(selected_path)
        else:
            selected_file = base_path / selected_path

        if not selected_file.exists():
            print("File not found")
            return

        playlist_path, _ = PlaylistManager.create_playlist(
            [selected_file], "1", "search"
        )
        Player.play_playlist(playlist_path, Config.get_player_command())
        print(f"Playing: {selected_file.name}")
