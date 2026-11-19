#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Puts the installer's files into its binary packages.

debian/raye-paths says which package ships each file or folder. This
script checks that list against the tree (nothing missing, nothing left
out, no path shipped twice, programs executable) and copies the files
into debian/<package>/.

    raye_paths.py check            check only
    raye_paths.py install          check, then copy
    raye_paths.py verify X.deb...  compare built packages with the list

RAYE_PATHS_STRICT=1 makes a missing "?" path an error.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

# Folders whose files are all shipped: every file in them must be listed.
SHIPPED_ROOTS = ("etc", "usr", "qml", "assets/illustrations", "data")
BUILD_TREE = "debian/tmp"
# Files under these get run, so they must keep their exec bit.
PROGRAM_DIRS = ("usr/bin/", "usr/sbin/", "usr/libexec/", "usr/share/initramfs-tools/scripts/",
                "etc/initramfs-tools/scripts/")
# Byproducts of running the tests, never shipped.
SKIPPED_NAMES = ("__pycache__",)
SKIPPED_SUFFIXES = (".pyc", ".pyo", "~")
# Added by the packaging tools, not by this list.
DEB_EXTRAS = ("usr/share/doc/", "usr/share/lintian/", "usr/share/man/", "usr/share/bug/")


# A source under debian/tmp is a BUILD OUTPUT. Its absence says NOTHING
# about whether the part that makes it is written: outside a package build
# debian/tmp does not exist at all, so every one of these entries reads as
# "missing" whatever the state of the source. Measured 2026-11-07 on this
# repository: the release gate reported
#     raye-paths: error: debian/tmp/usr/bin/raye-first-run: missing
# while app/firstrun/CMakeLists.txt was written and installed that very
# binary (install(TARGETS raye-first-run RUNTIME DESTINATION bindir), line
# 18). The gate was not wrong about the file -- it was answering a question
# it had no way to ask.
#
# What DOES say whether the part is written is the part's own
# CMakeLists.txt, and that is readable with no build at all -- the same
# property the rest of this project demands of a citation.
#
# RAYE_PARTS is READ from the top CMakeLists.txt, never copied here: a
# second list of the parts would go stale on the day one is added, which is
# exactly the defect this function exists to undo.
def cmake_parts(root) -> list[str]:
    """The RAYE_PARTS of the top CMakeLists.txt, in order."""
    try:
        text = (pathlib.Path(root) / "CMakeLists.txt").read_text()
    except OSError:
        return []
    m = re.search(r"set\s*\(\s*RAYE_PARTS\s+([^)]*)\)", text)
    if not m:
        return []
    return [w for w in m.group(1).split() if w and not w.startswith("#")]


def producing_part(root, source: str) -> str | None:
    """Which written CMake part installs this debian/tmp path, if any.

    Returns the part's folder (e.g. "app/firstrun"), or None when no
    written part installs it -- that is, when the part really is owed.
    """
    root = pathlib.Path(root)
    name = source.rsplit("/", 1)[-1]
    if not name:
        return None
    for part in cmake_parts(root):
        lists = root / part / "CMakeLists.txt"
        if not lists.is_file():
            continue          # the part is not written yet
        try:
            text = lists.read_text()
        except OSError:
            continue
        if re.search(r"install\s*\(\s*TARGETS\s+%s\b" % re.escape(name), text):
            return part
    return None


class PathsError(Exception):
    pass


@dataclass(frozen=True)
class Entry:
    package: str
    source: str
    dest: str
    optional: bool
    line: int

    @property
    def from_build(self) -> bool:
        return self.source == BUILD_TREE or self.source.startswith(BUILD_TREE + "/")


@dataclass
class Plan:
    copies: list = field(default_factory=list)  # (source path, dest, package)
    notes: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    # Not errors and not notes: entries this run had no way to judge.
    # Keeping them apart is the whole point -- folded into errors they read
    # as unwritten parts, folded into notes they vanish.
    cannot_judge: list = field(default_factory=list)


def _clean_path(text: str, lineno: int) -> str:
    path = text.strip("/") if not text.startswith("/") else text
    parts = path.split("/")
    if not path or path.startswith("/") or ".." in parts or "." in parts or "//" in path:
        raise PathsError(f"debian/raye-paths line {lineno}: bad path {text!r}")
    return path


def _expand(text: str, variables: dict, lineno: int) -> str:
    def value(match):
        name = match.group(1)
        if name not in variables:
            raise PathsError(f"debian/raye-paths line {lineno}: unknown variable {name}")
        return variables[name]
    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", value, text)


