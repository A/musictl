#!/usr/bin/env python3
import sys
from .controller import Controller


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: musictl <command>")
        print("Commands:")
        print("  select        - Browse and play music")
        print("  pick <dir>    - Move current track to directory")
        print("  delete        - Delete current track")
        return

    command = sys.argv[1]
    controller = Controller()

    if command == "select":
        controller.start()
    elif command == "pick":
        if len(sys.argv) < 3:
            print("Usage: musictl pick <directory>")
            return

        target_dir = sys.argv[2]
        controller.pick(target_dir)
    elif command == "delete":
        controller.delete()
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
