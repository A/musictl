#!/usr/bin/env python3
import sys
import signal
from .controller import Controller


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\nInterrupted by user. Cleaning up...")
    sys.exit(0)


def main():
    """Main entry point."""
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
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
    
    try:
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
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