def parse(text: str, variables: dict) -> list[Entry]:
    entries = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        fields = raw.split("#", 1)[0].split()
        if not fields:
            continue
        if len(fields) not in (2, 3):
            raise PathsError(f"debian/raye-paths line {lineno}: expected 'package source [destination]'")
        package, source = fields[0], fields[1]
        optional = source.startswith("?")
        source = _clean_path(source[1:] if optional else source, lineno)
        if len(fields) == 3:
            dest = _clean_path(_expand(fields[2], variables, lineno), lineno)
        elif source.startswith(BUILD_TREE + "/"):
            dest = source[len(BUILD_TREE) + 1:]
        else:
            dest = source
        entries.append(Entry(package, source, dest, optional, lineno))
    return entries


def read_control(text: str) -> dict[str, set[str]]:
    """Binary packages of debian/control, each with the names in its Depends."""
    packages = {}
    for para in re.split(r"\n\s*\n", text):
        fields, key = {}, None
        for line in para.splitlines():
            if line.startswith("#"):
                continue
            if line[:1] in (" ", "\t") and key:
                fields[key] += " " + line.strip()
            elif ":" in line:
                key, value = line.split(":", 1)
                fields[key] = value.strip()
        if "Package" in fields:
            names = set()
            for alt in re.split(r"[,|]", fields.get("Depends", "")):
                name = re.sub(r"\(.*?\)|\[.*?\]|<.*?>", "", alt).strip()
                if name:
                    names.add(name.split(":")[0] if not name.startswith("${") else name)
            packages[fields["Package"]] = names
    return packages


def _skipped(rel: str) -> bool:
    parts = rel.split("/")
    return any(p in SKIPPED_NAMES for p in parts) or rel.endswith(SKIPPED_SUFFIXES)


def _files(base: pathlib.Path):
    """Files and symlinks under base (or base itself), relative to base."""
    if base.is_symlink() or base.is_file():
        yield ""
        return
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIPPED_NAMES
                             and not os.path.islink(os.path.join(dirpath, d)))
        links = [d for d in os.listdir(dirpath)
                 if os.path.islink(os.path.join(dirpath, d)) and os.path.isdir(os.path.join(dirpath, d))]
        for name in sorted(filenames + links):
            rel = os.path.relpath(os.path.join(dirpath, name), base)
            if not _skipped(rel):
                yield rel


def _join(a: str, b: str) -> str:
    return f"{a}/{b}" if b else a


def plan(root: pathlib.Path, strict: bool, variables: dict) -> Plan:
    root = pathlib.Path(root)
    result = Plan()
    try:
        control = read_control((root / "debian/control").read_text())
        entries = parse((root / "debian/raye-paths").read_text(), variables)
    except (OSError, PathsError) as exc:
        result.errors.append(str(exc))
        return result

    claimed: set[str] = set()   # source files covered by an entry
    owner: dict[str, Entry] = {}  # destination file -> entry
    for entry in entries:
        if entry.package not in control:
            result.errors.append(f"line {entry.line}: {entry.package} is not a package of debian/control")
            continue
        base = root / entry.source
        if not (base.exists() or base.is_symlink()):
            # Three different states, and they used to share one message.
            part = producing_part(root, entry.source) if entry.from_build else None
            if part is not None and not (root / BUILD_TREE).is_dir():
                # The part IS written; we are simply not inside a package
                # build. Say that, and never call it an unwritten part.
                result.cannot_judge.append(
                    f"{entry.source}: {part} is written and installs it, but "
                    f"{BUILD_TREE} does not exist here, so this gate cannot "
                    f"see the file (line {entry.line}). It is judged by the "
                    f"package build, which runs this script after "
                    f"dh_auto_install")
            elif entry.optional and not strict:
                owes = f", and no written part installs it" if entry.from_build else ""
                result.notes.append(f"{entry.source}: not there yet, skipped{owes}")
            elif entry.from_build and part is None:
                result.errors.append(
                    f"{entry.source}: missing, and no part of RAYE_PARTS "
                    f"installs it -- the part that makes it is not written "
                    f"(line {entry.line})")
            else:
                result.errors.append(f"{entry.source}: missing (line {entry.line})")
            continue
        for rel in _files(base):
            src = _join(entry.source, rel)
            dest = _join(entry.dest, rel)
            claimed.add(src)
            if dest in owner:
                other = owner[dest]
                result.errors.append(f"{dest}: shipped twice (lines {other.line} and {entry.line})")
                continue
            owner[dest] = entry
            path = root / src
            if (dest.startswith(PROGRAM_DIRS) and not path.is_symlink()
                    and not os.access(path, os.X_OK)):
                result.errors.append(f"{src}: a program, but not executable")
            result.copies.append((path, dest, entry.package))

    for top in SHIPPED_ROOTS + (BUILD_TREE,):
        base = root / top
        if not base.is_dir():
            continue
        for rel in _files(base):
            src = _join(top, rel)
            if src not in claimed:
                result.errors.append(f"{src}: not listed in debian/raye-paths")
    return result


