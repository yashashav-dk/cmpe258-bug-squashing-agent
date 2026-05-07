#!/usr/bin/env python3
"""
setup_workspaces.py — Clone and pin OSS repos used by the benchmark.

Usage:
    python scripts/setup_workspaces.py --all
    python scripts/setup_workspaces.py --repo click
    python scripts/setup_workspaces.py --repo requests
"""
import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_DIR = REPO_ROOT / "external"

REPOS = {
    "click": {
        "url": "https://github.com/pallets/click",
        "commit": "052c006033729bbb422cbdad0c4fee988ecb5aa5",
        "install": ["pip", "install", "-e", ".", "pytest"],
    },
    "requests": {
        "url": "https://github.com/psf/requests",
        "commit": "111d2b77",
        "install": ["pip", "install", "-e", ".", "pytest", "requests-mock"],
    },
}


def run(cmd: list, cwd: Path = None) -> int:
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def setup_repo(name: str, cfg: dict) -> bool:
    dest = EXTERNAL_DIR / name
    if (dest / ".git").exists():
        print(f"[{name}] already cloned at {dest}, skipping clone.")
    else:
        print(f"[{name}] Cloning {cfg['url']} -> {dest}")
        rc = run(["git", "clone", cfg["url"], str(dest)])
        if rc != 0:
            print(f"[{name}] Clone failed (exit {rc})")
            return False

    print(f"[{name}] Checking out {cfg['commit']}")
    rc = run(["git", "-C", str(dest), "checkout", cfg["commit"]])
    if rc != 0:
        print(f"[{name}] Checkout failed (exit {rc})")
        return False

    print(f"[{name}] Installing dependencies")
    rc = run([sys.executable, "-m"] + cfg["install"], cwd=dest)
    if rc != 0:
        print(f"[{name}] Install failed (exit {rc})")
        return False

    print(f"[{name}] Done.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Clone and pin OSS benchmark workspaces")
    parser.add_argument("--repo", action="append", choices=list(REPOS), help="Specific repo(s) to set up")
    parser.add_argument("--all", action="store_true", help="Set up all repos")
    args = parser.parse_args()

    if not args.all and not args.repo:
        parser.print_help()
        sys.exit(1)

    targets = list(REPOS) if args.all else args.repo
    failures = []
    for name in targets:
        ok = setup_repo(name, REPOS[name])
        if not ok:
            failures.append(name)

    if failures:
        print(f"\nFailed: {', '.join(failures)}")
        sys.exit(1)
    print(f"\nAll {len(targets)} workspace(s) ready.")


if __name__ == "__main__":
    main()
