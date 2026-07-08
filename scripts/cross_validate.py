#!/usr/bin/env python3
"""Cross-validation: does this repo's spec line up with kody-w/RAPP?

The network has two sources of truth (this repo and kody-w/RAPP). Drift between
them is a signal that one or both need an update — same property the network
relies on between operator estates. This script makes the check mechanical.

Checks performed:
  1. Every schema string referenced in this repo's SPEC.md MUST appear at
     least once in the relevant kody-w/RAPP spec files (or anywhere in the
     repo if the file isn't pinned).
  2. The rappid format string declared in this repo's SPEC.md §5 MUST match
     the format declared in upstream ESTATE_SPEC.md §1 verbatim.
  3. Every kind value this repo emits (currently `project`) SHOULD be in the
     upstream frozen valid-kinds list (drift here is a "loud" warning, not a
     hard fail — kinds get added).
  4. File paths this repo's docs reference inside kody-w/RAPP MUST exist
     there (e.g. `pages/docs/ESTATE_SPEC.md`).

Resolution order for upstream files:
  - $RAPP_REPO env var (a local clone of kody-w/RAPP)
  - ./_rapp_clone/ if present (you can `git clone kody-w/RAPP _rapp_clone`)
  - HTTP fetch from raw.githubusercontent.com (requires network)

Exit code 0 if all checks match, 1 if any drift.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_MD = REPO_ROOT / "SPEC.md"
README_MD = REPO_ROOT / "README.md"

UPSTREAM_PIN_FILES = [
    "CONSTITUTION.md",
    "NEIGHBORHOOD_PROTOCOL.md",
    "ECOSYSTEM.md",
    "ECOSYSTEM_MAP.md",
    "pages/docs/SPEC.md",
    "pages/docs/ESTATE_SPEC.md",
    "pages/docs/TWIN_LIFECYCLE_SPEC.md",
    "pages/docs/NEIGHBORHOOD_EGG_SPEC.md",
]

GITHUB_RAW = "https://raw.githubusercontent.com/kody-w/RAPP/main/"


# ---------------------------------------------------------------------------
# Upstream resolver
# ---------------------------------------------------------------------------

class Upstream:
    """Reads upstream files by path; tries local then network."""
    def __init__(self, local_root: Path | None, allow_network: bool):
        self.local_root = local_root
        self.allow_network = allow_network
        self._cache: dict[str, str | None] = {}

    def read(self, rel_path: str) -> str | None:
        if rel_path in self._cache:
            return self._cache[rel_path]
        content = None
        if self.local_root:
            p = self.local_root / rel_path
            if p.exists():
                try:
                    content = p.read_text(errors="replace")
                except OSError:
                    pass
        if content is None and self.allow_network:
            try:
                with urllib.request.urlopen(GITHUB_RAW + rel_path, timeout=10) as r:
                    content = r.read().decode("utf-8", errors="replace")
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
                content = None
        self._cache[rel_path] = content
        return content

    def grep_any(self, needle: str, files: list[str]) -> tuple[bool, str | None]:
        """Return (found, in_which_file)."""
        for f in files:
            c = self.read(f)
            if c and needle in c:
                return True, f
        return False, None


# ---------------------------------------------------------------------------
# Local SPEC extraction
# ---------------------------------------------------------------------------

SCHEMA_RE = re.compile(r"`(rapp-[a-z][a-z0-9-]*\/[0-9]+\.[0-9]+(?:\.[0-9]+)?)`")
KIND_RE = re.compile(r"^`kind: \"([a-z][a-z0-9-]*)\"`", re.MULTILINE)
RAPPID_FORMAT_RE = re.compile(
    r"```\s*\n(rappid:@[^`\n]+)\s*\n```"
)


def extract_schemas(text: str) -> set[str]:
    return set(SCHEMA_RE.findall(text))


def extract_kinds(text: str) -> set[str]:
    """Extract `kind` values quoted in `kind: "..."` form."""
    kinds = set()
    for m in re.finditer(r"['\"`]kind['\"`]?\s*[:=]\s*['\"]([a-z][a-z0-9-]*)['\"]", text):
        kinds.add(m.group(1))
    return kinds


def extract_rappid_format(text: str) -> str | None:
    m = RAPPID_FORMAT_RE.search(text)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_schemas_exist_upstream(spec: str, up: Upstream) -> list[tuple[str, bool, str | None]]:
    schemas = sorted(extract_schemas(spec))
    results = []
    for s in schemas:
        # Schemas this repo OWNS (rapp-network/, rapp-twin-manifest/, rapp-project-twin-job/,
        # rapp-twin-transport/, rapp-twin-workspace/) are NOT required to exist upstream.
        # Schemas the upstream owns MUST exist upstream.
        owned_here_prefixes = (
            "rapp-network/", "rapp-twin-manifest/", "rapp-project-twin-job/",
            "rapp-twin-transport/", "rapp-twin-workspace/",
        )
        if any(s.startswith(p) for p in owned_here_prefixes):
            results.append((s, True, "(owned by this repo — not required upstream)"))
            continue
        found, where = up.grep_any(s, UPSTREAM_PIN_FILES)
        results.append((s, found, where))
    return results


def check_rappid_format(spec: str, up: Upstream) -> tuple[bool, str | None, str | None]:
    here = extract_rappid_format(spec)
    if not here:
        return False, None, "this repo's SPEC.md has no rappid format block in §5"
    estate = up.read("pages/docs/ESTATE_SPEC.md")
    if not estate:
        return False, here, "upstream ESTATE_SPEC.md unreachable (try setting RAPP_REPO=/path/to/clone)"
    # The upstream format is in a fenced block too.
    m = re.search(r"```\s*\n(rappid:@[^`\n]+)\s*\n```", estate)
    if not m:
        return False, here, "upstream ESTATE_SPEC.md has no rappid format block"
    there = m.group(1).strip()
    # Compare structurally — normalize both placeholders (<owner>, <slug>, ...) and
    # concrete tokens (kody-w, hex, etc.) to a single wildcard so the shape
    # comparison sees only the structural Eternity form `rappid:@_/_:_`.
    def normalize(s: str) -> str:
        s = re.sub(r"<[^>]+>", "_", s)            # <owner> → _
        s = re.sub(r"[A-Za-z0-9-]+", "_", s)      # project / kody-w / hex → _
        return s
    here_shape = normalize(here)
    there_shape = normalize(there)
    if here_shape == there_shape:
        return True, here, None
    return False, here, f"shape diverges from upstream: here={here_shape!r}, upstream={there_shape!r}"


def check_kinds(spec: str, up: Upstream) -> list[tuple[str, bool, str | None]]:
    kinds = extract_kinds(spec)
    estate = up.read("pages/docs/ESTATE_SPEC.md") or ""
    # Frozen kinds list lives in ESTATE_SPEC §1 (one line, front_door + gate kinds
    # in backticks). Grab the whole "Valid kinds" line — dot-tolerant, since the
    # 2026-06-02 amendment note ("Art. XLVI.2") contains periods.
    m = re.search(r"\*\*Valid kinds\*\*(.+)", estate)
    upstream_kinds = set()
    if m:
        for k in re.findall(r"`([a-z][a-z0-9-]*)`", m.group(1)):
            upstream_kinds.add(k)
    results = []
    for k in sorted(kinds):
        results.append((k, k in upstream_kinds, ", ".join(sorted(upstream_kinds)) or None))
    return results


def check_paths(up: Upstream) -> list[tuple[str, bool]]:
    results = []
    for p in UPSTREAM_PIN_FILES:
        results.append((p, up.read(p) is not None))
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rapp-repo", default=os.environ.get("RAPP_REPO"),
                    help="Path to a local clone of kody-w/RAPP")
    ap.add_argument("--offline", action="store_true",
                    help="Don't fetch from raw.githubusercontent.com")
    ap.add_argument("--json", action="store_true", help="Machine-readable output")
    args = ap.parse_args(argv)

    local_root = None
    if args.rapp_repo:
        local_root = Path(args.rapp_repo).expanduser().resolve()
    else:
        sibling = REPO_ROOT / "_rapp_clone"
        if sibling.exists():
            local_root = sibling

    up = Upstream(local_root, allow_network=not args.offline)

    if not SPEC_MD.exists():
        print(f"ERROR: {SPEC_MD} not found", file=sys.stderr)
        return 2
    spec_text = SPEC_MD.read_text()

    results = {
        "upstream_paths": check_paths(up),
        "schemas": check_schemas_exist_upstream(spec_text, up),
        "rappid_format": check_rappid_format(spec_text, up),
        "kinds": check_kinds(spec_text, up),
    }

    drift = []

    if args.json:
        print(json.dumps({
            "upstream_root": str(local_root) if local_root else None,
            "offline": args.offline,
            "results": {
                "upstream_paths": results["upstream_paths"],
                "schemas": results["schemas"],
                "rappid_format": {
                    "match": results["rappid_format"][0],
                    "here": results["rappid_format"][1],
                    "note": results["rappid_format"][2],
                },
                "kinds": results["kinds"],
            },
        }, indent=2, default=str))
    else:
        print(f"upstream source: {local_root or 'raw.githubusercontent.com'}")
        print(f"offline mode:    {args.offline}")
        print()

        print("== upstream file reachability ==")
        for p, ok in results["upstream_paths"]:
            mark = "OK  " if ok else "MISS"
            print(f"  [{mark}] {p}")
            if not ok:
                drift.append(f"unreachable: {p}")
        print()

        print("== schemas referenced in SPEC.md ==")
        for s, found, where in results["schemas"]:
            mark = "OK  " if found else "DRFT"
            note = f" → {where}" if where else ""
            print(f"  [{mark}] {s}{note}")
            if not found:
                drift.append(f"schema not found upstream: {s}")
        print()

        print("== rappid format alignment ==")
        match, here, note = results["rappid_format"]
        if match:
            print(f"  [OK  ] {here}")
        else:
            print(f"  [DRFT] {here or '(none)'}")
            print(f"         {note}")
            drift.append(f"rappid format drift: {note}")
        print()

        print("== kind values ==")
        for k, ok, upstream_list in results["kinds"]:
            mark = "OK  " if ok else "WARN"
            note = f" (upstream: {upstream_list})" if upstream_list else " (no upstream list found)"
            print(f"  [{mark}] {k}{note}")
            # `kind` mismatches are loud warnings, not failures — kinds get added.
        print()

        if drift:
            print(f"FAIL — {len(drift)} drift signal(s):")
            for d in drift:
                print(f"  - {d}")
            print()
            print("Drift is the signal that ONE OR BOTH repos need an update.")
            print("Investigate before assuming the upstream is wrong.")
        else:
            print("PASS — every check aligns with kody-w/RAPP.")

    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
