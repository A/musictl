#!/usr/bin/env python3
import shutil
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

        self.ui.show_menu(items, callbacks, f"{directory.name}:")

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

        self.ui.show_menu(items, callbacks, "Select music directory:")

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
