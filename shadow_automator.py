#!/usr/bin/env python3
"""
ShadowAutomator — pro, addictive, CLI-first file/folder organizer.

Usage examples:
  # preview
  ./shadow_automator.py /path/to/messy --dry-run

  # actually organize
  ./shadow_automator.py /path/to/messy

  # with "cast" (magical) mode
  ./shadow_automator.py /path/to/messy cast --archive-days 365 --ai

Author: Handcrafted for a pro demo.
"""
from __future__ import annotations
import os
import sys
import shutil
import argparse
import datetime
import zipfile
import textwrap

# ---------- Configurable defaults ----------
ARCHIVE_DIR_NAME = "ShadowArchives"
REPORT_FILENAME = "shadow_report.txt"
SNAPSHOT_BEFORE = "shadow_before.txt"
SNAPSHOT_AFTER = "shadow_after.txt"
# -------------------------------------------

# ANSI color helpers (no external libs)
CSI = "\033["
RESET = CSI + "0m"
BOLD = CSI + "1m"
GREEN = CSI + "92m"
YELLOW = CSI + "93m"
CYAN = CSI + "96m"
MAGENTA = CSI + "95m"
FAINT = CSI + "2m"

def c(text: str, color: str = "") -> str:
    return f"{color}{text}{RESET}" if color else text

# ----- Utilities -----
def now_ts():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def human_days(days: int) -> str:
    return f"{days} day{'s' if days != 1 else ''}"

def walk_files(root: str):
    for base, dirs, files in os.walk(root):
        for f in files:
            yield os.path.join(base, f)

def snapshot_tree(root: str, max_lines=1000) -> str:
    """Return an ASCII tree snapshot (limited size)."""
    lines = []
    for base, dirs, files in os.walk(root):
        rel = os.path.relpath(base, root)
        indent = "" if rel == "." else ("  " * (rel.count(os.sep)+0))
        display = os.path.basename(base) if rel != "." else os.path.basename(root)
        if rel == ".":
            lines.append(display + "/")
        else:
            lines.append(f"{indent}{display}/")
        for f in sorted(files)[:200]:
            lines.append(f"{indent}  └─ {f}")
        if len(lines) > max_lines:
            lines.append("  ... (snapshot truncated)")
            break
    return "\n".join(lines)

# ----- Smart rename -----
def smart_filename(dest_dir: str, name: str, pattern: str = None) -> str:
    """Return a safe file name in dest_dir using pattern or timestamp."""
    base, ext = os.path.splitext(name)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if pattern:
        fname = pattern.replace("{name}", sanitize(base)).replace("{ts}", ts).replace("{ext}", ext.lstrip("."))
        if not ext and "{ext}" in pattern:
            # pattern may expect ext; ensure extension present
            fname = fname
        # add ext if user didn't include
        if not fname.endswith(ext) and ext:
            fname = fname + ext
    else:
        fname = f"{sanitize(base)}_{ts}{ext}"
    safe = fname
    i = 1
    # avoid collisions
    while os.path.exists(os.path.join(dest_dir, safe)):
        safe = f"{os.path.splitext(fname)[0]}_{i}{ext}"
        i += 1
    return safe

def sanitize(s: str) -> str:
    """Make filename safe-ish: remove control chars and collapse spaces."""
    s = s.replace("\n", " ").replace("\r", " ")
    s = "".join(ch for ch in s if ch not in ('/', '\\', '\0'))
    s = "_".join(s.strip().split())
    return s[:120]

# ----- Archives -----
def make_archive_file(root: str, files: list[str], archive_root: str) -> str:
    """Create a dated zip archive of files (paths), returns archive path."""
    os.makedirs(archive_root, exist_ok=True)
    archive_name = f"shadow_archive_{now_ts()}.zip"
    archive_path = os.path.join(archive_root, archive_name)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            arcname = os.path.relpath(f, root)
            zf.write(f, arcname)
    return archive_path

