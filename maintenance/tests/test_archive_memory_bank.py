import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import archive_memory_bank as amb  # noqa: E402

TODAY = date(2026, 10, 14)
CUTOFF = datetime(2026, 9, 30, 0, 0)
OLD = datetime(2026, 9, 1, 12, 0)
RECENT = datetime(2026, 10, 10, 9, 0)


def touch(root: Path, rel: str, content: str = "x") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def fake_stat(mtimes: dict[Path, datetime]):
    def _stat(path):
        p = Path(path)
        if p in mtimes:
            return SimpleNamespace(st_mtime=mtimes[p].timestamp())
        raise FileNotFoundError(p)

    return _stat


class FakeRunner:
    def __init__(self, root, fail_paths=()):
        self.calls = []
        self.fail_paths = set(fail_paths)
        self.root = Path(root)

    def __call__(self, cmd):
        self.calls.append(cmd)
        target = cmd[-1]
        if any(t in target for t in self.fail_paths):
            return 1, "simulated failure"
        # Simulate the effect of kilo-safe-remove / kilo-safe-rmdir
        p = self.root / target
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        else:
            p.unlink(missing_ok=True)
        return 0, "Deleted: " + target


def make_tree(tmp_path: Path) -> dict:
    ai = tmp_path / "docs" / "ai"
    ai.mkdir(parents=True)
    tsv = "\n".join([
        "task_file\tstatus\tnext_action",
        "docs/ai/tasks/2026-10-14-active.md\t進行中\tnext",
        "docs/ai/tasks/2026-09-01-done.md\t完了\tdone",
        "docs/ai/tasks/2026-09-01-paused.md\t中断\tpaused",
    ]) + "\n"
    (ai / "current-task.tsv").write_text(tsv, encoding="utf-8")

    touch(tmp_path, "docs/ai/tasks/2026-09-01-old.md")
    touch(tmp_path, "docs/ai/tasks/2026-09-01-old2.md")
    touch(tmp_path, "docs/ai/tasks/2026-10-14-active.md")
    touch(tmp_path, "docs/ai/tasks/2026-09-01-done.md")
    touch(tmp_path, "docs/ai/tasks/2026-09-01-paused.md")
    (ai / "tasks" / "archive").mkdir()

    feat = ai / "verification" / "feat-a"
    for name in ("run-old", "run-mid", "run-new1", "run-new2"):
        (feat / "runs" / name).mkdir(parents=True)
    (ai / "verification" / "feat-b").mkdir()

    touch(tmp_path, "docs/ai/tmp/f1.txt")
    touch(tmp_path, "docs/ai/tmp/.hidden")
    touch(tmp_path, "docs/ai/tmp/sub/inner.txt")
    touch(tmp_path, "docs/ai/tmp/old-sub/inner-old.txt")

    mtimes = {
        tmp_path / "docs/ai/tasks/2026-09-01-old.md": OLD,
        tmp_path / "docs/ai/tasks/2026-09-01-old2.md": OLD,
        tmp_path / "docs/ai/tasks/2026-10-14-active.md": RECENT,
        tmp_path / "docs/ai/tasks/2026-09-01-done.md": OLD,
        tmp_path / "docs/ai/tasks/2026-09-01-paused.md": OLD,
        feat / "runs/run-old": datetime(2026, 10, 1, 0, 0),
        feat / "runs/run-mid": datetime(2026, 10, 5, 0, 0),
        feat / "runs/run-new1": datetime(2026, 10, 10, 0, 0),
        feat / "runs/run-new2": datetime(2026, 10, 10, 0, 0),
        tmp_path / "docs/ai/tmp/f1.txt": RECENT,
        tmp_path / "docs/ai/tmp/.hidden": OLD,
        tmp_path / "docs/ai/tmp/sub": OLD,
        tmp_path / "docs/ai/tmp/sub/inner.txt": RECENT,
        tmp_path / "docs/ai/tmp/old-sub": OLD,
        tmp_path / "docs/ai/tmp/old-sub/inner-old.txt": OLD,
    }
    return {"tmp": tmp_path, "mtimes": mtimes}


def test_plan_tasks_mv_candidates_and_reference_set(tmp_path):
    ctx = make_tree(tmp_path)
    plan = amb.build_plan(tmp_path, TODAY, fake_stat(ctx["mtimes"]))
    assert [p.name for p in plan.mvs] == [
        "2026-09-01-done.md",
        "2026-09-01-old.md",
        "2026-09-01-old2.md",
        "2026-09-01-paused.md",
    ]


