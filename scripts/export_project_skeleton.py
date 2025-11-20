#!/usr/bin/env python3
"""
Utility to export the reusable Spec Kit skeleton into a new directory.
The script copies all core automation files, SOP documents, templates,
and MCP tooling while creating clean service/test scaffolds with
placeholder directories.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Iterable, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]

CORE_FILES: Sequence[str] = (
    "Makefile",
    "pyproject.toml",
    "Dockerfile",
    "Dockerfile.slack",
    "cloudbuild.yaml",
    "cloudbuild.slack.yaml",
    "cloudbuild-slack.yaml",
    "cloudbuild.summary-web-service.yaml",
    "cloudbuild.transcription.yaml",
    ".markdownlint-cli2.jsonc",
    ".gitignore",
    ".dockerignore",
    "QUICK_START_FOR_AI.md",
    "DEVELOPMENT_GUIDELINES.md",
    "TOKEN_OPTIMIZATION_GUIDE.md",
    "memory/constitution.md",
)

DOC_FILES: Sequence[str] = (
    "docs/ai-collaboration-playbook.md",
    "docs/credential-management.md",
    "docs/subagent_alternatives.md",
    "docs/local-development.md",
    "docs/installation.md",
)

FULL_DIRECTORIES: Sequence[str] = (
    ".specify",
    ".devcontainer",
    "templates",
    "tools",
    "scripts",
)

SERVICE_SCAFFOLDS = {
    "analysis-service": {
        "files": ("Dockerfile", "cloudbuild.yaml", "requirements.txt"),
        "empty_dirs": ("src", "tests"),
    },
    "web-service": {
        "files": ("Dockerfile", "README.md", "requirements.txt"),
        "empty_dirs": ("src", "static", "templates", "tests"),
    },
}

TEST_SCAFFOLD = {
    "files": ("tests/conftest.py",),
    "empty_dirs": ("tests/unit",),
}


def copy_file(rel_path: str, dest_root: Path, missing: List[str]) -> None:
    src = REPO_ROOT / rel_path
    if not src.exists():
        missing.append(rel_path)
        return
    dest = dest_root / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def copy_directory(rel_path: str, dest_root: Path, missing: List[str]) -> None:
    src = REPO_ROOT / rel_path
    if not src.exists():
        missing.append(rel_path)
        return
    dest = dest_root / rel_path
    shutil.copytree(src, dest, dirs_exist_ok=True)


def ensure_empty_dirs(paths: Iterable[str], dest_root: Path) -> None:
    for path in paths:
        target = dest_root / path
        target.mkdir(parents=True, exist_ok=True)
        gitkeep = target / ".gitkeep"
        gitkeep.touch(exist_ok=True)


def scaffold_service(name: str, config: dict, dest_root: Path, missing: List[str]) -> None:
    base_path = Path(name)
    for file_name in config.get("files", ()):
        copy_file(str(base_path / file_name), dest_root, missing)
    ensure_empty_dirs((str(base_path / d) for d in config.get("empty_dirs", ())), dest_root)


def scaffold_tests(dest_root: Path, missing: List[str]) -> None:
    for file_name in TEST_SCAFFOLD["files"]:
        copy_file(file_name, dest_root, missing)
    ensure_empty_dirs(TEST_SCAFFOLD["empty_dirs"], dest_root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the Spec Kit skeleton to a destination directory.",
    )
    parser.add_argument(
        "destination",
        help="Path to the directory where the skeleton should be created.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow writing into an existing empty directory.",
    )
    return parser.parse_args()


def ensure_destination(path: Path, allow_existing: bool) -> None:
    if path.exists():
        if any(path.iterdir()):
            if not allow_existing:
                sys.exit(f"Destination '{path}' already exists and is not empty. Pass --overwrite to continue.")
        else:
            return
    else:
        path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()
    destination = Path(args.destination).expanduser().resolve()
    ensure_destination(destination, allow_existing=args.overwrite)

    missing: List[str] = []

    for rel_path in CORE_FILES:
        copy_file(rel_path, destination, missing)

    for rel_path in DOC_FILES:
        copy_file(rel_path, destination, missing)

    for directory in FULL_DIRECTORIES:
        copy_directory(directory, destination, missing)

    for name, config in SERVICE_SCAFFOLDS.items():
        scaffold_service(name, config, destination, missing)

    scaffold_tests(destination, missing)

    if missing:
        print("⚠️ The following paths were not found in the source repository and were skipped:")
        for rel_path in missing:
            print(f"   - {rel_path}")

    print(f"✅ Skeleton exported to: {destination}")
    print("Next steps:")
    print("  1. Update pyproject.toml metadata (name, version, description).")
    print("  2. Configure Docker image names and Cloud Build triggers.")
    print("  3. Re-run scripts/setup_mcp_infrastructure.sh if MCP servers are needed.")
    print("  4. Start implementing new business logic inside the empty service/test scaffolds.")


if __name__ == "__main__":
    main()
