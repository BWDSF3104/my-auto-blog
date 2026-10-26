"""VS Code (Code.exe) の正規クローズ＋再起動。

強制終了（taskkill等）は使用しない:
- クローズ: Code.exe メインウィンドウへ WM_CLOSE 送信（ユーザーが X 押すのと同じ）
- 再起動: 一発タスク（タスクスケジューラ）に委譲。
  理由: バッチは VS Code プロセスツリーの shell 内を走るため、
  正規クローズ時にツリーが殺害され再発動まで届かない恐れがある
  （kilo.exe は Code.exe 子プロセスの child、bash シェルは kilo の子）。

使い方:
    python vscode_graceful_restart.py <cwd>
    python vscode_graceful_restart.py --dry-run <cwd>
    python vscode_graceful_restart.py --self-test <cwd>

終了コード: 0 成功 / 1 ウィンドウなし / 2 失敗
"""

from __future__ import annotations

import ctypes
import datetime
import os
import shutil
import subprocess
import sys
import time
from ctypes import wintypes

TASK_NAME = "my-auto-blog\\vscode-restart"
WM_CLOSE = 0x0010
MAIN_WINDOW_CLASSES = frozenset({"chrome_widgetwin_0", "chrome_widgetwin_1"})
_CODE_BIN_DIRS = [
    r"C:\Program Files\Microsoft VS Code\bin",
    r"C:\Program Files (x86)\Microsoft VS Code\bin",
    r"D:\Program Files\Microsoft VS Code\bin",
    r"D:\Program Files (x86)\Microsoft VS Code\bin",
    r"E:\Program Files\Microsoft VS Code\bin",
    r"E:\Program Files (x86)\Microsoft VS Code\bin",
]

user32 = ctypes.WinDLL("user32", use_last_error=True)

user32.GetWindowThreadProcessId.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_ulong),
]
user32.GetWindowThreadProcessId.restype = wintypes.BOOL
user32.EnumWindows.restype = wintypes.BOOL
user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(wintypes.WCHAR),
    ctypes.c_int,
]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(wintypes.WCHAR),
    ctypes.c_int,
]
user32.GetClassNameW.restype = ctypes.c_int
user32.SendMessageW.argtypes = [
    ctypes.c_void_p,
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_long,
]
user32.SendMessageW.restype = wintypes.BOOL


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


def _window_title(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _window_class(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buffer, 256)
    return buffer.value


def _code_exe_pids() -> set[int]:
    """tasklist (/FO CSV) で code.exe の PID 集合を取得。"""
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq Code.exe", "/FO", "CSV"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        return set()
    pids: set[int] = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        fields = line.split(",")
        if len(fields) >= 2:
            try:
                pid = int(fields[1].strip().strip('"'))
            except ValueError:
                continue
            pids.add(pid)
    return pids


def find_code_windows() -> list[dict]:
    """code.exe が持つ Electron メインウィンドウ（Chrome_WidgetWin_0/1）を特定。"""
    code_pids = _code_exe_pids()
    if not code_pids:
        return []
    found: list[dict] = []

    def _callback(hwnd: int, lpparam: object) -> bool:
        pid_value = ctypes.c_ulong()
        if not user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_value)):
            return True
        if pid_value.value not in code_pids:
            return True
        cls = _window_class(hwnd).lower()
        if cls not in MAIN_WINDOW_CLASSES:
            return True
        found.append({"hwnd": hwnd, "pid": pid_value.value, "title": _window_title(hwnd)})
        return True

    cb = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,
        ctypes.c_void_p,
    )(_callback)
    user32.EnumWindows(cb, None, None)
    return found


def send_close(hwnd: int) -> bool:
    return user32.SendMessageW(hwnd, WM_CLOSE, 0, 0)


def pid_running(pid: int) -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True
    )
    return str(pid) in result.stdout


def _python_path() -> str:
    path = shutil.which("python")
    if not path:
        raise SystemExit("python not found on PATH")
    return path


def _worker_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "vscode_relaunch_worker.py")


def _quote_cmd(arg: str) -> str:
    if " " in arg:
        return f'"{arg}"'
    return arg


