import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

if os.name != "nt":
    pytest.skip("vscode_graceful_restart is Windows-only", allow_module_level=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import vscode_graceful_restart as g  # noqa: E402
import vscode_relaunch_worker as w  # noqa: E402


def test_only_visible_electron_window_is_target():
    assert g.is_main_window("Chrome_WidgetWin_1", True)
    assert g.is_main_window("chrome_widgetwin_1", True)
    assert not g.is_main_window("Chrome_WidgetWin_0", True)
    assert not g.is_main_window("Chrome_WidgetWin_1", False)
    assert not g.is_main_window("IME", True)


def test_integrity_mismatch_only_when_target_higher():
    medium = 0x2000
    high = 0x3000
    assert g.integrity_mismatch(medium, high)
    assert not g.integrity_mismatch(high, medium)
    assert not g.integrity_mismatch(high, high)
    assert not g.integrity_mismatch(None, high)
    assert not g.integrity_mismatch(high, None)


def test_integrity_name_maps_levels():
    assert g.integrity_name(0x3000) == "High"
    assert g.integrity_name(0x2000) == "Medium"
    assert g.integrity_name(None) == "unknown"


def test_needs_elevation_only_for_non_elevated_shell():
    assert g.needs_elevation(0x2000)
    assert not g.needs_elevation(0x3000)
    assert not g.needs_elevation(0x4000)
    assert not g.needs_elevation(None)


def test_interpreter_prefers_gui_subsystem(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "_python_path", lambda: str(tmp_path / "python.exe"))
    assert g._interpreter_path() == str(tmp_path / "python.exe")
    (tmp_path / "pythonw.exe").write_text("x", encoding="utf-8")
    assert g._interpreter_path() == str(tmp_path / "pythonw.exe")


def test_task_action_does_not_go_through_console_app(tmp_path, monkeypatch):
    action = str(tmp_path / "pythonw.exe")
    worker = str(tmp_path / "my worker.py")
    monkeypatch.setattr(g, "_python_path", lambda: action)
    monkeypatch.setattr(g, "_worker_path", lambda: worker)
    tr = g.task_command_line("C:\\cwd dir", "C:\\code.cmd", "a1")
    assert not tr.startswith("cmd ")
    assert tr.startswith(action)
    assert f'"{worker}"' in tr
    assert '"C:\\cwd dir"' in tr


def test_out_survives_missing_stdout(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    w.out("no console")


def test_duplicate_attempt_guard(tmp_path, monkeypatch):
    monkeypatch.setattr(w, "report_path", lambda: str(tmp_path / "report.txt"))
    assert not w.already_ran("a1")
    w.report("success", "a1")
    assert w.already_ran("a1")
    assert not w.already_ran("a2")
    assert not w.already_ran("")


def test_log_writes_to_report_without_stdout(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(g, "report_path", lambda: str(tmp_path / "report.txt"))
    g.log("entry line")
    assert "entry line" in (tmp_path / "report.txt").read_text(encoding="utf-8")


def test_log_survives_unwritable_report(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(g, "report_path", lambda: "\x00invalid")
    g.log("x")


def test_execute_mode_uses_detached_pythonw_in_bat():
    bat = Path(__file__).resolve().parents[1] / "restart-vscode.bat"
    assert 'start "" /b pythonw' in bat.read_text(encoding="utf-8")


def test_code_path_prefers_native_over_cmd(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "code.cmd").write_text("x", encoding="utf-8")
    (bin_dir / "code.exe").write_text("x", encoding="utf-8")
    monkeypatch.setattr(shutil, "which", lambda name: str(bin_dir / "code.cmd"))
    assert g._code_path() == str(bin_dir / "code.exe")
    assert w._code_path() == str(bin_dir / "code.exe")


def test_code_path_falls_back_to_install_root_code_exe(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "code.cmd").write_text("x", encoding="utf-8")
    (tmp_path / "Code.exe").write_text("x", encoding="utf-8")
    monkeypatch.setattr(shutil, "which", lambda name: str(bin_dir / "code.cmd"))
    assert g._code_path() == str(tmp_path / "Code.exe")
    assert w._code_path() == str(tmp_path / "Code.exe")


def test_extract_notify_session():
    rest, caller = g.extract_notify_session(["--dry-run", "C:\\cwd", "--notify-session", "ses_x"])
    assert rest == ["--dry-run", "C:\\cwd"]
    assert caller == "ses_x"
    rest, caller = g.extract_notify_session(["C:\\cwd"])
    assert caller == ""


def test_task_command_line_excludes_caller(tmp_path, monkeypatch):
    # KI-20261028-02: /TR は 255 文字上限。caller は TR に埋めずファイルで受け渡す。
    monkeypatch.setattr(g, "_python_path", lambda: str(tmp_path / "python.exe"))
    monkeypatch.setattr(g, "_worker_path", lambda: str(tmp_path / "worker.py"))
    tr = g.task_command_line("C:\\cwd", "C:\\Code.exe", "a1")
    assert tr.endswith("a1")
    assert "ses_" not in tr
    assert len(tr) <= 255


def test_notify_target_handoff(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "notify_target_path", lambda: str(tmp_path / "vscode_relaunch_notify.txt"))
    monkeypatch.setattr(w, "report_path", lambda: str(tmp_path / "report.txt"))
    g.write_notify_target("ses_x")
    assert w.read_notify_target() == "ses_x"


def test_notify_skips_when_kilo_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(w, "report_path", lambda: str(tmp_path / "report.txt"))
    monkeypatch.setattr(shutil, "which", lambda name: None)
    w.notify("ses_x", "msg", "a1")
    assert "notify skipped" in (tmp_path / "report.txt").read_text(encoding="utf-8")


def test_notify_sends_via_kilo_run(tmp_path, monkeypatch):
    monkeypatch.setattr(w, "report_path", lambda: str(tmp_path / "report.txt"))
    monkeypatch.setattr(shutil, "which", lambda name: "kilo")
    calls = []

    class FakeResult:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, *args, **kwargs):
        calls.append((cmd, kwargs))
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)
    w.notify("ses_x", "restart complete", "a1")
    assert calls[0][0] == ["kilo", "run", "--session", "ses_x", "restart complete"]
    assert calls[0][1].get("capture_output") is True
    assert calls[0][1].get("creationflags") == subprocess.CREATE_NO_WINDOW
    assert "notify sent" in (tmp_path / "report.txt").read_text(encoding="utf-8")


def test_worker_notifies_on_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(w, "report_path", lambda: str(tmp_path / "report.txt"))
    monkeypatch.setattr(w, "wait_until_gone", lambda: False)
    monkeypatch.setattr(w, "cleanup_task", lambda: None)
    monkeypatch.setattr(shutil, "which", lambda name: "kilo")

    class FakeResult:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda cmd, *args, **kwargs: FakeResult())
    monkeypatch.setattr(sys, "argv", ["prog", "C:\\cwd", "C:\\Code.exe", "a1", "ses_x"])
    assert w.main() == 2
    text = (tmp_path / "report.txt").read_text(encoding="utf-8")
    assert "restart failed (attempt=a1)" in text
    assert "notify sent" in text


def test_cleanup_scratch_uses_canonical_bin_directly(tmp_path, monkeypatch):
    calls = []
    captured_kwargs = {}

    class FakeResult:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        captured_kwargs.update(kwargs)
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)
    # Simulate the canonical bin on PATH so the resolver returns this folder.
    monkeypatch.setattr(shutil, "which", lambda name: str(tmp_path / name))
    monkeypatch.setattr(g, "_repo_root", lambda: str(tmp_path))
    monkeypatch.setattr(g, "report_path", lambda: str(tmp_path / "report.txt"))
    monkeypatch.setattr(sys, "stdout", None)
    ps1 = tmp_path / "safe-rmdir.ps1"
    ps1.write_text("x", encoding="utf-8")
    g.cleanup_scratch(str(tmp_path / "docs" / "ai" / "tmp" / "scratch"))
    assert calls and calls[0][0] == "powershell.exe"
    assert "cmd.exe" not in calls[0]
    # Direct call to the canonical ps1, cwd = project root (so the canonical
    # tool's .git walk-up resolves this project).
    assert calls[0][5] == str(ps1)
    assert captured_kwargs.get("cwd") == str(tmp_path)
