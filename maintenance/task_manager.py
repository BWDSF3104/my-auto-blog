"""AI Memory Bank タスク開始/終了ヘルパー (docs/ai/tasks + current-task.tsv).

Usage:
    python maintenance/task_manager.py add --slug short-name --title "タスク名" [--dry-run]
    python maintenance/task_manager.py end --task 2026-10-16-short-name [--dry-run]

Rules: docs/ai/memory-bank-guide.md
- add: タスクファイル骨架を作成 + current-task.tsv に参照行を追加
  (反映が既定、--dry-run でプレビューのみ。ファイル既存 / 重複行なら exit 1)
  + 開始前コンテキスト (working tree 状態 / 他タスクの進行中行 / backlog エントリ)
    と Agent 指示 (ガイド参照 / 他タスク確認 / 開始完了まで実着手しない) を出力する
    (読み取りのみ・非ブロッキング)
- end: タスクファイルの Status 行を「完了」へ更新 + tsv 参照行を削除
  + レポート (git status/diff --stat、未チェックの完了チェックリスト項目)。
- add/end とも、スクリプト自身が作成・変更したファイル (タスクファイル +
  current-task.tsv) は反映時に git add する (staging のみ)。--no-git-add で
  スキップ可能。staging 失敗は警告のみ (exit code はファイル操作の結果に依存)。
  git commit/push と、スクリプトが判断できない他ファイルの git add は
  workflows.md 手順でエージェントが担当。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass

TSV_RELPATH = Path("docs") / "ai" / "current-task.tsv"
TSV_HEADER = "task_file\tstatus\tnext_action"
TASKS_DIR = Path("docs") / "ai" / "tasks"
STATUS_IN_PROGRESS = "進行中"
STATUS_DONE_LINE = "**Status**: 完了"
STATUS_LINE_RE = re.compile(r"^\*\*Status\*\*:.*$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CHECKLIST_HEADING = "## 完了時 Memory Bank 操作"
UNCHECKED_RE = re.compile(r"^- \[ \] (.+)$")

# タスク終了時に変更される预期パス (end レポートで想定外ファイルを検知する)
EXPECTED_REPORT_PATHS = (
    "docs/ai/current-task.tsv",
    "docs/ai/backlog.md",
    "docs/ai/known-issues/",
)


class AmbiguousTaskError(Exception):
    """--task の解決結果が複数ファイルに該当した場合。"""

    def __init__(self, candidates: list[str]):
        super().__init__("ambiguous task")
        self.candidates = candidates


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def _tsv_path(root: Path) -> Path:
    return root / TSV_RELPATH


def _read_tsv(root: Path) -> list[str]:
    p = _tsv_path(root)
    if not p.is_file():
        return []
    return p.read_text(encoding="utf-8").splitlines()


def _write_tsv(root: Path, lines: list[str]) -> None:
    _tsv_path(root).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _tsv_task_files(root: Path) -> set[str]:
    files: set[str] = set()
    for line in _read_tsv(root)[1:]:
        if line:
            files.add(line.split("\t", 1)[0])
    return files


def build_skeleton(
    title: str,
    today: date,
    backlog: str | None,
    next_action: str | None,
) -> str:
    lines = [f"# {title}", ""]
    lines.append(f"**Status**: {STATUS_IN_PROGRESS}")
    lines.append(f"**Date**: {today.isoformat()}")
    if backlog:
        lines.append(f"**Backlog**: {backlog}")
    if next_action:
        lines.append(f"**Next Action**: {next_action}")
    lines.extend(
        [
            "",
            "## 意図 / 背景",
            "",
            "（記入）",
            "",
            "## 調査結果 / 変更内容",
            "",
            "（記入）",
            "",
            "## Verification",
            "",
            "（記入）",
            "",
            CHECKLIST_HEADING,
            "",
            "- [ ] `current-task.tsv` の参照行を削除",
            "- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）",
            "- [ ] `backlog.md` の完了項目を削除（該当する場合）",
            "",
        ]
    )
    return "\n".join(lines)


BACKLOG_REF_RE = re.compile(r"^P(\d+)\s*#(\d+)$")


def _backlog_entry(root: Path, ref: str) -> str | None:
    """'P<N> #<N>' に対応する backlog.md のテーブル行を返す (未発見は None)。"""
    m = BACKLOG_REF_RE.match(ref.strip())
    if not m:
        return None
    prio, num = m.group(1), m.group(2)
    p = root / "docs" / "ai" / "backlog.md"
    if not p.is_file():
        return None
    in_section = False
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_section = re.match(rf"^##\s+P{prio}\b", line) is not None
            continue
        if in_section:
            stripped = line.strip()
            if stripped.startswith(f"| {num} |"):
                return stripped
    return None


def _pre_start_context(root: Path, task_posix: str, args) -> tuple[list[str], int]:
    """開始前コンテキスト (working tree / 他タスクの進行中行 / backlog エントリ) を収集する。

    返り値は (出力行, 他タスクの進行中件数)。全て読み取りのみ・非ブロッキング。
    """
    lines: list[str] = []
    code, out = _git(root, "status", "--porcelain")
    if code != 0:
        lines.append(f"working tree: unknown (git status failed: {out})")
    elif not out:
        lines.append("working tree: clean")
    else:
        count = len(_porcelain_paths(out))
        lines.append(f"working tree: dirty ({count} path(s)):")
        lines.extend(f"  {line}" for line in out.splitlines())
        lines.append("note: confirm these are not leftovers from a previous task before starting")
    active_rows: list[str] = []
    for line in _read_tsv(root)[1:]:
        if not line:
            continue
        parts = line.split("\t")
        tf = parts[0]
        status = parts[1] if len(parts) > 1 else ""
        if tf == task_posix or status != STATUS_IN_PROGRESS:
            continue
        next_action = parts[2].strip() if len(parts) > 2 else ""
        active_rows.append(f"  {tf}" + (f" | {next_action}" if next_action else ""))
    if active_rows:
        lines.append(f"in-progress tasks: {len(active_rows)}")
        lines.extend(active_rows)
    else:
        lines.append("in-progress tasks: 0")
    if args.backlog:
        entry = _backlog_entry(root, args.backlog)
        if entry is None:
            lines.append(f"backlog: {args.backlog} (entry not found in backlog.md)")
        else:
            lines.append(f"backlog: {args.backlog}")
            lines.append(f"  {entry}")
    return lines, len(active_rows)


def _agent_instructions(active_count: int) -> list[str]:
    """タスク開始時の Agent 指示 (非ブロッキング・Agent が各項目を処理する)。"""
    lines = ["--- Agent 指示 ---"]
    n = 1
    lines.append(f"{n}. docs/ai/memory-bank-guide.md を参照（タスク開始ルール）")
    n += 1
    if active_count:
        lines.append(f"{n}. 他タスクが進行中 → ユーザーに並行継続 or 完了・保留を先に確認する")
        n += 1
    lines.append(f"{n}. タスクファイルの「意図 / 背景」を edit ツールで記入")
    n += 1
    lines.append(f"{n}. `python maintenance/archive_memory_bank.py` を実行（dry-run 確認後 `--apply`）")
    n += 1
    lines.append(f"{n}. タスク開始完了まで実装に着手しない")
    return lines


def cmd_add(args: argparse.Namespace) -> int:
    root: Path = args.root
    apply = not args.dry_run
    if not SLUG_RE.match(args.slug):
        return fail(
            f"invalid slug: {args.slug!r} "
            "(lowercase alphanumeric and hyphens only, e.g. task-slash-commands)"
        )
    today = date.today()
    task_path = root / TASKS_DIR / f"{today.isoformat()}-{args.slug}.md"
    task_posix = task_path.relative_to(root).as_posix()

    if task_path.exists():
        return fail(f"task file already exists: {task_posix}")
    if task_posix in _tsv_task_files(root):
        return fail(f"current-task.tsv already has a row for this task: {task_posix}")

    ctx_lines, active_count = _pre_start_context(root, task_posix, args)

    touched = [task_path, _tsv_path(root)]
    if apply:
        task_path.parent.mkdir(parents=True, exist_ok=True)
        task_path.write_text(
            build_skeleton(args.title, today, args.backlog, args.next_action),
            encoding="utf-8",
            newline="\n",
        )
        tsv_lines = _read_tsv(root) or [TSV_HEADER]
        tsv_lines.append(f"{task_posix}\t{STATUS_IN_PROGRESS}\t{args.next_action or ''}")
        _write_tsv(root, tsv_lines)

    note = _stage_note(root, touched, apply, args.no_git_add)
    print(
        "\n".join(
            [
                f"root: {root}",
                f"task file: {task_posix}",
                f"title: {args.title}",
                "applied" if apply else "planned (dry-run: no changes written)",
                note,
                "",
                "--- 開始前コンテキスト ---",
                *ctx_lines,
                "",
                *_agent_instructions(active_count),
            ]
        )
    )
    return 0


DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")


def _stem_matches(stem: str, value: str) -> bool:
    """ファイル名の slug 部（日付プレフィックス除外）をハイフン境界で照合する。

    完全一致 / "<値>-" プレフィックス / "-<値>" サフィックス のいずれかに一致すれば True。
    """
    if stem == value:
        return True
    short = DATE_PREFIX_RE.sub("", stem)
    return (
        short == value
        or short.endswith(f"-{value}")
        or short.startswith(f"{value}-")
    )


def resolve_task_file(root: Path, value: str) -> Path | None:
    """--task の値をタスクファイルに解決する。見つからなければ None、複数なら AmbiguousTaskError。

    解決順序:
    1. パス (root 相対/絶対) として実在 → 使用
    2. .md 終端 → docs/ai/tasks/ 内でファイル名完全一致
    3. それ以外 → slug 部 (日付プレフィックス除外) が値そのもの、
       または "<値>-" プレフィックス / "-<値>" サフィックス (ハイフン境界) の候補
    """
    raw = Path(value)
    candidate = raw if raw.is_absolute() else root / raw
    if candidate.is_file():
        return candidate

    tasks_dir = root / TASKS_DIR
    if not tasks_dir.is_dir():
        return None
    files = sorted(f for f in tasks_dir.glob("*.md") if f.is_file())
    name = raw.name
    if name.endswith(".md"):
        candidates = [f for f in files if f.name == name]
    else:
        candidates = [f for f in files if _stem_matches(f.stem, value)]
    if not candidates:
        return None
    if len(candidates) > 1:
        raise AmbiguousTaskError([f.relative_to(root).as_posix() for f in candidates])
    return candidates[0]


def _unchecked_items(lines: list[str]) -> list[str]:
    items: list[str] = []
    in_section = False
    for line in lines:
        if line.startswith("## "):
            in_section = line == CHECKLIST_HEADING
            continue
        if in_section:
            m = UNCHECKED_RE.match(line)
            if m:
                items.append(m.group(1))
    return items


def _git(root: Path, *git_args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", *git_args],
            cwd=root,
            capture_output=True,
            encoding="utf-8",
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1, "(git unavailable)"
    # 先頭スペース (porcelain の最初の行の XY ステータス) を壊さないよう末尾のみ除去する
    out = (proc.stdout or "").rstrip()
    if proc.returncode != 0 and not out:
        out = (proc.stderr or "").strip()
    return proc.returncode, out


def _porcelain_paths(status_out: str) -> list[str]:
    paths: list[str] = []
    for line in status_out.splitlines():
        if len(line) < 4:
            continue
        rest = line[3:]
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[0]
        paths.append(rest.strip())
    return paths


def git_report(root: Path, task_posix: str) -> list[str]:
    lines: list[str] = []
    code, out = _git(root, "status", "--porcelain")
    if code != 0:
        lines.append(f"git status: unavailable ({out})")
        return lines
    if not out:
        lines.append("git status: working tree clean")
    else:
        lines.append("git status --porcelain:")
        lines.extend(f"  {line}" for line in out.splitlines())
        unexpected = sorted(
            {
                p
                for p in _porcelain_paths(out)
                if p != task_posix
                and p not in EXPECTED_REPORT_PATHS
                and not p.startswith("docs/ai/known-issues/")
            }
        )
        if unexpected:
            lines.append("warning: files outside the expected list:")
            lines.extend(f"  ! {p}" for p in unexpected)
    for label, args in (
        ("git diff --stat (unstaged)", ("diff", "--stat")),
        ("git diff --cached --stat (staged)", ("diff", "--cached", "--stat")),
    ):
        code, out = _git(root, *args)
        lines.append("")
        lines.append(label)
        if code != 0:
            lines.append(f"  unavailable ({out})")
        elif out:
            lines.extend(f"  {line}" for line in out.splitlines())
        else:
            lines.append("  (none)")
    return lines


def _stage_note(root: Path, touched: list[Path], apply: bool, no_git_add: bool) -> str:
    """Report (and, on apply, perform) staging of the files this script touched."""
    if no_git_add:
        return "git add: skipped (--no-git-add)"
    if not apply:
        return f"git add: would stage {len(touched)} path(s) (dry-run)"
    rels = [p.relative_to(root).as_posix() for p in touched]
    code, out = _git(root, "add", "--", *rels)
    if code == 0:
        return f"git add: staged {len(touched)} path(s)"
    return f"git add: WARNING failed (exit {code}): {out}"


def cmd_end(args: argparse.Namespace) -> int:
    root: Path = args.root
    apply = not args.dry_run
    try:
        task_path = resolve_task_file(root, args.task)
    except AmbiguousTaskError as exc:
        return fail(
            "multiple task files matched, re-run with the full path: "
            + ", ".join(exc.candidates)
        )
    if task_path is None:
        return fail(f"task file not found: {args.task!r}")
    try:
        task_posix = task_path.relative_to(root).as_posix()
    except ValueError:
        return fail(f"task file is outside the project root: {task_path}")

    lines = task_path.read_text(encoding="utf-8").splitlines()
    status_idx = next(
        (i for i, line in enumerate(lines) if STATUS_LINE_RE.match(line)), None
    )
    if status_idx is None:
        return fail(f"Status line not found in {task_posix}")
    old_status = lines[status_idx]

    tsv_lines = _read_tsv(root)
    tsv_idx = next(
        (
            i
            for i, line in enumerate(tsv_lines[1:], start=1)
            if line.split("\t", 1)[0] == task_posix
        ),
        None,
    )

    touched = [task_path]
    if tsv_idx is not None:
        touched.append(_tsv_path(root))
    if apply:
        lines[status_idx] = STATUS_DONE_LINE
        task_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        if tsv_idx is not None:
            del tsv_lines[tsv_idx]
            _write_tsv(root, tsv_lines)

    note = _stage_note(root, touched, apply, args.no_git_add)
    report = [
        f"root: {root}",
        f"task file: {task_posix}",
        f"Status: {old_status} -> {STATUS_DONE_LINE}",
        "applied" if apply else "planned (dry-run: no changes written)",
        note,
    ]
    if tsv_idx is None:
        report.append("note: no row for this task in current-task.tsv (nothing to drop)")
    unchecked = _unchecked_items(lines)
    if unchecked:
        report.append("unchecked '完了時 Memory Bank 操作' items (agent performs these):")
        report.extend(f"  - {item}" for item in unchecked)
    elif CHECKLIST_HEADING not in lines:
        report.append("note: no '完了時 Memory Bank 操作' section found")
    report.append("")
    report.extend(git_report(root, task_posix))
    print("\n".join(report))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AI Memory Bank task start/end helper (apply by default, --dry-run to preview)."
    )
    parser.add_argument("--root", default=None, help="project root (default: repository root)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="create task file skeleton + add tsv row")
    p_add.add_argument("--slug", required=True, help="task short name (lowercase alphanumeric and hyphens)")
    p_add.add_argument("--title", required=True, help="task name (task file heading)")
    p_add.add_argument("--backlog", default=None, help='backlog reference (e.g. "P2 #17")')
    p_add.add_argument("--next-action", default=None, help="next action (tsv column + skeleton line)")
    p_add.add_argument("--dry-run", action="store_true", help="preview only, no changes written (default: apply)")
    p_add.add_argument(
        "--no-git-add",
        action="store_true",
        help="skip staging the touched files (git add)",
    )
    p_add.set_defaults(func=cmd_add)

    p_end = sub.add_parser("end", help="mark task done + drop tsv row + report")
    p_end.add_argument("--task", required=True, help="task file (path / date-slug / slug)")
    p_end.add_argument("--dry-run", action="store_true", help="preview only, no changes written (default: apply)")
    p_end.add_argument(
        "--no-git-add",
        action="store_true",
        help="skip staging the touched files (git add)",
    )
    p_end.set_defaults(func=cmd_end)

    args = parser.parse_args(argv)
    args.root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