def schedule_relaunch(cwd: str) -> None:
    """一発タスクを作成し即時実行。/Run が失敗しても次分でのバックストップがある。"""
    code = _code_path()
    task_tr = " ".join(
        [_quote_cmd("cmd"), "/c", _quote_cmd(_python_path()), _quote_cmd(_worker_path()), _quote_cmd(cwd), _quote_cmd(code)]
    )
    # バックストップはワーカーの最大実行時間(約4分)を余裕をもって上回らせる。
    st = (datetime.datetime.now() + datetime.timedelta(minutes=5)).strftime("%H:%M")
    subprocess.run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"], capture_output=True)
    create = subprocess.run(
        ["schtasks", "/Create", "/TN", TASK_NAME, "/TR", task_tr, "/SC", "ONCE", "/ST", st],
        capture_output=True,
        text=True,
    )
    if create.returncode != 0:
        detail = (create.stderr or create.stdout).strip()
        print(f"schtasks /Create failed: {detail}", file=sys.stderr)
        sys.exit(2)
    run = subprocess.run(["schtasks", "/Run", "/TN", TASK_NAME], capture_output=True, text=True)
    if run.returncode != 0:
        print(
            "warning: schtasks /Run failed ("
            f"{(run.stderr or run.stdout).strip()}). relaunch will be done by the scheduled trigger (next minute)",
            file=sys.stderr,
        )


def _launch_code(code_path: str, cwd: str) -> None:
    """DETACHED_PROCESS で VS Code を起動（バックグラウンド、非ブロッキング）。"""
    subprocess.Popen([code_path, cwd], creationflags=0x10)


def self_test(cwd: str) -> int:
    """検証: scratch フォルダで VS Code 新規ウィンドウを起動し、WM_CLOSE で正規クローズ。

    既に開かれているフォルダへ起動すると既存ウィンドウのフォーカスになり
    新規ウィンドウが作られず、スクラッチフォルダを使う。
    """
    code = _code_path()
    scratch = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "ai", "tmp", "vscode_selftest")
    )
    os.makedirs(scratch, exist_ok=True)
    before = {w["hwnd"] for w in find_code_windows()}
    before_count = len(before)
    _launch_code(code, scratch)
    for _ in range(30):
        if len(find_code_windows()) > before_count:
            break
        time.sleep(1)
    for _ in range(30):
        cur = find_code_windows()
        for w in cur:
            if w["hwnd"] not in before:
                send_close(w["hwnd"])
        if len(cur) <= before_count:
            break
        time.sleep(1)
    if len(find_code_windows()) > before_count:
        print("new window did not close within 30 seconds", file=sys.stderr)
        return 2
    print(f"self-test complete: scratch window closed normally (scratch={scratch})")
    return 0


def main(argv: list[str]) -> int:
    args = list(argv[1:])
    mode = "run"
    if not args:
        print("usage: vscode_graceful_restart.py [--dry-run | --self-test] <cwd>", file=sys.stderr)
        return 1
    if args[0] == "--dry-run":
        mode = "dry-run"
        args = args[1:]
    elif args[0] == "--self-test":
        mode = "self-test"
        args = args[1:]
    if not args:
        print("usage: vscode_graceful_restart.py [--dry-run | --self-test] <cwd>", file=sys.stderr)
        return 1
    cwd = os.path.abspath(args[0])
    windows = find_code_windows()
    print(f"found Code.exe main windows: {len(windows)}")
    for w in windows:
        print(f"  hwnd=0x{w['hwnd']:x} pid={w['pid']} title={w['title']!r}")
    if mode == "dry-run":
        print(f"python: {_python_path()}")
        print(f"worker: {_worker_path()}")
        print("dry-run complete (no changes)")
        return 0
    if mode == "self-test":
        return self_test(cwd)
    # The relaunch task MUST be scheduled BEFORE the close. The worker runs
    # in the task scheduler (independent of VS Code); scheduling it first
    # guarantees it is already waiting even if this shell is killed when
    # VS Code closes.
    schedule_relaunch(cwd)
    print(f"relaunch task scheduled; worker waiting for VS Code to close")
    if windows:
        sent = all(send_close(w["hwnd"]) for w in windows)
        if not sent:
            print("warning: WM_CLOSE failed for some window, continuing", file=sys.stderr)
        print("close requested")
    else:
        print("Code.exe not running; worker will relaunch")
    print(f"relaunch delegated to scheduled task {TASK_NAME}; VS Code should reopen in about 5-10 seconds")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
