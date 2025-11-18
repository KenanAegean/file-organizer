from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from collections import Counter
import json
import shutil
from typing import Dict, List


# ---------- Config & data ----------

@dataclass
class OrganizerConfig:
    extension_index: Dict[str, str]
    ignore_hidden_files: bool = True
    ignore_hidden_folders: bool = True

    @classmethod
    def from_json(cls, path: Path) -> "OrganizerConfig":
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        categories = raw.get("categories", {})
        options = raw.get("options", {})

        ext_index: Dict[str, str] = {}
        for category, exts in categories.items():
            for ext in exts:
                ext_index[ext.lower()] = category

        return cls(
            extension_index=ext_index,
            ignore_hidden_files=options.get("ignore_hidden_files", True),
            ignore_hidden_folders=options.get("ignore_hidden_folders", True),
        )


@dataclass
class OrganizeResult:
    moved: Counter
    skipped_unmapped: int
    skipped_other: int


# ---------- Helpers ----------

def _is_hidden(path: Path) -> bool:
    return path.name.startswith(".")


def generate_unique_path(target: Path) -> Path:
    """
    If target exists, create 'name (1).ext', 'name (2).ext', ...
    """
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    parent = target.parent
    counter = 1

    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


# ---------- Main logic ----------

def organize_folder(
    folder: Path,
    config: OrganizerConfig,
    recursive: bool = True,
    dry_run: bool = False,
    verbose: bool = True,
) -> OrganizeResult:
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Folder does not exist or is not a directory: {folder}")

    moved_counter: Counter = Counter()
    skipped_unmapped = 0
    skipped_other = 0

    if verbose:
        print(f"\nOrganizing folder: {folder}")
        print(f"Recursive: {recursive} | Dry-run: {dry_run}")
        print("-" * 60)

    iterator = folder.rglob("*") if recursive else folder.iterdir()

    for item in iterator:
        try:
            # Skip directories
            if item.is_dir():
                if config.ignore_hidden_folders and _is_hidden(item):
                    continue
                continue

            # Hidden file?
            if config.ignore_hidden_files and _is_hidden(item):
                skipped_other += 1
                continue

            ext = item.suffix.lower()
            category = config.extension_index.get(ext)

            if not category:
                skipped_unmapped += 1
                continue

            target_dir = folder / category

            # Already in correct folder
            if item.parent == target_dir:
                continue

            if not dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)

            dest = target_dir / item.name
            dest = generate_unique_path(dest)

            if dry_run:
                if verbose:
                    print(f"[DRY-RUN] {item.relative_to(folder)} -> {dest.relative_to(folder)}")
            else:
                shutil.move(str(item), str(dest))
                if verbose:
                    print(f"Moved: {item.relative_to(folder)} -> {dest.relative_to(folder)}")

            moved_counter[category] += 1

        except Exception as exc:  # Safety net
            skipped_other += 1
            if verbose:
                print(f"Skipping '{item}': {exc}")

    if verbose:
        print("\nSummary")
        print("-" * 60)
        for category, count in moved_counter.items():
            print(f"{category:15}: {count} file(s)")
        print(f"Unmapped       : {skipped_unmapped} file(s)")
        print(f"Other skipped  : {skipped_other} file(s)")
        print("-" * 60)

    return OrganizeResult(
        moved=moved_counter,
        skipped_unmapped=skipped_unmapped,
        skipped_other=skipped_other,
    )