def test_plan_tsv_drops_completed_and_interrupted(tmp_path):
    ctx = make_tree(tmp_path)
    plan = amb.build_plan(tmp_path, TODAY, fake_stat(ctx["mtimes"]))
    assert len(plan.tsv_drops) == 2
    assert all("完了" in l or "中断" in l for l in plan.tsv_drops)


def test_plan_verification_keeps_two_newest_by_mtime(tmp_path):
    ctx = make_tree(tmp_path)
    plan = amb.build_plan(tmp_path, TODAY, fake_stat(ctx["mtimes"]))
    deleted = {p.name for p in plan.rm_dirs if "runs" in p.parts}
    assert deleted == {"run-mid", "run-old"}


def test_plan_verification_noop_when_two_or_fewer_runs(tmp_path):
    ctx = make_tree(tmp_path)
    (tmp_path / "docs/ai/verification/feat-a/runs/run-new2").rmdir()
    (tmp_path / "docs/ai/verification/feat-a/runs/run-new1").rmdir()
    plan = amb.build_plan(tmp_path, TODAY, fake_stat(ctx["mtimes"]))
    assert not [p for p in plan.rm_dirs if "runs" in p.parts]


def test_plan_tmp_files_and_dirs(tmp_path):
    ctx = make_tree(tmp_path)
    plan = amb.build_plan(tmp_path, TODAY, fake_stat(ctx["mtimes"]))
    assert [p.name for p in plan.rm_files] == [".hidden"]
    assert [p.name for p in plan.rm_dirs if "tmp" in p.parts] == ["old-sub"]
    assert not any(p.name == "sub" for p in plan.rm_dirs)
    assert any("tmp: keep (updated within 7d): f1.txt" in n for n in plan.notes)
    assert any("tmp: keep (updated within 7d): sub" in n for n in plan.notes)


def test_plan_tmp_dir_retained_when_nested_file_recent(tmp_path):
    ctx = make_tree(tmp_path)
    plan = amb.build_plan(tmp_path, TODAY, fake_stat(ctx["mtimes"]))
    assert tmp_path / "docs/ai/tmp/sub" not in plan.rm_dirs


def test_plan_tmp_retention_days_boundary(tmp_path):
    ctx = make_tree(tmp_path)
    f1 = tmp_path / "docs/ai/tmp/f1.txt"
    kept = amb.build_plan(tmp_path, TODAY, fake_stat(ctx["mtimes"]), tmp_retention_days=4)
    assert f1 not in kept.rm_files
    removed = amb.build_plan(tmp_path, TODAY, fake_stat(ctx["mtimes"]), tmp_retention_days=3)
    assert f1 in removed.rm_files


def test_tasks_boundary_mtmp(tmp_path):
    edge = touch(tmp_path, "docs/ai/tasks/2026-09-30-edge.md")
    plan = amb.build_plan(tmp_path, TODAY, fake_stat({edge: CUTOFF}))
    assert edge in plan.mvs

    edge2 = touch(tmp_path, "docs/ai/tasks/2026-09-30-edge2.md")
    plan2 = amb.build_plan(
        tmp_path, TODAY, fake_stat({edge: CUTOFF, edge2: CUTOFF + timedelta(seconds=1)})
    )
    assert edge in plan2.mvs
    assert edge2 not in plan2.mvs


def test_dry_run_no_side_effects(tmp_path):
    ctx = make_tree(tmp_path)
    runner = FakeRunner(tmp_path)
    plan = amb.build_plan(tmp_path, TODAY, fake_stat(ctx["mtimes"]))
    results = amb.execute_plan(plan, apply=False, runner=runner)
    assert all(r.status == "ok" for r in results)
    assert runner.calls == []
    assert (tmp_path / "docs/ai/tasks/2026-09-01-old.md").exists()
    assert (tmp_path / "docs/ai/verification/feat-a/runs/run-old").exists()
    assert (tmp_path / "docs/ai/tmp/f1.txt").exists()
    assert (tmp_path / "docs/ai/tmp/.hidden").exists()
    assert (tmp_path / "docs/ai/tmp/old-sub").exists()
    assert "完了" in (tmp_path / "docs/ai/current-task.tsv").read_text(encoding="utf-8")


