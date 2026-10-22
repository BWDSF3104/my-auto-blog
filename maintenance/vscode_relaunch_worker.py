"""VS Code再起動ワーカー（タスクスケジューラ一発タスクとして実行）。

VS Codeプロセスツリーの外（スケジューラ）から実行されるため、
VS Codeの正規クローズによるツリー殺害の影響を受けない。
Code.exeが全消したあと、指定ディレクトリでVS Codeを再起動する。

標準ライブラリのみ。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time

TASK_NAME = "my-auto-blog\\vscode-restart"
MAX_POLLS = 180
POLL_INTERVAL_SECONDS = 1
_CODE_BIN_DIRS = [
    r"C:\Program Files\Microsoft VS Code\bin",
    r"C:\Program Files (x86)\Microsoft VS Code\bin",
    r"D:\Program Files\Microsoft VS Code\bin",
    r"D:\Program Files (x86)\Microsoft VS Code\bin",
    r"E:\Program Files\Microsoft VS Code\bin",
    r"E:\Program Files (x86)\Microsoft VS Code\bin",
]


def _code_path() -> str:
    """コードコマンド実行ファイル（code.cmd を優先）のパスを特定。"""
    p = shutil.which("code")
    if p:
        d = os.path.dirname(p)
        for name in ("code.cmd", "code"):
            c = os.path.join(d, name)
            if os.path.exists(c):
                return c
        return p
    env = os.environ
    dirs = list(_CODE_BIN_DIRS)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        dirs.append(os.path.join(local, "Programs", "Microsoft VS Code", "bin"))
    program_data = os.environ.get("ProgramData")
    if program_data:
        dirs.append(os.path.join(program_data, "Microsoft VS Code", "bin"))
    for d in dirs:
        for name in ("code.cmd", "code"):
            c = os.path.join(d, name)
            if os.path.exists(c):
                return c
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


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: vscode_relaunch_worker.py <cwd> [code_path]", file=sys.stderr)
        return 1
    cwd = sys.argv[1]
    code_path = sys.argv[2] if len(sys.argv) > 2 else _code_path()
    if not wait_until_gone():
        print(
            "polling limit reached: Code.exe still running "
            "(possible save dialog, etc.)",
            file=sys.stderr,
        )
        cleanup_task()
        return 2
    if not relaunch(cwd, code_path):
        print("failed to confirm VS Code relaunch", file=sys.stderr)
        cleanup_task()
        return 2
    cleanup_task()
    print("VS Code relaunch complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
