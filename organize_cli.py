from __future__ import annotations
import argparse
import time
from pathlib import Path

from file_organizer import OrganizerConfig, organize_folder


def parse_args():
    parser = argparse.ArgumentParser(
        description="Organize files into subfolders by type (configurable via JSON)."
    )
    parser.add_argument(
        "folder",
        help="Path to the folder you want to organize.",
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to JSON config file (default: config.json)",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do NOT search in subfolders.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen, but do not move any files.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="Run repeatedly every N minutes (0 = run once).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    folder = Path(args.folder).expanduser().resolve()
    config_path = Path(args.config).expanduser().resolve()

    config = OrganizerConfig.from_json(config_path)

    recursive = not args.no_recursive
    dry_run = args.dry_run
    interval_min = args.interval

    if interval_min <= 0:
        # Single run
        organize_folder(folder, config, recursive=recursive, dry_run=dry_run, verbose=True)
    else:
        # Repeated runs
        interval_sec = interval_min * 60
        print(f"Auto mode: organizing '{folder}' every {interval_min} minute(s).")
        print("Press Ctrl+C to stop.\n")

        try:
            while True:
                print("\n=== Run started ===")
                organize_folder(folder, config, recursive=recursive, dry_run=dry_run, verbose=True)
                print(f"Sleeping for {interval_min} minute(s)...")
                time.sleep(interval_sec)
        except KeyboardInterrupt:
            print("\nStopped by user.")


if __name__ == "__main__":
    main()
