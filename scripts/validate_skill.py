#!/usr/bin/env python3
"""Maintainer check for this skill's structure (not used by agents at runtime).

Validates SKILL.md frontmatter against the Agent Skills specification, link
integrity, orphaned reference files, reference-file tables of contents, the
eval files, and repository hygiene (no secrets, no project manifests that
would become false stack signals once the skill is installed inside a project).

Usage:
    python scripts/validate_skill.py [SKILL_DIR]

Exits 1 if any error is found. Standard library only.
"""
from __future__ import annotations

import json
import os
import re
import sys

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ALLOWED_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
RESERVED_WORDS = ("anthropic", "claude")
MAX_BODY_LINES = 500          # spec recommendation for SKILL.md
MAX_BODY_TOKENS = 5000        # spec recommendation, estimated below
TOC_THRESHOLD = 100           # reference files longer than this need "## Contents"
REFERENCE_DIRS = ("references", "languages", "frameworks")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
# Files that would look like project manifests to a host repository's stack detection.
FORBIDDEN_MANIFESTS = {
    "package.json", "pom.xml", "build.gradle", "build.gradle.kts", "pyproject.toml",
    "requirements.txt", "go.mod", "Cargo.toml", "composer.json", "Gemfile",
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock", "uv.lock",
}
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{32,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"),
]
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

errors, warnings = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    block = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")
    fields, current = {}, None
    for line in block.splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and current:
            sub = line.strip()
            if ":" in sub:
                k, v = sub.split(":", 1)
                if not isinstance(fields[current], dict):
                    fields[current] = {}
                fields[current][k.strip()] = v.strip().strip('"\'')
            continue
        if ":" not in line:
            err("frontmatter: cannot parse line: {!r}".format(line))
            continue
        k, v = line.split(":", 1)
        current = k.strip()
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        fields[current] = v if v else {}
    return fields, body


def check_frontmatter(skill_dir, fields):
    if fields is None:
        err("SKILL.md: missing YAML frontmatter delimited by ---")
        return
    for key in fields:
        if key not in ALLOWED_FIELDS:
            warn("frontmatter: '{}' is not an Agent Skills spec field (host-specific?)".format(key))
    name = fields.get("name")
    if not isinstance(name, str) or not name:
        err("frontmatter: 'name' is required")
    else:
        if len(name) > 64:
            err("frontmatter: name longer than 64 characters")
        if not NAME_RE.match(name):
            err("frontmatter: name must be lowercase letters/digits/single hyphens, no leading/trailing hyphen")
        if any(w in name for w in RESERVED_WORDS):
            err("frontmatter: name must not contain reserved words {}".format(RESERVED_WORDS))
        dirname = os.path.basename(os.path.abspath(skill_dir))
        if name != dirname:
            err("frontmatter: name '{}' must match directory name '{}'".format(name, dirname))
    desc = fields.get("description")
    if not isinstance(desc, str) or not desc.strip():
        err("frontmatter: 'description' is required")
    else:
        if len(desc) > 1024:
            err("frontmatter: description is {} chars (max 1024)".format(len(desc)))
        if re.search(r"<[^>]+>", desc):
            err("frontmatter: description must not contain XML tags")
        if not re.search(r"\bUse (when|for)\b", desc):
            warn("frontmatter: description should say when to use the skill ('Use when ...')")
        if re.match(r"\s*(I|You)\b", desc):
            warn("frontmatter: description should be written in third person")
    comp = fields.get("compatibility")
    if isinstance(comp, str) and len(comp) > 500:
        err("frontmatter: compatibility exceeds 500 characters")
    meta = fields.get("metadata")
    if meta is not None and not isinstance(meta, dict):
        err("frontmatter: metadata must be a mapping")


def check_links(path, text, root):
    targets = []
    for link in LINK_RE.findall(text):
        if re.match(r"^[a-z]+:", link) or link.startswith("#"):
            continue
        if "\\" in link:
            err("{}: Windows-style path in link {!r}".format(os.path.relpath(path, root), link))
        target = os.path.normpath(os.path.join(os.path.dirname(path), link.split("#")[0]))
        if not os.path.exists(target):
            err("{}: broken link {!r}".format(os.path.relpath(path, root), link))
        targets.append(target)
    return targets


def check_skill_md(skill_dir):
    path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(path):
        err("SKILL.md not found")
        return set()
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    fields, body = parse_frontmatter(text)
    check_frontmatter(skill_dir, fields)
    lines = body.count("\n") + 1
    if lines > MAX_BODY_LINES:
        err("SKILL.md body has {} lines (max {})".format(lines, MAX_BODY_LINES))
    est_tokens = int(len(re.findall(r"\S+", body)) * 1.4)
    if est_tokens > MAX_BODY_TOKENS:
        warn("SKILL.md body is ~{} tokens (recommended < {})".format(est_tokens, MAX_BODY_TOKENS))
    print("SKILL.md: {} body lines, ~{} tokens (estimate)".format(lines, est_tokens))
    return set(check_links(path, text, skill_dir))