def _inside(staged: pathlib.Path, path: pathlib.Path) -> bool:
    try:
        path.resolve().relative_to(staged)
    except ValueError:
        return False
    return True


def install(result: Plan, root: pathlib.Path) -> None:
    root = pathlib.Path(root)
    for path, dest, package in result.copies:
        staged = (root / "debian" / package).resolve()
        target = staged / dest
        # A symlink to a folder inside the staging tree would otherwise
        # take the copy out of the package, silently.
        if not _inside(staged, target.parent):
            raise PathsError(f"{dest}: lands outside debian/{package}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink() or target.exists():
            target.unlink()
        if path.is_symlink():
            target.symlink_to(os.readlink(path))
        else:
            shutil.copy2(path, target)


def compare_deb(package: str, expected: set[str], actual: set[str]) -> tuple[list, list]:
    actual = {p for p in actual if not p.startswith(DEB_EXTRAS)}
    return sorted(expected - actual), sorted(actual - expected)


def _deb_files(deb: str) -> tuple[str, set[str]]:
    package = subprocess.run(["dpkg-deb", "-f", deb, "Package"], check=True,
                             capture_output=True, text=True).stdout.strip()
    listing = subprocess.run(["dpkg-deb", "-c", deb], check=True,
                             capture_output=True, text=True).stdout
    files = set()
    for line in listing.splitlines():
        if line.startswith("d"):
            continue
        name = line.split(None, 5)[5].split(" -> ")[0]
        files.add(name.removeprefix("./"))
    return package, files


def main(argv=None, env=None) -> int:
    env = os.environ if env is None else env
    parser = argparse.ArgumentParser(prog="raye_paths.py")
    parser.add_argument("command", choices=("check", "install", "verify"))
    parser.add_argument("debs", nargs="*")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)

    variables = {"DEB_HOST_MULTIARCH": env.get("DEB_HOST_MULTIARCH") or _multiarch()}
    strict = env.get("RAYE_PATHS_STRICT", "") not in ("", "0")
    root = pathlib.Path(args.root)
    result = plan(root, strict, variables)
    for note in result.notes:
        print(f"raye-paths: {note}")
    # On stderr, and under their own word: an entry this run could not
    # judge is not a pass. Printing them with the notes is how a gate comes
    # to look green over something it never looked at.
    for undecided in result.cannot_judge:
        print(f"raye-paths: NOT JUDGED HERE: {undecided}", file=sys.stderr)
    for error in result.errors:
        print(f"raye-paths: error: {error}", file=sys.stderr)
    if result.cannot_judge:
        print(f"raye-paths: {len(result.cannot_judge)} entr"
              f"{'y' if len(result.cannot_judge) == 1 else 'ies'} could not "
              f"be judged outside a package build (see above); the package "
              f"build judges them", file=sys.stderr)
    if result.errors:
        return 1

    if args.command == "install":
        install(result, root)
    elif args.command == "verify":
        expected: dict[str, set[str]] = {}
        for _, dest, package in result.copies:
            expected.setdefault(package, set()).add(dest)
        bad = False
        for deb in args.debs:
            package, files = _deb_files(deb)
            missing, extra = compare_deb(package, expected.get(package, set()), files)
            for path in missing:
                print(f"{package}: missing {path}", file=sys.stderr)
            for path in extra:
                print(f"{package}: not in the list {path}", file=sys.stderr)
            bad = bad or bool(missing or extra)
            print(f"{package}: {len(files)} entries, {'differs' if missing or extra else 'matches'}")
        return 1 if bad else 0
    return 0


def _multiarch() -> str:
    try:
        return subprocess.run(["dpkg-architecture", "-qDEB_HOST_MULTIARCH"], check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "x86_64-linux-gnu"


if __name__ == "__main__":
    sys.exit(main())
