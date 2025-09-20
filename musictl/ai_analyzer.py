#!/usr/bin/env python3
import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from mutagen import File as MutagenFile
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from .config import Config


class AIAnalyzer:
    """AI-powered music genre analyzer using Agno Agent."""

    def __init__(self):
        """Initialize the AI analyzer."""
        self.logger = logging.getLogger(__name__)
        self.config = Config()
        self.agent = None
        self._setup_agent()

    def _setup_agent(self):
        """Set up the Agno agent for music analysis."""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")

            self.agent = Agent(
                description="Music Genre Analysis Assistant",
                model=OpenAIChat(id="gpt-4o-mini", temperature=0.1),
                tools=[
                    DuckDuckGoTools(),
                ],
                system_message=self._get_system_message(),
                instructions=self._get_instructions(),
                exponential_backoff=True,
                delay_between_retries=2,
                debug_mode=False
            )
            self.logger.info("AI Agent initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize AI Agent: {e}")
            raise

    def _get_system_message(self) -> str:
        """Get the system message for the AI agent."""
        return """You are a music genre analysis expert. Your task is to analyze music tracks and determine their most appropriate genres from a given list of available genres.

CRITICAL: You must respond with ONLY the genre name(s) or empty string. No explanations, no analysis, no additional text.

Rules:
1. Analyze the track's metadata (title, artist, album, existing genre if any)
2. Use web search to gather information about the track if needed
3. Determine the most appropriate genres from the provided list
4. Return multiple genres separated by semicolon (;) if several genres fit well
5. Return only the genre name(s), or empty string if no suitable genre is found
6. Be conservative - if you're not confident, return empty string rather than guessing

Examples of correct responses:
- rock
- electronic;ambient
- jazz;blues
- (empty string if no suitable genre)

WRONG responses (do not do this):
- "Based on analysis, this track is indie"
- "The genre for this track is: rock"
- "indie; folk (alternative pop style)"

CORRECT response format:
- indie;folk
- rock
- (empty string)"""

    def _get_instructions(self) -> str:
        """Get instructions for the AI agent based on available genres."""
        genres = self.config.get_analyze_genres()
        if not genres:
            return "No genres configured. Please add genres to the configuration first."
        
        genres_list = ", ".join(genres)
        return f"""Available genres: {genres_list}

For each track, analyze its metadata and determine which genre from the list best fits the track. 
If the track doesn't clearly fit any of the available genres, return an empty string.
Focus on the musical style, not just the artist's typical genre."""

    def _get_prompt(self, track_path: Path, genres: List[str]) -> str:
        """Generate analysis prompt for a specific track."""
        try:
            audio_file = MutagenFile(str(track_path))
            if audio_file is None:
                return f"Track: {track_path.name} (unable to read metadata)"
            
            # Get tags - mutagen returns lists for most formats, use ID3 tags like in controller.py
            title = (
                audio_file.get("TIT2") or audio_file.get("TITLE") or [track_path.stem]
            )
            artist = (
                audio_file.get("TPE1") or audio_file.get("ARTIST") or ["Unknown Artist"]
            )
            album = (
                audio_file.get("TALB") or audio_file.get("ALBUM") or ["Unknown Album"]
            )
            existing_genre = (
                audio_file.get("TCON") or audio_file.get("GENRE") or [""]
            )
            
            # Extract first value from lists
            title = title[0] if isinstance(title, list) else str(title)
            artist = artist[0] if isinstance(artist, list) else str(artist)
            album = album[0] if isinstance(album, list) else str(album)
            existing_genre = existing_genre[0] if isinstance(existing_genre, list) else str(existing_genre)
            
            prompt = f"""Analyze this music track and determine its genre:

Track: {title}
Artist: {artist}
Album: {album}
Current genre: {existing_genre or 'None'}
File: {track_path.name}

Available genres: {', '.join(genres)}

Determine the most appropriate genre from the list above. If none fit well, return empty string."""
            
            return prompt
        except Exception as e:
            self.logger.error(f"Error reading track metadata for {track_path}: {e}")
            return f"Track: {track_path.name} (error reading metadata)"

    def _is_track_analyzed(self, track_path: Path) -> bool:
        """Check if track was already analyzed by looking for analysis marker in comment tag."""
        try:
            audio_file = MutagenFile(str(track_path))
            if audio_file is None:
                return False
            
            # Check for analysis marker in comment tag - try different tag names
            comment = ""
            for tag_name in ["COMM", "COMMENT", "COMM::eng", "COMM::XXX", "comment"]:
                tag_value = audio_file.get(tag_name)
                if tag_value:
                    if isinstance(tag_value, list):
                        comment = tag_value[0] if tag_value else ""
                    else:
                        comment = str(tag_value)
                    break
            
            # Look for our analysis marker
            analysis_marker = "musictl-ai-analyzed"
            is_analyzed = analysis_marker in comment.lower()
            
            return is_analyzed
            
        except Exception as e:
            self.logger.error(f"Error checking analysis status for {track_path}: {e}")
            return False

    def analyze_track(self, track_path: Path, force: bool = False) -> Optional[str]:
        """Analyze a single track and return the suggested genre."""
        try:
            # Check if track was already analyzed (unless force is True)
            if not force:
                if self._is_track_analyzed(track_path):
                    return "SKIPPED"
            
            genres = self.config.get_analyze_genres()
            if not genres:
                self.logger.warning("No genres configured for analysis")
                return None

            prompt = self._get_prompt(track_path, genres)
            # Don't log here to avoid duplicate messages
            
            response = self.agent.run(prompt)
            suggested_genres_str = response.content.strip() if hasattr(response, 'content') and response.content else ""
            
            if not suggested_genres_str:
                self.logger.info(f"✗ No suitable genre found for {track_path.name}")
                return ""
            
            # Clean up the response - extract only genre names
            # Remove common prefixes and suffixes that AI might add
            cleaned_response = suggested_genres_str
            prefixes_to_remove = [
                "Based on the analysis",
                "The genre for this track is:",
                "The most appropriate genre",
                "Given the available genres",
                "This track is characterized as",
                "The track falls under",
                "The music is described as"
            ]
            
            for prefix in prefixes_to_remove:
                if cleaned_response.lower().startswith(prefix.lower()):
                    # Find the last colon or newline and take everything after it
                    for sep in [':', '\n', '-']:
                        if sep in cleaned_response:
                            cleaned_response = cleaned_response.split(sep, 1)[1].strip()
                            break
                    break
            
            # Parse multiple genres separated by semicolon
            suggested_genres = [g.strip().strip('"\'') for g in cleaned_response.split(';') if g.strip()]
            valid_genres = []
            
            # Create case-insensitive mapping
            genres_lower = {g.lower(): g for g in genres}
            
            for genre in suggested_genres:
                genre_lower = genre.lower()
                if genre_lower in genres_lower:
                    # Use the original case from config
                    valid_genres.append(genres_lower[genre_lower])
                else:
                    self.logger.warning(f"⚠ Suggested genre '{genre}' not in configured list for {track_path.name}")
            
            if valid_genres:
                separator = self.config.get_analyze_separator()
                result = separator.join(valid_genres)
                print(f"  ✓ Found genres: {', '.join(valid_genres)}")
                return result
            else:
                print(f"  ✗ No valid genres found")
                return ""
                
        except Exception as e:
            self.logger.error(f"Error analyzing track {track_path}: {e}")
            return None

    def update_track_genre(self, track_path: Path, genre: str, add_analysis_marker: bool = True) -> bool:
        """Update the genre metadata of a track."""
        try:
            audio_file = MutagenFile(str(track_path))
            if audio_file is None:
                self.logger.error(f"Cannot read audio file: {track_path}")
                return False
            
            if genre:
                # Split genres by separator
                genre_list = [g.strip() for g in genre.split(self.config.get_analyze_separator()) if g.strip()]
                genre_string = self.config.get_analyze_separator().join(genre_list)
                
                # Try different approaches based on file type
                try:
                    # First try the simple approach
                    audio_file["GENRE"] = genre_string
                except Exception:
                    try:
                        # If that fails, try with list
                        audio_file["GENRE"] = [genre_string]
                    except Exception:
                        try:
                            # For ID3v2, try TCON
                            from mutagen.id3 import TCON
                            audio_file.tags["TCON"] = TCON(encoding=3, text=genre_string)
                        except Exception as e:
                            self.logger.error(f"Failed to set genre for {track_path}: {e}")
                            return False
                
                # Add analysis marker to comment if requested
                if add_analysis_marker:
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    analysis_marker = f"musictl-ai-analyzed {timestamp}"
                    
                    # Get existing comment and append marker
                    existing_comment = (
                        audio_file.get("COMM") or audio_file.get("COMMENT") or audio_file.get("COMM::XXX") or audio_file.get("comment") or [""]
                    )
                    existing_comment = existing_comment[0] if isinstance(existing_comment, list) else str(existing_comment)
                    
                    if existing_comment and "musictl-ai-analyzed" not in existing_comment.lower():
                        new_comment = f"{existing_comment} | {analysis_marker}"
                    else:
                        new_comment = analysis_marker
                    
                    # Always try to save to COMM::XXX first, then fallback to other tags
                    try:
                        from mutagen.id3 import COMM
                        audio_file.tags["COMM::XXX"] = COMM(encoding=3, text=new_comment)
                    except Exception as e1:
                        try:
                            audio_file["comment"] = new_comment
                        except Exception as e2:
                            try:
                                audio_file["COMMENT"] = new_comment
                            except Exception as e3:
                                try:
                                    audio_file["COMMENT"] = [new_comment]
                                except Exception as e4:
                                    try:
                                        from mutagen.id3 import COMM
                                        audio_file.tags["COMM::eng"] = COMM(encoding=3, text=new_comment)
                                    except Exception as e5:
                                        self.logger.warning(f"Failed to set comment for {track_path}: {e5}")
                
                audio_file.save()
                # Log with comma-separated genres for readability
                display_genres = genre.replace(self.config.get_analyze_separator(), ', ')
                self.logger.info(f"Updated genre for {track_path.name}: {display_genres}")
            else:
                # Remove genre if empty
                if "TCON" in audio_file:
                    del audio_file["TCON"]
                if "GENRE" in audio_file:
                    del audio_file["GENRE"]
                audio_file.save()
                self.logger.info(f"Removed genre from {track_path.name}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error updating track {track_path}: {e}")
            return False

    def analyze_directory(self, directory: Path, dry_run: bool = False, global_start: int = 0, total_tracks: int = 0, force: bool = False) -> Dict[str, Any]:
        """Analyze all music files in a directory."""
        results = {
            "processed": 0,
            "updated": 0,
            "errors": 0,
            "tracks": []
        }
        
        if not directory.exists():
            self.logger.error(f"Directory does not exist: {directory}")
            return results
        
        music_extensions = self.config.get_music_extensions()
        tracks = []
        
        for ext in music_extensions:
            tracks.extend(directory.rglob(f"*{ext}"))
        
        self.logger.info(f"Found {len(tracks)} music files in {directory}")
        
        for i, track_path in enumerate(tracks, 1):
            try:
                results["processed"] += 1
                global_track_num = global_start + i
                
                # Check if track is already analyzed before showing processing message
                is_already_analyzed = not force and self._is_track_analyzed(track_path)
                
                if is_already_analyzed:
                    if total_tracks > 0:
                        print(f"Skipped [{global_track_num}/{total_tracks}] ({i}/{len(tracks)} in {directory.name}): {track_path.name}")
                    else:
                        print(f"Skipped [{i}/{len(tracks)}]: {track_path.name}")
                else:
                    if total_tracks > 0:
                        print(f"Processing [{global_track_num}/{total_tracks}] ({i}/{len(tracks)} in {directory.name}): {track_path.name}")
                    else:
                        print(f"Processing [{i}/{len(tracks)}]: {track_path.name}")
                
                suggested_genre = self.analyze_track(track_path, force)
                
                track_info = {
                    "path": str(track_path),
                    "name": track_path.name,
                    "suggested_genre": suggested_genre,
                    "updated": False
                }
                
                # Log the result for dry run
                if dry_run and suggested_genre and suggested_genre != "SKIPPED":
                    # Display genres with comma separation for readability
                    display_genres = suggested_genre.replace(self.config.get_analyze_separator(), ', ')
                    print(f"  → {display_genres}")
                elif dry_run and suggested_genre == "SKIPPED":
                    print(f"  ⏭ (already analyzed)")
                elif dry_run:
                    print(f"  - (no suitable genre found)")
                
                if suggested_genre is not None and suggested_genre != "SKIPPED" and not dry_run:
                    if self.update_track_genre(track_path, suggested_genre):
                        track_info["updated"] = True
                        results["updated"] += 1
                
                results["tracks"].append(track_info)
                
            except Exception as e:
                self.logger.error(f"Error processing {track_path}: {e}")
                results["errors"] += 1
        
        return results

    def analyze_all_configured_dirs(self, dry_run: bool = False, force: bool = False) -> Dict[str, Any]:
        """Analyze all configured directories."""
        genres = self.config.get_analyze_genres()
        if not genres:
            self.logger.error("No genres configured. Please add genres to the configuration first.")
            return {"error": "No genres configured"}
        
        analyze_dirs = self.config.get_analyze_dirs()
        base_path = self.config.get_base_path()
        
        # First, count total tracks across all directories
        total_tracks = 0
        for dir_name in analyze_dirs:
            dir_path = base_path / dir_name
            if dir_path.exists():
                music_extensions = self.config.get_music_extensions()
                for ext in music_extensions:
                    total_tracks += len(list(dir_path.rglob(f"*{ext}")))
        
        total_results = {
            "processed": 0,
            "updated": 0,
            "errors": 0,
            "total_tracks": total_tracks,
            "directories": {}
        }
        
        processed_so_far = 0
        for dir_name in analyze_dirs:
            dir_path = base_path / dir_name
            self.logger.info(f"Analyzing directory: {dir_path}")
            
            dir_results = self.analyze_directory(dir_path, dry_run, processed_so_far, total_tracks, force)
            total_results["processed"] += dir_results["processed"]
            total_results["updated"] += dir_results["updated"]
            total_results["errors"] += dir_results["errors"]
            total_results["directories"][dir_name] = dir_results
            processed_so_far += dir_results["processed"]
        
        return total_results
