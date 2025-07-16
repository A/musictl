#!/usr/bin/env python3
import sys
from .controller import Controller


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: musictl <command>")
        print("Commands:")
        print("  select          - Browse and play music")
        print("  search          - Search and play a specific track")
        print("  pick <dir>      - Move current track to directory")
        print("  delete          - Delete current track")
        print("  import <dir> <source> - Import tracks from source to target directory")
        return

    command = sys.argv[1]
    controller = Controller()

    if command == "select":
        controller.start()
    elif command == "search":
        controller.search()
    elif command == "pick":
        if len(sys.argv) < 3:
            print("Usage: musictl pick <directory>")
            return

        target_dir = sys.argv[2]
        controller.pick(target_dir)
    elif command == "delete":
        controller.delete()
    elif command == "import":
        if len(sys.argv) < 4:
            print("Usage: musictl import <target_dir/subdir> <source_dir>")
            print("Example: musictl import collection/indie_inbox ~/Downloads/Artist")
            return

        target_dir = sys.argv[2]
        source_dir = sys.argv[3]
        controller.import_tracks(target_dir, source_dir)
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
