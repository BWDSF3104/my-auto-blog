"""maintenance/task_manager.py のテスト (tmp_path 使用・外部 API 呼び出しなし)。"""

import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import task_manager as tm  # noqa: E402

TSV_HEADER = "task_file\tstatus\tnext_action"
TODAY = date.today().isoformat()


def make_root(tmp_path: Path) -> Path:
    ai = tmp_path / "docs" / "ai"
    (ai / "tasks").mkdir(parents=True)
    (ai / "current-task.tsv").write_text(TSV_HEADER + "\n", encoding="utf-8")
    (ai / "backlog.md").write_text("# バックログ\n", encoding="utf-8")
    return tmp_path


def make_task_file(root: Path, slug: str, status: str = "進行中") -> Path:
    p = root / "docs" / "ai" / "tasks" / f"{TODAY}-{slug}.md"
    p.write_text(
        "\n".join(
            [
                f"# {slug}",
                "",
                f"**Status**: {status}",
                f"**Date**: {TODAY}",
                "",
                "## 意図 / 背景",
                "",
                "テストタスク",
                "",
                "## 完了時 Memory Bank 操作",
                "",
                "- [ ] `current-task.tsv` の参照行を削除",
                "- [ ] `backlog.md` の完了項目を削除（該当する場合）",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return p


def add_tsv_row(root: Path, task_file: str) -> None:
    tsv = root / "docs" / "ai" / "current-task.tsv"
    lines = tsv.read_text(encoding="utf-8").splitlines()
    lines.append(f"{task_file}\t進行中\tnext")
    tsv.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def add_ns(root: Path, **kw):
    base = {
        "root": root,
        "slug": "demo-task",
        "title": "デモタスク",
        "backlog": None,
        "next_action": None,
        "dry_run": False,
        "no_git_add": False,
    }
    base.update(kw)
    return SimpleNamespace(**base)


def end_ns(root: Path, task: str, dry_run: bool = False, no_git_add: bool = False):
    return SimpleNamespace(root=root, task=task, dry_run=dry_run, no_git_add=no_git_add)


def ok_git(root, *args):
    return 0, ""


def fake_git(root, *args):
    if args[:2] == ("status", "--porcelain"):
        return 0, " M docs/ai/backlog.md\n?? docs/ai/stray-file.md"
    if args[:3] == ("diff", "--stat",):
        return 0, " docs/ai/backlog.md | 1 +\n 1 file changed, 1 insertion(+)"
    return 0, ""


def test_add_apply_creates_file_and_tsv_row(tmp_path, monkeypatch):
    root = make_root(tmp_path)
    monkeypatch.setattr(tm, "_git", ok_git)
    rc = tm.cmd_add(add_ns(root))
    assert rc == 0
    task_file = root / "docs" / "ai" / "tasks" / f"{TODAY}-demo-task.md"
    assert task_file.is_file()
    text = task_file.read_text(encoding="utf-8")
    assert "# デモタスク" in text
    assert "**Status**: 進行中" in text
    assert f"**Date**: {TODAY}" in text
    assert "## 完了時 Memory Bank 操作" in text
    lines = (root / "docs" / "ai" / "current-task.tsv").read_text(encoding="utf-8").splitlines()
    assert lines[-1] == f"docs/ai/tasks/{TODAY}-demo-task.md\t進行中\t"


def test_add_dry_run_writes_nothing(tmp_path, monkeypatch):
    root = make_root(tmp_path)
    monkeypatch.setattr(tm, "_git", ok_git)
    rc = tm.cmd_add(add_ns(root, dry_run=True))
    assert rc == 0
    assert not (root / "docs" / "ai" / "tasks" / f"{TODAY}-demo-task.md").exists()
    lines = (root / "docs" / "ai" / "current-task.tsv").read_text(encoding="utf-8").splitlines()
    assert lines == [TSV_HEADER]


def test_add_existing_file_errors(tmp_path):
    root = make_root(tmp_path)
    make_task_file(root, "demo-task")
    rc = tm.cmd_add(add_ns(root))
    assert rc == 1


def test_add_duplicate_tsv_row_errors(tmp_path):
    root = make_root(tmp_path)
    add_tsv_row(root, f"docs/ai/tasks/{TODAY}-demo-task.md")
    rc = tm.cmd_add(add_ns(root))
    assert rc == 1


def test_add_invalid_slug_errors(tmp_path, monkeypatch):
    root = make_root(tmp_path)
    monkeypatch.setattr(tm, "_git", ok_git)
    assert tm.cmd_add(add_ns(root, slug="Bad Slug!")) == 1
    assert tm.cmd_add(add_ns(root, slug="trailing-")) == 1
    assert tm.cmd_add(add_ns(root, slug="9-ok", dry_run=True)) == 0


def test_add_backlog_and_next_action(tmp_path, monkeypatch):
    root = make_root(tmp_path)
    monkeypatch.setattr(tm, "_git", ok_git)
    rc = tm.cmd_add(add_ns(root, backlog="P2 #17", next_action="設計確認"))
    assert rc == 0
    text = (root / "docs" / "ai" / "tasks" / f"{TODAY}-demo-task.md").read_text(encoding="utf-8")
    assert "**Backlog**: P2 #17" in text
    assert "**Next Action**: 設計確認" in text
    lines = (root / "docs" / "ai" / "current-task.tsv").read_text(encoding="utf-8").splitlines()
    assert lines[-1] == f"docs/ai/tasks/{TODAY}-demo-task.md\t進行中\t設計確認"


def test_add_apply_stages_task_file_and_tsv(tmp_path, capsys, monkeypatch):
    root = make_root(tmp_path)
    calls = []

    def rec_git(r, *args):
        calls.append(args)
        return 0, ""

    monkeypatch.setattr(tm, "_git", rec_git)
    rc = tm.cmd_add(add_ns(root))
    assert rc == 0
    assert calls == [
        ("status", "--porcelain"),
        ("add", "--", f"docs/ai/tasks/{TODAY}-demo-task.md", "docs/ai/current-task.tsv"),
    ]
    assert "git add: staged 2 path(s)" in capsys.readouterr().out


def test_add_no_git_add_skips_staging(tmp_path, capsys, monkeypatch):
    root = make_root(tmp_path)
    calls = []

    def rec_git(r, *args):
        calls.append(args)
        return 0, ""

    monkeypatch.setattr(tm, "_git", rec_git)
    rc = tm.cmd_add(add_ns(root, no_git_add=True))
    assert rc == 0
    assert calls == [("status", "--porcelain")]
    assert "git add: skipped (--no-git-add)" in capsys.readouterr().out
    assert (root / "docs" / "ai" / "tasks" / f"{TODAY}-demo-task.md").is_file()


def test_add_stage_failure_is_warning_not_fatal(tmp_path, capsys, monkeypatch):
    root = make_root(tmp_path)

    def boom_git(r, *args):
        if args[:1] == ("add",):
            return 1, "boom"
        return 0, ""

    monkeypatch.setattr(tm, "_git", boom_git)
    rc = tm.cmd_add(add_ns(root))
    assert rc == 0
    assert (root / "docs" / "ai" / "tasks" / f"{TODAY}-demo-task.md").is_file()
    assert "git add: WARNING failed (exit 1): boom" in capsys.readouterr().out


def test_add_pre_context_clean_tree_and_no_active_tasks(tmp_path, capsys, monkeypatch):
    root = make_root(tmp_path)
    monkeypatch.setattr(tm, "_git", ok_git)
    rc = tm.cmd_add(add_ns(root))
    assert rc == 0
    out = capsys.readouterr().out
    assert "--- 開始前コンテキスト ---" in out
    assert "working tree: clean" in out
    assert "in-progress tasks: 0" in out
    assert "--- Agent 指示 ---" in out
    assert "docs/ai/memory-bank-guide.md" in out
    assert "タスク開始完了まで実装に着手しない" in out


def test_add_pre_context_lists_other_in_progress_tasks(tmp_path, capsys, monkeypatch):
    root = make_root(tmp_path)
    add_tsv_row(root, f"docs/ai/tasks/{TODAY}-other-task.md")
    monkeypatch.setattr(tm, "_git", ok_git)
    rc = tm.cmd_add(add_ns(root))
    assert rc == 0
    out = capsys.readouterr().out
    assert "in-progress tasks: 1" in out
    assert f"  docs/ai/tasks/{TODAY}-other-task.md | next" in out
    assert "ユーザーに並行継続 or 完了・保留を先に確認する" in out


def test_add_pre_context_dirty_tree_warns(tmp_path, capsys, monkeypatch):
    root = make_root(tmp_path)
    monkeypatch.setattr(tm, "_git", fake_git)
    rc = tm.cmd_add(add_ns(root))
    assert rc == 0
    out = capsys.readouterr().out
    assert "working tree: dirty (2 path(s)):" in out
    assert "  M docs/ai/backlog.md" in out
    assert "  ?? docs/ai/stray-file.md" in out
    assert "confirm these are not leftovers from a previous task before starting" in out


def test_add_pre_context_git_unavailable_is_unknown(tmp_path, capsys, monkeypatch):
    root = make_root(tmp_path)
    monkeypatch.setattr(tm, "_git", lambda r, *a: (128, "not a git repository"))
    rc = tm.cmd_add(add_ns(root))
    assert rc == 0
    out = capsys.readouterr().out
    assert "working tree: unknown (git status failed: not a git repository)" in out


def test_add_pre_context_prints_backlog_entry(tmp_path, capsys, monkeypatch):
    root = make_root(tmp_path)
    (root / "docs" / "ai" / "backlog.md").write_text(
        "\n".join(
            [
                "# Backlog",
                "",
                "## P2",
                "",
                "| # | 項目 |",
                "|---|------|",
                "| 17 | 新プロンプトタイプ「ポケモン」追加 |",
                "",
                "## P3",
                "",
                "| # | 項目 |",
                "|---|------|",
                "| 17 | 同号の別項目 |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(tm, "_git", ok_git)
    rc = tm.cmd_add(add_ns(root, backlog="P2 #17"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "backlog: P2 #17" in out
    assert "| 17 | 新プロンプトタイプ「ポケモン」追加 |" in out
    assert "同号の別項目" not in out


def test_add_pre_context_backlog_entry_missing_warns(tmp_path, capsys, monkeypatch):
    root = make_root(tmp_path)
    monkeypatch.setattr(tm, "_git", ok_git)
    rc = tm.cmd_add(add_ns(root, backlog="P9 #99"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "backlog: P9 #99 (entry not found in backlog.md)" in out


def test_end_apply_updates_status_and_drops_row(tmp_path, monkeypatch, capsys):
    root = make_root(tmp_path)
    task_file = make_task_file(root, "demo-task")
    add_tsv_row(root, f"docs/ai/tasks/{TODAY}-demo-task.md")
    monkeypatch.setattr(tm, "_git", fake_git)

    rc = tm.cmd_end(end_ns(root, "demo-task"))
    assert rc == 0

    text = task_file.read_text(encoding="utf-8")
    assert "**Status**: 完了" in text
    assert "**Status**: 進行中" not in text
    lines = (root / "docs" / "ai" / "current-task.tsv").read_text(encoding="utf-8").splitlines()
    assert lines == [TSV_HEADER]

    out = capsys.readouterr().out
    assert f"Status: **Status**: 進行中 -> **Status**: 完了" in out
    assert "applied" in out
    assert "unchecked '完了時 Memory Bank 操作' items" in out
    assert "warning: files outside the expected list" in out
    assert "docs/ai/stray-file.md" in out
    assert "git diff --stat (unstaged)" in out
    assert "git diff --cached --stat (staged)" in out


def test_end_dry_run_writes_nothing(tmp_path, monkeypatch, capsys):
    root = make_root(tmp_path)
    task_file = make_task_file(root, "demo-task")
    add_tsv_row(root, f"docs/ai/tasks/{TODAY}-demo-task.md")
    monkeypatch.setattr(tm, "_git", fake_git)

    rc = tm.cmd_end(end_ns(root, "demo-task", dry_run=True))
    assert rc == 0

    assert "**Status**: 進行中" in task_file.read_text(encoding="utf-8")
    lines = (root / "docs" / "ai" / "current-task.tsv").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert "planned (dry-run" in capsys.readouterr().out


def test_end_resolves_date_slug_and_path(tmp_path, monkeypatch):
    root = make_root(tmp_path)
    make_task_file(root, "demo-task")
    monkeypatch.setattr(tm, "_git", fake_git)

    assert tm.cmd_end(end_ns(root, f"{TODAY}-demo-task")) == 0
    assert tm.cmd_end(end_ns(root, f"docs/ai/tasks/{TODAY}-demo-task.md")) == 0
    assert tm.cmd_end(end_ns(root, f"{TODAY}-demo-task.md")) == 0


def test_end_ambiguous_slug_lists_candidates(tmp_path, capsys):
    root = make_root(tmp_path)
    make_task_file(root, "task-a")
    make_task_file(root, "task-b")
    rc = tm.cmd_end(end_ns(root, "task"))
    assert rc == 1
    err = capsys.readouterr().err
    assert f"docs/ai/tasks/{TODAY}-task-a.md" in err
    assert f"docs/ai/tasks/{TODAY}-task-b.md" in err


def test_end_not_found_errors(tmp_path):
    root = make_root(tmp_path)
    assert tm.cmd_end(end_ns(root, "no-such-task")) == 1


def test_end_missing_status_line_errors(tmp_path, monkeypatch):
    root = make_root(tmp_path)
    p = root / "docs" / "ai" / "tasks" / f"{TODAY}-plain.md"
    p.write_text("# 見出しのみ\n\n本文\n", encoding="utf-8")
    monkeypatch.setattr(tm, "_git", fake_git)
    assert tm.cmd_end(end_ns(root, "plain")) == 1


def test_end_no_tsv_row_is_note_only(tmp_path, monkeypatch, capsys):
    root = make_root(tmp_path)
    make_task_file(root, "demo-task")
    monkeypatch.setattr(tm, "_git", fake_git)

    rc = tm.cmd_end(end_ns(root, "demo-task"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "no row for this task in current-task.tsv" in out
    assert "git add: staged 1 path(s)" in out


def test_end_already_done_is_idempotent(tmp_path, monkeypatch):
    root = make_root(tmp_path)
    make_task_file(root, "demo-task", status="完了")
    monkeypatch.setattr(tm, "_git", fake_git)
    rc = tm.cmd_end(end_ns(root, "demo-task"))
    assert rc == 0
    text = (root / "docs" / "ai" / "tasks" / f"{TODAY}-demo-task.md").read_text(encoding="utf-8")
    assert text.count("**Status**: 完了") == 1


def test_end_apply_stages_task_file_and_tsv(tmp_path, capsys, monkeypatch):
    root = make_root(tmp_path)
    make_task_file(root, "demo-task")
    add_tsv_row(root, f"docs/ai/tasks/{TODAY}-demo-task.md")
    calls = []

    def rec_git(r, *args):
        calls.append(args)
        return 0, ""

    monkeypatch.setattr(tm, "_git", rec_git)
    rc = tm.cmd_end(end_ns(root, "demo-task"))
    assert rc == 0
    add_calls = [c for c in calls if c[:1] == ("add",)]
    assert add_calls == [
        ("add", "--", f"docs/ai/tasks/{TODAY}-demo-task.md", "docs/ai/current-task.tsv")
    ]
    assert "git add: staged 2 path(s)" in capsys.readouterr().out


def test_end_no_git_add_skips_staging(tmp_path, capsys, monkeypatch):
    root = make_root(tmp_path)
    make_task_file(root, "demo-task")
    add_tsv_row(root, f"docs/ai/tasks/{TODAY}-demo-task.md")
    calls = []

    def rec_git(r, *args):
        calls.append(args)
        return 0, ""

    monkeypatch.setattr(tm, "_git", rec_git)
    rc = tm.cmd_end(end_ns(root, "demo-task", no_git_add=True))
    assert rc == 0
    assert [c for c in calls if c[:1] == ("add",)] == []
    assert "git add: skipped (--no-git-add)" in capsys.readouterr().out


def test_end_stage_failure_is_warning_not_fatal(tmp_path, capsys, monkeypatch):
    root = make_root(tmp_path)
    task_file = make_task_file(root, "demo-task")
    add_tsv_row(root, f"docs/ai/tasks/{TODAY}-demo-task.md")

    def boom_git(r, *args):
        if args[:1] == ("add",):
            return 1, "boom"
        return 0, ""

    monkeypatch.setattr(tm, "_git", boom_git)
    rc = tm.cmd_end(end_ns(root, "demo-task"))
    assert rc == 0
    assert "**Status**: 完了" in task_file.read_text(encoding="utf-8")
    assert "git add: WARNING failed (exit 1): boom" in capsys.readouterr().out


def test_git_keeps_leading_space_of_first_line(tmp_path, monkeypatch):
    class FakeProc:
        returncode = 0
        stdout = " M AGENTS.md\n M docs/ai/backlog.md\n"
        stderr = ""

    monkeypatch.setattr(
        tm.subprocess, "run", lambda *a, **kw: FakeProc()
    )
    code, out = tm._git(tmp_path, "status", "--porcelain")
    assert code == 0
    assert out == " M AGENTS.md\n M docs/ai/backlog.md"
    assert tm._porcelain_paths(out) == ["AGENTS.md", "docs/ai/backlog.md"]


def test_git_report_clean_tree(tmp_path, monkeypatch):
    def clean_git(root, *args):
        return 0, ""

    monkeypatch.setattr(tm, "_git", clean_git)
    report = tm.git_report(tmp_path, "docs/ai/tasks/x.md")
    assert report[0] == "git status: working tree clean"
    assert "  (none)" in report
