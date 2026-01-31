#!/usr/bin/env python3
"""
push.py — portable Git push script for the repo it lives in.

What it does:
  1) Finds repo root (via .git)
  2) Ensures remote 'origin' is set to the target repo
  3) Detects remote default branch (main/master/etc.)
  4) Adds all changes, commits if needed
  5) Pushes to origin default branch (no force)

Run:
  python push.py
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


TARGET_OWNER = "ronandownes"
TARGET_REPO = "am"

# Choose ONE:
# HTTPS (works with Git Credential Manager on Windows)
TARGET_ORIGIN = f"https://github.com/{TARGET_OWNER}/{TARGET_REPO}.git"
# SSH (uncomment to use SSH instead)
# TARGET_ORIGIN = f"git@github.com:{TARGET_OWNER}/{TARGET_REPO}.git"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print(f"→ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)


def capture(cmd: list[str]) -> str:
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", errors="replace")
    return out.strip()


def find_repo_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / ".git").exists():
            return p
    raise RuntimeError("Could not find repo root (.git not found). Put push.py in the repo root.")


def ensure_origin(target_url: str) -> None:
    try:
        current = capture(["git", "remote", "get-url", "origin"])
        if current != target_url:
            print(f"! origin is set to:\n  {current}\n! changing to:\n  {target_url}")
            run(["git", "remote", "set-url", "origin", target_url])
        else:
            print(f"✓ origin already set to {target_url}")
    except subprocess.CalledProcessError:
        print(f"! origin not found. Adding origin -> {target_url}")
        run(["git", "remote", "add", "origin", target_url])


def detect_remote_default_branch() -> str:
    """
    Prefer: symbolic-ref refs/remotes/origin/HEAD -> refs/remotes/origin/<branch>
    Fallback: main, then master, then current branch.
    """
    run(["git", "fetch", "origin", "--prune"], check=False)

    try:
        ref = capture(["git", "symbolic-ref", "refs/remotes/origin/HEAD"])
        return ref.rsplit("/", 1)[-1]
    except subprocess.CalledProcessError:
        branches = capture(["git", "branch", "-r"])
        if "origin/main" in branches:
            return "main"
        if "origin/master" in branches:
            return "master"
        current = capture(["git", "branch", "--show-current"])
        return current or "main"


def ensure_local_branch(branch: str) -> None:
    current = capture(["git", "branch", "--show-current"])
    if current == branch:
        return

    locals_ = capture(["git", "branch", "--list", branch])
    if locals_.strip():
        run(["git", "checkout", branch])
        return

    remotes = capture(["git", "branch", "-r"])
    if f"origin/{branch}" in remotes:
        run(["git", "checkout", "-b", branch, f"origin/{branch}"])
    else:
        run(["git", "checkout", "-b", branch])


def commit_if_needed(message: str) -> None:
    run(["git", "add", "."])
    status = capture(["git", "status", "--porcelain"])
    if not status.strip():
        print("✓ No changes to commit")
        return
    run(["git", "commit", "-m", message], check=True)


def push(branch: str) -> None:
    run(["git", "push", "-u", "origin", branch], check=True)


def main() -> int:
    repo_root = find_repo_root(Path(__file__).resolve().parent)
    os.chdir(repo_root)
    print(f"Repo root: {repo_root}")

    ensure_origin(TARGET_ORIGIN)

    default_branch = detect_remote_default_branch()
    print(f"Remote default branch: {default_branch}")

    ensure_local_branch(default_branch)

    commit_if_needed("sync applied-maths")
    push(default_branch)

    print("✓ Done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