# ----- CLI behavior -----
def parse_args():
    p = argparse.ArgumentParser(prog="shadow_automator", description="ShadowAutomator — tidy your chaos.")
    p.add_argument("path", help="Path to folder to tidy")
    p.add_argument("--dry-run", action="store_true", help="Show what would be done")
    p.add_argument("--archive-days", type=int, default=365, help="Archive files older than N days (0 to disable)")
    p.add_argument("--pattern", type=str, default=None, help="Rename pattern, e.g. '{name}_{ts}.{ext}' or 'ProjectA_{ts}.{ext}'")
    p.add_argument("--ai", action="store_true", help="Show AI-style folder suggestions (local rules)")
    p.add_argument("mode", nargs="?", choices=("cast",), help="Optional 'cast' mode for magical output")
    return p.parse_args()

def human_age_days(path: str) -> int:
    stat = os.stat(path)
    mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
    delta = datetime.datetime.now() - mtime
    return delta.days

def type_folder_for(ext: str) -> str:
    ext = ext.lower().lstrip(".")
    if ext in ("jpg","jpeg","png","gif","bmp","webp","svg"):
        return "Pictures"
    if ext in ("mp4","mkv","mov","avi","webm"):
        return "Videos"
    if ext in ("pdf","doc","docx","odt","xls","xlsx","ppt","pptx","txt","md"):
        return "Documents"
    if ext in ("zip","tar","gz","7z","rar"):
        return "Archives"
    if ext in ("py","js","html","css","go","rs","java","c","cpp","sh"):
        return "Code"
    if ext in ("mp3","wav","flac","ogg","m4a"):
        return "Music"
    return "Misc"