def check_references(skill_dir, linked):
    for d in REFERENCE_DIRS:
        full = os.path.join(skill_dir, d)
        if not os.path.isdir(full):
            continue
        for f in sorted(os.listdir(full)):
            if not f.endswith(".md"):
                continue
            path = os.path.normpath(os.path.join(full, f))
            rel = os.path.relpath(path, skill_dir).replace(os.sep, "/")
            if path not in linked:
                err("{} is not linked from SKILL.md (orphaned reference)".format(rel))
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            if not text.lstrip().startswith("# "):
                warn("{}: should start with a level-1 heading".format(rel))
            if text.count("\n") > TOC_THRESHOLD and "## Contents" not in text:
                err("{}: longer than {} lines without a '## Contents' section".format(rel, TOC_THRESHOLD))
            check_links(path, text, skill_dir)


def check_evals(skill_dir, skill_name):
    path = os.path.join(skill_dir, "evals", "evals.json")
    if not os.path.isfile(path):
        err("evals/evals.json not found")
        return
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError as e:
        err("evals/evals.json: invalid JSON ({})".format(e))
        return
    if data.get("skill_name") != skill_name:
        err("evals/evals.json: skill_name must be '{}'".format(skill_name))
    evals = data.get("evals")
    if not isinstance(evals, list) or len(evals) < 3:
        err("evals/evals.json: needs an 'evals' list with at least 3 cases")
        return
    ids = set()
    for i, case in enumerate(evals):
        label = "evals[{}]".format(i)
        cid = case.get("id")
        if not isinstance(cid, int) or cid in ids:
            err("{}: 'id' must be a unique integer".format(label))
        ids.add(cid)
        for key in ("name", "scenario", "prompt", "expected_output"):
            if not isinstance(case.get(key), str) or not case[key].strip():
                err("{}: '{}' must be a non-empty string".format(label, key))
        for key in ("expectations", "failure_conditions", "categories"):
            if not isinstance(case.get(key), list) or not case[key]:
                err("{}: '{}' must be a non-empty list".format(label, key))
        if not isinstance(case.get("repository"), dict):
            err("{}: 'repository' must be an object".format(label))
        for f in case.get("files", []):
            if not os.path.exists(os.path.join(skill_dir, f)):
                err("{}: file {!r} does not exist".format(label, f))
    print("evals/evals.json: {} cases".format(len(evals)))

    tpath = os.path.join(skill_dir, "evals", "trigger-evals.json")
    if os.path.isfile(tpath):
        try:
            with open(tpath, encoding="utf-8") as fh:
                trig = json.load(fh)
        except ValueError as e:
            err("evals/trigger-evals.json: invalid JSON ({})".format(e))
            return
        pos = sum(1 for t in trig if t.get("should_trigger") is True)
        neg = sum(1 for t in trig if t.get("should_trigger") is False)
        if pos + neg != len(trig) or any(not t.get("query") for t in trig):
            err("evals/trigger-evals.json: each entry needs 'query' and boolean 'should_trigger'")
        print("evals/trigger-evals.json: {} should-trigger, {} should-not".format(pos, neg))


def check_hygiene(skill_dir):
    for dirpath, dirnames, filenames in os.walk(skill_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, skill_dir).replace(os.sep, "/")
            if f in FORBIDDEN_MANIFESTS or f.endswith((".csproj", ".sln")):
                err("{}: project manifests inside the skill become false stack signals when installed".format(rel))
            if f == ".env" or (f.startswith(".env.") and not f.endswith(".example")):
                err("{}: environment files must not be committed".format(rel))
            if f.endswith((".md", ".py", ".json", ".txt", ".yml", ".yaml")):
                try:
                    with open(path, encoding="utf-8") as fh:
                        text = fh.read()
                except UnicodeDecodeError:
                    err("{}: not valid UTF-8".format(rel))
                    continue
                if f != os.path.basename(__file__):
                    for rx in SECRET_PATTERNS:
                        if rx.search(text):
                            err("{}: matches secret pattern {}".format(rel, rx.pattern))


def main(argv):
    skill_dir = os.path.abspath(argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(__file__), ".."))
    linked = check_skill_md(skill_dir)
    check_references(skill_dir, linked)
    check_evals(skill_dir, os.path.basename(skill_dir))
    check_hygiene(skill_dir)
    for w in warnings:
        print("WARN  " + w)
    for e in errors:
        print("ERROR " + e)
    print("\n{} error(s), {} warning(s)".format(len(errors), len(warnings)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
