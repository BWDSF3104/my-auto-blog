"""VS Code再起動ワーカー（タスクスケジューラ一発タスクとして実行）。

VS Codeプロセスツリーの外（スケジューラ）から実行されるため、
VS Codeの正規クローズによるツリー殺害の影響を受けない。
Code.exeが全消したあと、指定ディレクトリでVS Codeを再起動する。
結果は docs/ai/tmp/vscode_relaunch_report.txt へ追記する（呼び出し元の shell は
VS Code クローズ時に殺されるため、失敗通知の受け口はここになる）。

標準ライブラリのみ。
"""

from __future__ import annotations

import datetime
import os
import shutil
import subprocess
import sys
import time

TASK_NAME = "my-auto-blog\\vscode-restart"
MAX_POLLS = 180
POLL_INTERVAL_SECONDS = 1
_CODE_INSTALL_DIRS = [
    r"C:\Program Files\Microsoft VS Code",
    r"C:\Program Files (x86)\Microsoft VS Code",
    r"D:\Program Files\Microsoft VS Code",
    r"D:\Program Files (x86)\Microsoft VS Code",
    r"E:\Program Files\Microsoft VS Code",
    r"E:\Program Files (x86)\Microsoft VS Code",
]


def _code_path() -> str:
    """console app を経由しない native 実行ファイルを優先（KI-20261028-01）。

    code.cmd（batch → cmd.exe）は交互セッションでコンソールウィンドウを作ると
    孤児化し得るため、`code` native（WindowsApps stub / bin\\code.exe）または
    `Code.exe` を優先し、`code.cmd` は native が無い場合のフォールバックのみ。
    """
    p = shutil.which("code")
    if p:
        if not p.lower().endswith(".cmd"):
            return p
        d = os.path.dirname(p)
        native = os.path.join(d, "code.exe")
        if os.path.exists(native):
            return native
        code_exe = os.path.join(os.path.dirname(d), "Code.exe")
        if os.path.exists(code_exe):
            return code_exe
        return p
    roots = list(_CODE_INSTALL_DIRS)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        roots.append(os.path.join(local, "Programs", "Microsoft VS Code"))
    program_data = os.environ.get("ProgramData")
    if program_data:
        roots.append(os.path.join(program_data, "Microsoft VS Code"))
    for d in roots:
        code_exe = os.path.join(d, "Code.exe")
        if os.path.exists(code_exe):
            return code_exe
        native = os.path.join(d, "bin", "code.exe")
        if os.path.exists(native):
            return native
        cmdp = os.path.join(d, "bin", "code.cmd")
        if os.path.exists(cmdp):
            return cmdp
    raise SystemExit("could not find VS Code 'code' executable")


def code_running() -> bool:
    """Code.exeプロセスが存在するかどうか。"""
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq Code.exe"], capture_output=True, text=True
    )
    return "Code.exe" in result.stdout


def wait_until_gone() -> bool:
    for _ in range(MAX_POLLS):
        if not code_running():
            return True
        time.sleep(POLL_INTERVAL_SECONDS)
    return False


def relaunch(cwd: str, code_path: str) -> bool:
    """DETACHED_PROCESS で VS Code を起動し、起動を確認。"""
    subprocess.Popen([code_path, cwd], creationflags=0x10)
    for _ in range(30):
        if code_running():
            return True
        time.sleep(2)
    return False


def cleanup_task() -> None:
    """実行済タスク定義を削除（ベストエフォート。失敗は無視）。"""
    subprocess.run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"], capture_output=True)


def report_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "docs", "ai", "tmp", "vscode_relaunch_report.txt"
    )


def already_ran(attempt: str) -> bool:
    """/Run 以外に ONCE トリガーでも再発動し得る（/Run はトリガーを消費しない）。同一 attempt の再実行は何もしない。"""
    if not attempt:
        return False
    path = report_path()
    if not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as fh:
            return f"attempt={attempt}" in fh.read()
    except OSError:
        return False


def report(message: str, attempt: str = "") -> None:
    """結果をスクラッチフォルダへ追記（実行シェルはクローズで殺されるため、ここが通知口になる）。"""
    path = report_path()
    prefix = f"attempt={attempt} " if attempt else ""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {prefix}{message}\n")
    except OSError:
        pass


def out(message: str) -> None:
    """pythonw（コンソールなし）では sys.stdout が None。書けないときはレポートファイルだけが通知口。"""
    if sys.stdout is not None:
        try:
            sys.stdout.write(f"{message}\n")
        except (OSError, ValueError):
            pass


def read_notify_target() -> str:
    """entry がスクラッチファイルへ書いた caller セッション ID を読む（KI-20261028-02）。"""
    path = os.path.join(os.path.dirname(report_path()), "vscode_relaunch_notify.txt")
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def notify(caller: str, message: str, attempt: str) -> None:
    """呼出し元セッションへ kilo CLI で follow-up を送る（best-effort、失敗はレポート行のみ）。

    capture_output=True は必須（redirected handles → console window が生成されない、KI-20261028-01）。
    local DB に存在するセッションのみ対象。追加ターンが1回発生する。
    """
    if not caller:
        return
    p = shutil.which("kilo")
    if not p:
        report(f"notify skipped: kilo CLI not found ({message})", attempt)
        return
    try:
        result = subprocess.run(
            [p, "run", "--session", caller, message],
            capture_output=True, timeout=60, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0:
            report(f"notify sent: {message}", attempt)
        else:
            report(f"notify failed (exit {result.returncode}): {(result.stderr or result.stdout).strip()}", attempt)
    except (OSError, subprocess.TimeoutExpired) as exc:
        report(f"notify failed: {exc}", attempt)


def main() -> int:
    if len(sys.argv) < 2:
        out("usage: vscode_relaunch_worker.py <cwd> [code_path] [attempt] [caller_session_id]")
        return 1
    cwd = sys.argv[1]
    code_path = sys.argv[2] if len(sys.argv) > 2 else _code_path()
    attempt = sys.argv[3] if len(sys.argv) > 3 else ""
    caller = sys.argv[4] if len(sys.argv) > 4 else read_notify_target()
    if caller:
        try:
            os.remove(os.path.join(os.path.dirname(report_path()), "vscode_relaunch_notify.txt"))
        except OSError:
            pass
    if already_ran(attempt):
        out(f"duplicate run for attempt={attempt}; nothing to do")
        return 0
    if not wait_until_gone():
        message = f"restart failed (attempt={attempt}): Code.exe still running after polling limit. manual restart needed"
        out(message)
        report(message, attempt)
        notify(caller, message, attempt)
        cleanup_task()
        return 2
    if not relaunch(cwd, code_path):
        message = f"restart failed (attempt={attempt}): relaunch not confirmed. manual restart needed"
        out(message)
        report(message, attempt)
        notify(caller, message, attempt)
        cleanup_task()
        return 2
    cleanup_task()
    message = f"restart complete (attempt={attempt})"
    out(message)
    report("success: VS Code relaunch complete", attempt)
    notify(caller, message, attempt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
