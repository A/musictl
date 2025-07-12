#!/usr/bin/env python3
from pathlib import Path
from typing import List, Set, Union, Optional, Dict


class FileScanner:
    """Simple file scanner with pattern/extension matching."""

    @staticmethod
    def scan(
        directory: Union[str, Path],
        file_patterns: Optional[Union[str, List[str], Set[str]]] = None,
        dir_patterns: Optional[Union[str, List[str], Set[str]]] = None,
        recursive: bool = True,
        ignored_dirs: Optional[Set[str]] = None,
    ) -> Dict:
        """Scan directory and return structured result."""
        directory = Path(directory)
        if not directory.exists():
            return {"files": [], "files_total": 0, "dirs": [], "dirs_total": 0}

        if isinstance(file_patterns, str):
            file_patterns = [file_patterns]
        if isinstance(dir_patterns, str):
            dir_patterns = [dir_patterns]

        file_patterns = set(file_patterns or [])
        dir_patterns = set(dir_patterns or [])
        ignored_dirs = ignored_dirs or set()

        files = []
        dirs = []

        try:
            # For files - use recursive or not based on parameter
            if file_patterns:
                file_iterator = (
                    directory.rglob("*") if recursive else directory.iterdir()
                )
                for path in file_iterator:
                    if any(ignored in str(path) for ignored in ignored_dirs):
                        continue
                    if path.is_file() and FileScanner._matches(path, file_patterns):
                        files.append(path)

            # For dirs - always non-recursive (only immediate subdirs)
            for path in directory.iterdir():
                if any(ignored in str(path) for ignored in ignored_dirs):
                    continue
                if path.is_dir() and FileScanner._matches(path, dir_patterns):
                    dirs.append(path)

        except PermissionError:
            pass

        return {
            "files": files,
            "files_total": len(files),
            "dirs": sorted(dirs),
            "dirs_total": len(dirs),
        }

    @staticmethod
    def _matches(path: Path, patterns: Set[str]) -> bool:
        if not patterns:
            return True
        return any(
            path.name.endswith(p) if p.startswith(".") else path.match(p)
            for p in patterns
        )