def test_apply_moves_deletes_and_rewrites_tsv(tmp_path):
    ctx = make_tree(tmp_path)
    runner = FakeRunner(tmp_path)
    plan = amb.build_plan(tmp_path, TODAY, fake_stat(ctx["mtimes"]))
    results = amb.execute_plan(plan, apply=True, runner=runner)
    assert all(r.status == "ok" for r in results)

    archive = tmp_path / "docs/ai/tasks/archive"
    assert sorted(p.name for p in archive.glob("*.md")) == [
        "2026-09-01-done.md",
        "2026-09-01-old.md",
        "2026-09-01-old2.md",
        "2026-09-01-paused.md",
    ]
    assert not (tmp_path / "docs/ai/verification/feat-a/runs/run-old").exists()
    assert not (tmp_path / "docs/ai/verification/feat-a/runs/run-mid").exists()
    assert (tmp_path / "docs/ai/verification/feat-a/runs/run-new1").exists()
    assert (tmp_path / "docs/ai/tmp/f1.txt").exists()
    assert (tmp_path / "docs/ai/tmp/sub").exists()
    assert not (tmp_path / "docs/ai/tmp/.hidden").exists()
    assert not (tmp_path / "docs/ai/tmp/old-sub").exists()

    tsv_bytes = (tmp_path / "docs/ai/current-task.tsv").read_bytes()
    assert not tsv_bytes.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in tsv_bytes
    assert tsv_bytes.endswith(b"\n") and not tsv_bytes.endswith(b"\n\n")
    tsv_lines = tsv_bytes.decode("utf-8").splitlines()
    assert tsv_lines[0] == "task_file\tstatus\tnext_action"
    assert len(tsv_lines) == 2
    assert tsv_lines[1].startswith("docs/ai/tasks/2026-10-14-active.md")

    assert [c[-1] for c in runner.calls] == [
        "docs/ai/tmp/.hidden",
        "docs/ai/verification/feat-a/runs/run-mid",
        "docs/ai/verification/feat-a/runs/run-old",
        "docs/ai/tmp/old-sub",
    ]
    cmd_paths = [c[2] for c in runner.calls]
    assert cmd_paths.count(str(tmp_path / "kilo-safe-remove.cmd")) == 1
    assert cmd_paths.count(str(tmp_path / "kilo-safe-rmdir.cmd")) == 3
    assert all(c[0] == "cmd.exe" and c[1] == "/c" for c in runner.calls)


def test_apply_mv_collision_is_error_and_others_continue(tmp_path):
    ctx = make_tree(tmp_path)
    touch(tmp_path, "docs/ai/tasks/archive/2026-09-01-old.md", "existing")
    runner = FakeRunner(tmp_path)
    plan = amb.build_plan(tmp_path, TODAY, fake_stat(ctx["mtimes"]))
    results = amb.execute_plan(plan, apply=True, runner=runner)
    errors = [r for r in results if r.status == "error"]
    assert len(errors) == 1
    assert errors[0].action.path.name == "2026-09-01-old.md"
    assert (tmp_path / "docs/ai/tasks/archive/2026-09-01-old2.md").exists()
    assert (tmp_path / "docs/ai/tasks/2026-09-01-old.md").exists()


def test_runner_failure_isolated_per_item(tmp_path):
    ctx = make_tree(tmp_path)
    runner = FakeRunner(tmp_path, fail_paths={"runs/run-old"})
    plan = amb.build_plan(tmp_path, TODAY, fake_stat(ctx["mtimes"]))
    results = amb.execute_plan(plan, apply=True, runner=runner)
    errors = [r for r in results if r.status == "error"]
    assert len(errors) == 1
    assert errors[0].action.path.name == "run-old"
    assert any(r.action.path.name == "run-mid" and r.status == "ok" for r in results)


def test_cli_dry_run_no_side_effects(tmp_path, capsys):
    make_tree(tmp_path)
    rc = amb.main(["--root", str(tmp_path), "--date", "2026-10-14"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "date: 2026-10-14" in out
    assert "total: " in out
    tsv = (tmp_path / "docs/ai/current-task.tsv").read_text(encoding="utf-8")
    assert "完了" in tsv
    assert (tmp_path / "docs/ai/tmp/f1.txt").exists()
    assert (tmp_path / "docs/ai/tasks/2026-09-01-old.md").exists()


def test_cli_tmp_retention_days_flag(tmp_path, capsys):
    make_tree(tmp_path)
    rc = amb.main(
        ["--root", str(tmp_path), "--date", "2026-10-14", "--tmp-retention-days", "3"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "total: " in out


def test_cli_apply_exit_code_on_error(tmp_path, capsys, monkeypatch):
    make_tree(tmp_path)

    def failing_runner(cmd):
        return 1, "simulated failure"

    monkeypatch.setattr(amb, "_default_runner", failing_runner)
    rc = amb.main(["--root", str(tmp_path), "--date", "2026-10-14", "--apply"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "error" in out
