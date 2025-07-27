import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional


class CueTrack:
    """Represents a track from CUE file."""
    
    def __init__(self, number: int, title: str, performer: str, start_time: str, end_time: Optional[str] = None, album: str = ""):
        self.number = number
        self.title = title
        self.performer = performer
        self.start_time = start_time
        self.end_time = end_time
        self.album = album
    
    def __str__(self):
        return f"{self.performer} - {self.album} - {self.number:02d}. {self.title}"


class CueSplitter:
    """Handles CUE file parsing and audio splitting."""
    
    def __init__(self):
        pass
    
    def find_cue_files(self, directory: Path) -> List[Tuple[Path, Path]]:
        """Find CUE files with corresponding audio files."""
        cue_pairs = []
        
        for cue_file in directory.glob("*.cue"):
            # Look for corresponding audio file
            base_name = cue_file.stem
            audio_file = None
            
            # Try exact match first
            for ext in ['.flac', '.wav', '.ape']:
                potential_audio = directory / f"{base_name}{ext}"
                if potential_audio.exists():
                    audio_file = potential_audio
                    break
            
            # If no exact match, look for any audio file in the same directory
            if not audio_file:
                for ext in ['.flac', '.wav', '.ape']:
                    audio_files = list(directory.glob(f"*{ext}"))
                    if audio_files:
                        # Take the first one (there's usually only one album file)
                        audio_file = audio_files[0]
                        break
            
            if audio_file:
                cue_pairs.append((cue_file, audio_file))
        
        return cue_pairs
    
    def parse_cue(self, cue_file: Path) -> Tuple[str, str, List[CueTrack]]:
        """Parse CUE file and extract track information."""
        content = None
        
        # Try different encodings
        for encoding in ['utf-8', 'cp1251', 'latin1']:
            try:
                with open(cue_file, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        
        if not content:
            raise ValueError(f"Could not read CUE file with any encoding: {cue_file}")
        
        # Extract album info (first TITLE and PERFORMER before any TRACK)
        lines = content.split('\n')
        album = "Unknown Album"
        artist = "Unknown Artist"
        
        for line in lines:
            line = line.strip()
            if line.startswith('TRACK '):
                break  # Stop at first track
            if line.startswith('TITLE ') and album == "Unknown Album":
                album = line[6:].strip('"')
            elif line.startswith('PERFORMER ') and artist == "Unknown Artist":
                artist = line[10:].strip('"')
        
        # Extract tracks
        tracks = []
        current_track = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('TRACK '):
                # Save previous track if exists
                if current_track:
                    tracks.append(current_track)
                
                # Start new track
                track_parts = line.split()
                track_num = int(track_parts[1])
                current_track = {
                    'number': track_num,
                    'title': f'Track {track_num}',
                    'performer': artist,
                    'start_time': '00:00:00'
                }
            
            elif current_track and line.startswith('TITLE '):
                current_track['title'] = line[6:].strip('"')
            
            elif current_track and line.startswith('PERFORMER '):
                current_track['performer'] = line[10:].strip('"')
            
            elif current_track and line.startswith('INDEX 01 '):
                current_track['start_time'] = line[9:].strip()
        
        # Add last track
        if current_track:
            tracks.append(current_track)
        
        # Convert to CueTrack objects
        cue_tracks = []
        for i, track_data in enumerate(tracks):
            end_time = None
            if i + 1 < len(tracks):
                end_time = tracks[i + 1]['start_time']
            
            cue_track = CueTrack(
                track_data['number'],
                track_data['title'],
                track_data['performer'],
                track_data['start_time'],
                end_time,
                album
            )
            cue_tracks.append(cue_track)
        
        return artist, album, cue_tracks
    
    def split_audio(self, audio_file: Path, tracks: List[CueTrack], output_dir: Path) -> List[Path]:
        """Split audio file based on CUE tracks using ffmpeg."""
        if not self._check_ffmpeg():
            raise RuntimeError("ffmpeg not found. Please install ffmpeg to split CUE files.")
        
        split_files = []
        
        for track in tracks:
            output_file = output_dir / f"{track.number:02d} - {self._sanitize_filename(track.title)}{audio_file.suffix}"
            
            cmd = [
                'ffmpeg', '-i', str(audio_file),
                '-ss', self._convert_time(track.start_time),
                '-c:a', 'flac', '-avoid_negative_ts', 'make_zero'
            ]
            
            if track.end_time:
                cmd.extend(['-to', self._convert_time(track.end_time)])
            
            # Add only our metadata (no original metadata copied)
            cmd.extend([
                '-metadata', f'title={track.title}',
                '-metadata', f'artist={track.performer}',
                '-metadata', f'album={track.album}',
                '-metadata', f'track={track.number}'
            ])
            
            cmd.append(str(output_file))
            
            try:
                subprocess.run(cmd, capture_output=True, check=True)
                split_files.append(output_file)
                print(f"Split: {output_file.name}")
            except subprocess.CalledProcessError as e:
                print(f"Error splitting track {track.number}: {e}")
                continue
        
        return split_files
    
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available."""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _convert_time(self, cue_time: str) -> str:
        """Convert CUE time format (MM:SS:FF) to ffmpeg format (HH:MM:SS.mmm)."""
        parts = cue_time.split(':')
        if len(parts) == 3:
            minutes, seconds, frames = map(int, parts)
            # Convert frames to milliseconds (75 frames per second for CD)
            milliseconds = int((frames / 75) * 1000)
            total_seconds = minutes * 60 + seconds
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
        return cue_time
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility."""
        # Replace problematic characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip()
        return filename
