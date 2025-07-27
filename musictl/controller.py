#!/usr/bin/env python3
import shutil
import mutagen
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List

from .config import Config
from .file_scanner import FileScanner
from .playlist_manager import PlaylistManager
from .player import Player
from .ui_manager import UIManager
from .mpris import Mpris
from .cue_splitter import CueSplitter


class Controller:
    """Main controller orchestrating the application."""

    def __init__(self):
        self.ui = UIManager()
        self.mpris = Mpris()
        self.cue_splitter = CueSplitter()

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

    def _find_cue_files(self, directory: Path) -> list[tuple[Path, Path]]:
        """Find FLAC/WAV files with corresponding CUE files."""
        cue_pairs = []
        
        for audio_file in directory.glob("*.flac"):
            cue_file = audio_file.with_suffix('.cue')
            if cue_file.exists():
                cue_pairs.append((audio_file, cue_file))
        
        for audio_file in directory.glob("*.wav"):
            cue_file = audio_file.with_suffix('.cue')
            if cue_file.exists():
                cue_pairs.append((audio_file, cue_file))
        
        return cue_pairs
    
    def _parse_cue_file(self, cue_file: Path) -> list[dict]:
        """Parse CUE file and extract track information."""
        tracks = []
        current_track = {}
        
        try:
            with open(cue_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encodings
            try:
                with open(cue_file, 'r', encoding='cp1251') as f:
                    content = f.read()
            except:
                print(f"Could not read CUE file: {cue_file}")
                return []
        
        lines = content.split('\n')
        album_title = ""
        album_artist = ""
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('TITLE '):
                title = line[6:].strip('"')
                if not album_title:
                    album_title = title
                else:
                    current_track['title'] = title
            
            elif line.startswith('PERFORMER '):
                performer = line[10:].strip('"')
                if not album_artist:
                    album_artist = performer
                else:
                    current_track['artist'] = performer
            
            elif line.startswith('TRACK '):
                if current_track:
                    tracks.append(current_track)
                track_parts = line.split()
                track_num = track_parts[1]
                current_track = {
                    'track_num': f"{int(track_num):02d}",
                    'album': album_title,
                    'album_artist': album_artist
                }
            
            elif line.startswith('INDEX 01 '):
                current_track['index'] = line[9:].strip()
        
        if current_track:
            tracks.append(current_track)
        
        # Fill missing artist fields with album artist
        for track in tracks:
            if 'artist' not in track:
                track['artist'] = album_artist
        
        return tracks
    
    def _split_audio_file(self, audio_file: Path, cue_file: Path, output_dir: Path) -> list[Path]:
        """Split audio file using CUE file with ffmpeg."""
        tracks = self._parse_cue_file(cue_file)
        if not tracks:
            return []
        
        output_files = []
        
        for i, track in enumerate(tracks):
            # Create output filename
            artist = track.get('artist', 'Unknown Artist')
            album = track.get('album', 'Unknown Album')
            track_num = track.get('track_num', '00')
            title = track.get('title', f'Track {track_num}')
            
            output_filename = f"{artist} - {album} - {track_num} - {title}.flac"
            output_path = output_dir / output_filename
            
            # Build ffmpeg command
            cmd = ['ffmpeg', '-i', str(audio_file), '-c', 'copy']
            
            # Set start time
            if 'index' in track:
                cmd.extend(['-ss', track['index']])
            
            # Set end time (start of next track)
            if i + 1 < len(tracks) and 'index' in tracks[i + 1]:
                cmd.extend(['-to', tracks[i + 1]['index']])
            
            cmd.append(str(output_path))
            
            try:
                import subprocess
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    output_files.append(output_path)
                    print(f"Extracted: {output_filename}")
                else:
                    print(f"Error extracting track {track_num}: {result.stderr}")
            except Exception as e:
                print(f"Error running ffmpeg: {e}")
                continue
        
        return output_files
    
    def _log_import(self, source_file: Path, target_file: Path):
        """Log imported file to import log."""
        try:
            log_file = Config.get_import_log_file()
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"{timestamp} | {source_file.absolute()} -> {target_file.absolute()}\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Warning: Could not write to import log: {e}")

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

        # Check for CUE files in subdirectories
        cue_pairs = []
        for item in source_path.rglob("*"):
            if item.is_dir():
                pairs = self.cue_splitter.find_cue_files(item)
                cue_pairs.extend(pairs)
        
        # Also check root directory
        root_pairs = self.cue_splitter.find_cue_files(source_path)
        cue_pairs.extend(root_pairs)
        
        # Debug: show what we found
        print(f"Debug: Found {len(cue_pairs)} CUE pairs")
        for cue_file, audio_file in cue_pairs:
            print(f"  CUE: {cue_file.name} -> Audio: {audio_file.name}")
        
        # Process CUE files if found
        temp_extracted_files = []
        temp_dir = None
        
        try:
            if cue_pairs:
                print(f"Found {len(cue_pairs)} CUE files with audio:")
                for cue_file, audio_file in cue_pairs:
                    try:
                        artist, album, tracks = self.cue_splitter.parse_cue(cue_file)
                        print(f"\n{audio_file.name} ({artist} - {album}) -> {len(tracks)} tracks:")
                        # Show all tracks, not just first 3
                        for track in tracks:
                            print(f"  {track}")
                    except Exception as e:
                        print(f"Error parsing {cue_file}: {e}")
                        continue
                
                response = input("\nDo you want to split these files using CUE data? (y/N): ").strip().lower()
                
                if response in ['y', 'yes']:
                    # Create temporary directory for extracted files
                    temp_dir = Path(tempfile.mkdtemp())
                    
                    for cue_file, audio_file in cue_pairs:
                        try:
                            print(f"Splitting {audio_file.name}...")
                            artist, album, tracks = self.cue_splitter.parse_cue(cue_file)
                            extracted = self.cue_splitter.split_audio(audio_file, tracks, temp_dir)
                            
                            # Rename extracted files to final format
                            for i, extracted_file in enumerate(extracted):
                                if i < len(tracks):
                                    track = tracks[i]
                                    final_name = f"{track.performer} - {album} - {track.number:02d} - {track.title}{extracted_file.suffix}"
                                    final_path = temp_dir / final_name
                                    extracted_file.rename(final_path)
                                    temp_extracted_files.append(final_path)
                            
                        except KeyboardInterrupt:
                            print("\nOperation cancelled by user.")
                            raise
                        except Exception as e:
                            print(f"Error splitting {audio_file}: {e}")
                            continue
                    
                    print(f"Extracted {len(temp_extracted_files)} tracks to temporary directory.")

            # Find regular music files (excluding CUE audio files)
            regular_files = []
            cue_audio_files = {audio_file for _, audio_file in cue_pairs}
            
            scan_result = FileScanner.scan(
                source_path,
                file_patterns=Config.get_music_extensions(),
                ignored_dirs=Config.get_ignored_dirs(),
            )
            
            for file_path in scan_result["files"]:
                if file_path not in cue_audio_files:
                    regular_files.append(file_path)
            
            # Combine regular files with extracted files
            all_files = regular_files + temp_extracted_files

            if not all_files:
                if cue_pairs:
                    print(f"No individual music files found, but found {len(cue_pairs)} CUE pairs.")
                    print("Run again and choose 'y' to split the CUE files.")
                else:
                    print(f"No music files found in {source_path}")
                return

            processed_count = 0
            processed_files = []  # Track source files for deletion

            for file_path in all_files:
                try:
                    # For extracted files, filename already contains metadata
                    if file_path in temp_extracted_files:
                        new_filename = file_path.name
                    else:
                        # Extract metadata from tags for regular files
                        artist, album, track_num, title = self._extract_metadata(file_path)
                        new_filename = f"{artist} - {album} - {track_num} - {title}{file_path.suffix}"

                    # Copy file to target directory
                    target_file = target_path / new_filename

                    if target_file.exists():
                        print(f"Skipping existing file: {new_filename}")
                        continue

                    shutil.copy2(file_path, target_file)
                    
                    # Log the import
                    self._log_import(file_path, target_file)
                    
                    processed_count += 1
                    if file_path not in temp_extracted_files:
                        processed_files.append(file_path)
                    print(f"Copied: {new_filename}")

                except KeyboardInterrupt:
                    print("\nOperation cancelled by user.")
                    raise
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    continue

            print(f"Successfully imported {processed_count} tracks to {target_path}")
            
            # Ask user if they want to delete source files (including CUE files)
            if processed_files or cue_pairs:
                source_count = len(processed_files) + len(cue_pairs)
                print(f"\nImported from {source_count} source files.")
                response = input("Do you want to delete the source files? (y/N): ").strip().lower()
                
                if response in ['y', 'yes']:
                    deleted_count = 0
                    
                    # Delete regular files
                    for source_file in processed_files:
                        try:
                            source_file.unlink()
                            deleted_count += 1
                            print(f"Deleted: {source_file.name}")
                        except Exception as e:
                            print(f"Error deleting {source_file}: {e}")
                    
                    # Delete CUE files and their audio files
                    for cue_file, audio_file in cue_pairs:
                        try:
                            cue_file.unlink()
                            audio_file.unlink()
                            deleted_count += 2
                            print(f"Deleted: {cue_file.name} and {audio_file.name}")
                        except Exception as e:
                            print(f"Error deleting CUE pair: {e}")
                    
                    print(f"Deleted {deleted_count} source files.")
                else:
                    print("Source files kept.")
        
        finally:
            # Clean up temporary files
            if temp_extracted_files:
                for temp_file in temp_extracted_files:
                    try:
                        temp_file.unlink()
                    except:
                        pass
            if temp_dir:
                try:
                    temp_dir.rmdir()
                except:
                    pass

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
