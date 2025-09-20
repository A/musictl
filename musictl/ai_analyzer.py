#!/usr/bin/env python3
import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from mutagen import File as MutagenFile
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from pydantic import BaseModel, Field
from .config import Config


class GenreAnalysisResult(BaseModel):
    """Schema for genre analysis result."""
    genres: List[str] = Field(description="List of matching genres", default_factory=list)


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
            self.agent = Agent(
                description="Music Genre Analysis Assistant",
                model=OpenAIChat(id="gpt-4o", temperature=0.1),
                tools=[
                    DuckDuckGoTools(cache_results=True, fixed_max_results=3),
                ],
                system_message=self._get_system_message(),
                instructions=self._get_instructions(),
                output_schema=GenreAnalysisResult,
                exponential_backoff=True,
                delay_between_retries=2,
                # debug_mode=True
            )
            self.logger.info("AI Agent initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize AI Agent: {e}")
            raise

    def _get_system_message(self) -> str:
        """Get the system message for the AI agent."""
        genres = self.config.get_analyze_genres()
        if not genres:
            return "No genres configured. Please add genres to the configuration first."
        
        genres_text = ""
        for genre in genres:
            title = genre.get("title", "")
            description = genre.get("description", "")
            if title:
                if description:
                    genres_text += f"- {title}: {description}\n"
                else:
                    genres_text += f"- {title}\n"
        genres_section = f"Available genres:\n{genres_text}"
        
        return f"""
You are an experienced musical journalist speaking both russian and english languages.
You need to analyze given track, and provide  a comprehensive and accurate list of musical
genres it matches with.

## Core Rules:

- ALWAYS use only available genres
- NEVER make up genres
- USE both english and russian languages for search. Especially if track information in russian.

## Web Search Rules:

1. Search for artist information and genres "[artist] [] genre"
2. Search for album genres "[artist] [album] genre"
3. Search for soundtrack "[artist] - [album] - [track] is a soundtrack for movie or a game?"

If it's clear after direct question about album genre, you can stop, and proceed to the response generation.

If not, try to search artist social networks:

1. Search for soundcloud "[artist] - [track] [country?] soundcloud"
2. Search for youtube "[artist] - [track] [country?] youtube"
3. Search for spotify "[artist] - [track] [country?] spotify"


## Genre Matching Rules:

1. You need to take track information as well as a list of user defined genres. Look into path, parent directory of a track
   might contain some hints.
2. Search for track genres in the web.
3. Select genres for the track from the list user provided
4. If multiple genres or a root genre and a sug-genre match with a track, return all of them
5. You need to return them as an array in resulting json response

## When No Genres Match a Track:

In this case return an empty list in response

## Genre Specific Rules:

- IMPORTANT: Ambient, Dark Ambient or other variations of this genres shouldn't be mixed with another genres, like
             a chillhop or pop. If there is any other genre matches along with ambient, remove ambient and its sub-genres
- IMPORTANT: Dark Orchestral can't be mixed with any other genre except Orchestral and Soundtrack.
             It stays for very dark sometimes horror orchestral music, like Elden Ring Soundtrack.
- IMPORTANT: Russian rap is very specific genre, that should aways be used along with rap root genre.
             Double check this genre and never attach it just if artist is just russian.
             NEVER translate artist name or track name.
- IMPORTANT: Soundtracks should always be explicitly and exclusively written for a movie or a game.
             If a track was released by an artist and then just used in the movie or a game, omit soundtrack genre.
             Examples: Witcher Soundtrack, Elden Ring Soundtrack, Hanz Zimmer Dune OST, etc.
- IMPORTANT: Synthwave is more broad, and includes nostalgic 80s vibe syth, dark synth and electronic music.
- IMPORTANT: Some genres just can't be mixed together, for example House and Chillhop or Orchestral and Rap.

## Language Specific Queries:

If a band is russian (you can detect it by cyrillic text in track info), translate query into russian:

INCORRECT: Пилар band information
CORRECT: Пилар информация о музыкальной группе

## List of User Genres

Below the list of user provided genres. Some of them may content additional information, like artist names, that
most likely may match with this genre, or some extra specific extends the genre definition.

```
{genres_section}
```

## Weird Genre Mixes to Avoid
- Indie, Russian Rap
- Indie, Dark Orchestral
- Russian Rap, House
- House, Chillhop

You must respond with a structured result containing the analysis results.
"""

    def _get_instructions(self) -> str:
        """Get instructions for the AI agent."""
        return """
Return the genres as a list. If no genres match, return an empty list.
"""

    def _get_prompt(self, track_path: Path, genres: List[dict]) -> str:
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
            # Extract first value from lists
            title = title[0] if isinstance(title, list) else str(title)
            artist = artist[0] if isinstance(artist, list) else str(artist)
            album = album[0] if isinstance(album, list) else str(album)
            
            prompt = f"""Track: {title}
Artist: {artist}
Album: {album}
File: {track_path.name}
Path: {track_path}"""
            
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
            # if 'Pilar' not in str(track_path):
            #     return 'SKIPPED'

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
            
            if not response or not hasattr(response, 'content'):
                print(f"  ✗ No response from AI for {track_path.name}")
                return ""
            
            # Get the structured result
            if hasattr(response, 'content') and isinstance(response.content, GenreAnalysisResult):
                suggested_genres = response.content.genres
            else:
                # Fallback to parsing JSON if needed
                try:
                    import json
                    response_data = json.loads(str(response.content))
                    suggested_genres = response_data.get("genres", [])
                except (json.JSONDecodeError, AttributeError) as e:
                    self.logger.warning(f"Failed to parse response for {track_path.name}: {e}")
                    print(f"  ✗ Invalid response format for {track_path.name}")
                    return ""
            
            if not suggested_genres:
                print(f"  ✗ No suitable genre found for {track_path.name}")
                return ""
            
            valid_genres = []
            
            # Create case-insensitive mapping
            if isinstance(genres[0], str):
                # Old format
                genres_lower = {g.lower(): g for g in genres}
            else:
                # New format - map titles
                genres_lower = {}
                for genre in genres:
                    title = genre.get("title", "")
                    if title:
                        genres_lower[title.lower()] = title
            
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
