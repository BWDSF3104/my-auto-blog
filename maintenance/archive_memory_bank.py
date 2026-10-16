"""Memory Bank batch cleanup (docs/ai: tasks/ verification/ tmp/ + current-task.tsv).

Usage:
    python maintenance/archive_memory_bank.py            # dry run (default)
    python maintenance/archive_memory_bank.py --apply    # apply + git add touched paths
    python maintenance/archive_memory_bank.py --apply --no-git-add  # apply, skip staging
    python maintenance/archive_memory_bank.py --date 2026-10-14 --root .
    python maintenance/archive_memory_bank.py --tmp-retention-days 14

Rules: docs/ai/memory-bank-guide.md "バッチクリーンアップ"
- current-task.tsv: drop reference lines whose status is in {完了, 中断}
- tasks/: mtime older than 14 days AND not referenced by the tsv -> mv to tasks/archive/
- verification/: per feature dir keep the newest 2 runs (mtime order), delete the rest
- tmp/: delete entries whose newest mtime is older than TMP_RETENTION_DAYS
  (default 7, --tmp-retention-days); directories are judged by the newest
  mtime inside them (deletion delegated to kilo-safe-*.cmd)
- git: on --apply, stage the touched paths (git add) so the agent only needs
  to commit; --no-git-add skips staging. The script never commits/pushes.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

AGE_DAYS = 14
KEEP_RUNS = 2
TMP_RETENTION_DAYS = 7
DROP_STATUSES = ("完了", "中断")


@dataclass(frozen=True)
class Action:
    kind: str
    path: Path
    detail: str = ""


@dataclass
class Result:
    action: Action
    status: str
    message: str = ""


@dataclass
class Plan:
    root: Path
    today: date
    tsv_drops: list[str] = field(default_factory=list)
    mvs: list[Path] = field(default_factory=list)
    rm_files: list[Path] = field(default_factory=list)
    rm_dirs: list[Path] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def build_plan(
    root: Path,
    today: date,
    stat_fn=os.stat,
    tmp_retention_days: int = TMP_RETENTION_DAYS,
) -> Plan:
    plan = Plan(root=root, today=today)
    ai = root / "docs" / "ai"

    tsv_path = ai / "current-task.tsv"
    referenced: set[str] = set()
    if tsv_path.is_file():
        lines = tsv_path.read_text(encoding="utf-8").splitlines()
        for line in lines[1:]:
            if not line:
                continue
            cols = line.split("\t")
            if len(cols) != 3:
                plan.notes.append(f"tsv: malformed line skipped: {line!r}")
                continue
            task_file, status, _next_action = cols
            if status in DROP_STATUSES:
                plan.tsv_drops.append(line)
            else:
                referenced.add(task_file)
    else:
        plan.notes.append("tsv: not found, reference set is empty")

    tasks_dir = ai / "tasks"
    if tasks_dir.is_dir():
        cutoff_ts = (datetime.combine(today, time.min) - timedelta(days=AGE_DAYS)).timestamp()
        for f in sorted(tasks_dir.glob("*.md")):
            if not f.is_file():
                continue
            if f.relative_to(root).as_posix() in referenced:
                continue
            if stat_fn(f).st_mtime <= cutoff_ts:
                plan.mvs.append(f)
    else:
        plan.notes.append("tasks: directory not found")

    ver_dir = ai / "verification"
    if ver_dir.is_dir():
        for feat in sorted(ver_dir.iterdir()):
            if not feat.is_dir():
                plan.notes.append(f"verification: keep top-level file (out of scope): {feat.name}")
                continue
            runs_dir = feat / "runs"
            if not runs_dir.is_dir():
                continue
            entries = sorted(runs_dir.iterdir())
            run_dirs = [d for d in entries if d.is_dir() and not d.is_symlink()]
            for d in entries:
                if d not in run_dirs:
                    plan.notes.append(f"verification: keep non-directory (out of scope): {d.name}")
            if len(run_dirs) <= KEEP_RUNS:
                continue
            ordered = sorted(run_dirs, key=lambda d: (-stat_fn(d).st_mtime, d.name))
            for d in ordered[KEEP_RUNS:]:
                plan.rm_dirs.append(d)
    else:
        plan.notes.append("verification: directory not found")

    tmp_dir = ai / "tmp"
    if tmp_dir.is_dir():
        tmp_cutoff_ts = (
            datetime.combine(today, time.min) - timedelta(days=tmp_retention_days)
        ).timestamp()
        for e in sorted(tmp_dir.iterdir()):
            if e.is_symlink():
                plan.notes.append(f"tmp: skip symlink (safe-* refuses): {e.name}")
                continue
            newest = stat_fn(e).st_mtime
            if e.is_dir():
                for p in e.rglob("*"):
                    try:
                        newest = max(newest, stat_fn(p).st_mtime)
                    except OSError:
                        continue
            if newest > tmp_cutoff_ts:
                plan.notes.append(
                    f"tmp: keep (updated within {tmp_retention_days}d): {e.name}"
                )
                continue
            if e.is_dir():
                plan.rm_dirs.append(e)
            else:
                plan.rm_files.append(e)
    else:
        plan.notes.append("tmp: directory not found")

    return plan


def _default_runner(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, capture_output=True, encoding="utf-8", timeout=300)
    out = "\n".join(part for part in (proc.stdout, proc.stderr) if part).strip()
    return proc.returncode, out


def intended_staged_paths(plan: Plan) -> list[Path]:
    """Paths that --apply would touch and therefore stage (dry-run preview)."""
    paths: list[Path] = []
    if plan.tsv_drops:
        paths.append(plan.root / "docs" / "ai" / "current-task.tsv")
    archive_dir = plan.root / "docs" / "ai" / "tasks" / "archive"
    for src in plan.mvs:
        paths.append(src)
        paths.append(archive_dir / src.name)
    paths.extend(plan.rm_files)
    paths.extend(plan.rm_dirs)
    return sorted(set(paths), key=lambda p: p.as_posix())


def _default_git_add(root: Path, paths: list[Path]) -> tuple[int, str]:
    rels = [p.relative_to(root).as_posix() for p in paths]
    return _default_runner(["git", "-C", str(root), "add", "--", *rels])


def execute_plan(plan: Plan, apply: bool, runner=None, git_add=None) -> list[Result]:
    if runner is None:
        runner = _default_runner
    results: list[Result] = []
    root = plan.root
    planned = "planned" if not apply else "applied"
    staged: list[Path] = []

    if plan.tsv_drops:
        tsv_path = root / "docs" / "ai" / "current-task.tsv"
        action = Action("tsv_drop", tsv_path, f"{len(plan.tsv_drops)} line(s)")
        if apply:
            lines = tsv_path.read_text(encoding="utf-8").splitlines()
            kept = [lines[0]] if lines else []
            kept += [l for l in lines[1:] if l not in plan.tsv_drops]
            tsv_path.write_text("\n".join(kept) + "\n", encoding="utf-8", newline="\n")
            staged.append(tsv_path)
        results.append(Result(action, "ok", planned))

    archive_dir = root / "docs" / "ai" / "tasks" / "archive"
    for src in plan.mvs:
        action = Action("mv", src, "tasks/archive/")
        if not apply:
            results.append(Result(action, "ok", "planned"))
            continue
        target = archive_dir / src.name
        if target.exists():
            results.append(Result(action, "error", f"target exists: {target.name}"))
            continue
        archive_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(target))
        staged.append(src)
        staged.append(target)
        results.append(Result(action, "ok", "moved"))

    for kind, paths in (("rm_file", plan.rm_files), ("rm_dir", plan.rm_dirs)):
        for p in paths:
            action = Action(kind, p)
            if not apply:
                results.append(Result(action, "ok", "planned"))
                continue
            cmd_name = "kilo-safe-remove.cmd" if kind == "rm_file" else "kilo-safe-rmdir.cmd"
            cmd = ["cmd.exe", "/c", str(root / cmd_name), p.relative_to(root).as_posix()]
            code, out = runner(cmd)
            if code == 0:
                staged.append(p)
                results.append(Result(action, "ok", "deleted"))
            else:
                results.append(Result(action, "error", f"exit {code}: {out}"))

    if apply and staged and git_add is not None:
        staged_paths = sorted(set(staged), key=lambda p: p.as_posix())
        code, out = git_add(root, staged_paths)
        results.append(
            Result(
                Action("git_add", root, f"{len(staged_paths)} path(s)"),
                "ok" if code == 0 else "error",
                "staged" if code == 0 else f"exit {code}: {out}",
            )
        )

    return results


def format_report(plan: Plan, results: list[Result], applied: bool = False) -> str:
    lines = [f"root: {plan.root}", f"date: {plan.today}", ""]
    for n in plan.notes:
        lines.append(f"note: {n}")
    if not applied:
        intended = intended_staged_paths(plan)
        if intended:
            lines.append(f"note: git_add: would stage {len(intended)} path(s) on --apply")
    for r in results:
        try:
            rel = r.action.path.relative_to(plan.root).as_posix()
        except ValueError:
            rel = str(r.action.path)
        lines.append(f"{r.status.upper():5s} [{r.action.kind}] {rel} {r.action.detail} {r.message}".rstrip())
    errors = sum(1 for r in results if r.status == "error")
    if not results and not plan.notes:
        lines.append("no-op: nothing to do")
    lines.append(f"total: {len(results)} action(s), {errors} error(s)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Memory Bank batch cleanup (dry-run by default, --apply to run)."
    )
    parser.add_argument("--apply", action="store_true", help="apply the plan (default: dry-run)")
    parser.add_argument(
        "--no-git-add",
        action="store_true",
        help="with --apply: skip staging the touched paths (git add)",
    )
    parser.add_argument("--date", default=None, help="reference date YYYY-MM-DD (default: today)")
    parser.add_argument("--root", default=None, help="project root (default: repository root)")
    parser.add_argument(
        "--tmp-retention-days",
        type=int,
        default=TMP_RETENTION_DAYS,
        help=f"tmp/ retention period in days (default: {TMP_RETENTION_DAYS})",
    )
    args = parser.parse_args(argv)

    today = date.fromisoformat(args.date) if args.date else date.today()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent

    plan = build_plan(root, today, tmp_retention_days=args.tmp_retention_days)
    git_add = _default_git_add if (args.apply and not args.no_git_add) else None
    results = execute_plan(plan, apply=args.apply, git_add=git_add)
    print(format_report(plan, results, applied=args.apply))
    return 1 if any(r.status == "error" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