def run_shadow(root: str, dry_run=False, archive_days=365, pattern=None, ai=False, cast_mode=False):
    root = os.path.abspath(root)
    if not os.path.exists(root) or not os.path.isdir(root):
        print(c("❌ Path not found or not a folder: " + root, YELLOW))
        return 1

    # Snapshots
    before_snapshot = snapshot_tree(root)
    with open(os.path.join(root, SNAPSHOT_BEFORE), "w") as f:
        f.write(before_snapshot)

    print(c("\n" + "="*48, MAGENTA))
    if cast_mode:
        print(c("🔮 Casting Shadow Spell...", BOLD+CYAN))
    else:
        print(c("🧹 ShadowAutomator — Taming folder chaos", BOLD+CYAN))
    print(c("="*48 + "\n", MAGENTA))

    moved = 0
    renamed = 0
    archived = 0
    archive_files = []

    # Collect target folders mapping
    targets = {}
    for fpath in list(walk_files(root)):
        # skip inside our own output folders
        if any(part in (ARCHIVE_DIR_NAME, ".git", SNAPSHOT_BEFORE, SNAPSHOT_AFTER, REPORT_FILENAME) for part in fpath.split(os.sep)):
            continue
        rel = os.path.relpath(fpath, root)
        # ignore dotfiles at root? keep them in Misc
        ext = os.path.splitext(fpath)[1].lower().lstrip(".")
        folder = type_folder_for(ext)
        # by year/month
        year = datetime.datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y")
        month = datetime.datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%B")
        dest_dir = os.path.join(root, folder, year, month)
        targets[fpath] = dest_dir

    # Process each file
    total = len(targets)
    i = 0
    for src, dest_dir in targets.items():
        i += 1
        name = os.path.basename(src)
        # Skip if already in the right place (safety)
        if os.path.commonpath([os.path.abspath(src), os.path.abspath(dest_dir)]) == os.path.abspath(dest_dir):
            continue

        os.makedirs(dest_dir, exist_ok=True)
        # smart rename pattern if needed
        newname = name
        if pattern:
            newname = smart_filename(dest_dir, name, pattern)
        dest_path = os.path.join(dest_dir, newname)

        # Archiving decision
        should_archive = False
        if archive_days and archive_days > 0:
            age = human_age_days(src)
            if age >= archive_days:
                should_archive = True

        # display
        pct = int((i/total)*100) if total else 100
        spinner = "|/-\\"[i % 4]
        if dry_run:
            print(c(f"[DRY] {spinner} [{pct:3}%] {name} -> {os.path.relpath(dest_path, root)}", FAINT+CYAN))
            if should_archive:
                print(c(f"       (would archive, age {age} days)", FAINT+YELLOW))
        else:
            # Move (or plan to add to archive list)
            try:
                shutil.move(src, dest_path)
                moved += 1
                if newname != name:
                    renamed += 1
                print(c(f"{spinner} [{pct:3}%] Moved: {name} -> {os.path.relpath(dest_path, root)}", GREEN))
                if should_archive:
                    archive_files.append(dest_path)
            except Exception as e:
                print(c(f"⚠️  Failed moving {name}: {e}", YELLOW))

    # create archives if needed
    if archive_days and archive_days > 0 and archive_files:
        archive_root = os.path.join(root, ARCHIVE_DIR_NAME, datetime.datetime.now().strftime("%Y"))
        if dry_run:
            print(c(f"\n[DRY] Would create archive with {len(archive_files)} files in {os.path.relpath(archive_root, root)}", FAINT+YELLOW))
        else:
            archive_path = make_archive_file(root, archive_files, archive_root)
            archived += 1
            # remove archived files from disk after zipping
            for f in archive_files:
                try:
                    os.remove(f)
                except Exception:
                    pass
            print(c(f"\n📦 Archive created: {os.path.relpath(archive_path, root)} ({len(archive_files)} files)", MAGENTA))

    # snapshots after
    after_snapshot = snapshot_tree(root)
    if not dry_run:
        with open(os.path.join(root, SNAPSHOT_AFTER), "w") as f:
            f.write(after_snapshot)

    # shadow report
    report_lines = [
        "ShadowAutomator Report",
        f"Path: {root}",
        f"Time: {datetime.datetime.now().isoformat()}",
        f"Dry run: {dry_run}",
        f"Files touched (moved): {moved}",
        f"Files renamed: {renamed}",
        f"Archives made: {archived}",
        "",
        "Before snapshot:",
        "-"*40,
        before_snapshot[:3000],
        "",
        "After snapshot:",
        "-"*40,
        after_snapshot[:3000],
    ]
    report_text = "\n".join(report_lines)
    if dry_run:
        print(c("\n" + "="*36, FAINT))
        print(c("Shadow Report (dry run)", FAINT+MAGENTA))
    else:
        print(c("\n" + "="*36, MAGENTA))
        print(c("Shadow Report", BOLD+MAGENTA))
    print(c("="*36, MAGENTA))
    print(c(f"Files moved: {moved}  |  Renamed: {renamed}  |  Archives: {archived}", CYAN))
    if ai:
        # rule-based suggestion (no external AI)
        print(c("\n🤖 Shadow AI Suggestions:", BOLD+YELLOW))
        print(c("- Consider grouping images by resolution", YELLOW))
        print(c("- Archive PDFs older than 1 year", YELLOW))
        print(c("- Create 'Projects/<project_name>' for loose docs", YELLOW))

    # save report
    try:
        with open(os.path.join(root, REPORT_FILENAME), "w") as rf:
            rf.write(report_text)
        if dry_run:
            print(c(f"\n[DRY] Would save report at: {os.path.join(root, REPORT_FILENAME)}", FAINT+YELLOW))
        else:
            print(c(f"\n📄 Saved shadow report: {os.path.join(root, REPORT_FILENAME)}", MAGENTA))
    except Exception as e:
        print(c(f"⚠️  Could not save report: {e}", YELLOW))

    # also save snapshots if not dry
    if not dry_run:
        print(c(f"\nSaved snapshots: {SNAPSHOT_BEFORE}, {SNAPSHOT_AFTER}", MAGENTA))

    print(c("\n✨ Done. Your chaos has been tidied. ✨\n", BOLD+GREEN))
    return 0

def main():
    args = parse_args()
    # simple sanity: avoid operating on root or /home for safety
    p = os.path.abspath(os.path.expanduser(args.path))
    if p in ("/", os.path.expanduser("~")):
        print(c("Refusing to operate on root or home folder for safety.", YELLOW))
        sys.exit(1)

    dry = args.dry_run
    archivedays = args.archive_days
    pattern = args.pattern
    ai = args.ai
    cast = args.mode == "cast"

    # If not dry-run and not explicit, ask for confirmation (interactive)
    if not dry:
        print(c(f"Target folder: {p}", CYAN))
        confirm = input(c("Proceed to organize this folder? (y/N): ", FAINT))
        if confirm.strip().lower() != "y":
            print(c("Aborted by user.", YELLOW))
            sys.exit(0)

    rc = run_shadow(p, dry_run=dry, archive_days=archivedays, pattern=pattern, ai=ai, cast_mode=cast)
    sys.exit(rc)

if __name__ == "__main__":
    main()
