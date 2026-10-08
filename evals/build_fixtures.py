#!/usr/bin/env python3
"""Pack and unpack the eval fixture repositories.

Fixture repositories are stored inside evals/fixtures.json instead of as real
files, because real project manifests (package.json, pom.xml, ...) inside an
installed skill would become false stack signals for the host project.

    python evals/build_fixtures.py unpack OUT_DIR [--only 1 4 ...]
        Writes each fixture to OUT_DIR/<NN-name>/ as a git repository with one
        commit on 'main'. Fixtures with a pull request get a 'pr' branch
        holding the PR changes (checked out), so `git diff main...pr` shows it.

    python evals/build_fixtures.py pack SRC_DIR
        Maintainers: rebuilds fixtures.json from SRC_DIR/<NN-name>/ directories
        (a directory containing base/ and pr/ is stored as a PR fixture).

Standard library and git only.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures.json")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "target", "bin", "obj", "dist", "build"}
MAX_FILE_BYTES = 200_000  # fixtures are small source files; anything larger is a mistake


def read_tree(root):
    files = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for f in sorted(filenames):
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if os.path.getsize(path) > MAX_FILE_BYTES:
                raise SystemExit("refusing to pack large file: {}".format(rel))
            try:
                with open(path, encoding="utf-8") as fh:
                    files[rel] = fh.read().replace("\r\n", "\n")
            except UnicodeDecodeError:
                raise SystemExit("refusing to pack non-UTF-8 file: {}".format(rel))
    return files


def pack(src):
    fixtures = {}
    for name in sorted(os.listdir(src)):
        full = os.path.join(src, name)
        if not os.path.isdir(full) or not name[:2].isdigit():
            continue
        if os.path.isdir(os.path.join(full, "base")) and os.path.isdir(os.path.join(full, "pr")):
            fixtures[name] = {"base": read_tree(os.path.join(full, "base")),
                              "pr": read_tree(os.path.join(full, "pr"))}
        else:
            fixtures[name] = {"base": read_tree(full)}
    with open(FIXTURES, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"fixtures": fixtures}, fh, indent=1, sort_keys=True)
        fh.write("\n")
    total = sum(len(f["base"]) + len(f.get("pr", {})) for f in fixtures.values())
    print("packed {} fixtures ({} files) into {}".format(len(fixtures), total, FIXTURES))


def write_files(root, files):
    for rel, content in files.items():
        path = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)


def git(root, *args):
    result = subprocess.run(["git", "-c", "user.name=eval", "-c", "user.email=eval@example.invalid",
                             "-c", "core.autocrlf=false", "-c", "core.longpaths=true", *args], cwd=root,
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit("git {} failed in {}:\n{}".format(" ".join(args), root, result.stderr.strip()))


def unpack(out, only):
    with open(FIXTURES, encoding="utf-8") as fh:
        fixtures = json.load(fh)["fixtures"]
    os.makedirs(out, exist_ok=True)
    for name, fx in sorted(fixtures.items()):
        if only and int(name[:2]) not in only:
            continue
        root = os.path.join(out, name)
        if os.path.exists(root):
            raise SystemExit("{} already exists; choose an empty OUT_DIR".format(root))
        os.makedirs(root)
        write_files(root, fx["base"])
        git(root, "init", "-q", "-b", "main")
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "Initial state")
        if fx.get("pr"):
            git(root, "checkout", "-q", "-b", "pr")
            write_files(root, fx["pr"])
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "Pull request under review")
        print(root)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    up = sub.add_parser("unpack")
    up.add_argument("out")
    up.add_argument("--only", type=int, nargs="*", default=[])
    pk = sub.add_parser("pack")
    pk.add_argument("src")
    args = ap.parse_args(argv)
    if args.cmd == "pack":
        pack(args.src)
    else:
        unpack(args.out, set(args.only))
    return 0


if __name__ == "__main__":
    sys.exit(main())
