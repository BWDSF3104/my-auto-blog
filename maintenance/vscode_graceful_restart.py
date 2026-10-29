"""VS Code (Code.exe) の正規クローズ＋再起動。

強制終了（taskkill等）は使用しない:
- クローズ: Code.exe の可視 Electron メインウィンドウへ WM_CLOSE 送信（ユーザーが X 押すのと同じ）
- 再起動: 一発タスク（タスクスケジューラ）に委譲。
  理由: バッチは VS Code プロセスツリーの shell 内を走るため、
  正規クローズ時にツリーが殺害され再発動まで届かない恐れがある
  （kilo.exe は Code.exe 子プロセスの child、bash シェルは kilo の子）。

クローズ判定は SendMessageW の返り値では行わない。返り値は窓プロックの返り値で、
正常処理後も DefWindowProc は 0 を返すため失敗と区別できない。送信後のウィンドウ
消失で判定する（この shell を抱えるウィンドウが閉じると本スクリプトも殺されるため、
判定はベストエフォート。実際の再起動確認はワーカー側が行う）。

インテグリティ（UAC 権限）がターゲットより低いと UIPI が WM_CLOSE をフィルタする。
実行シェルとターゲットウィンドウのインテグリティが一致している必要がある。

バッチ実行（restart-vscode.bat）はコンソールウィンドウを残さないため execute モードで
`start /b pythonw` を使う（KI-20261028-01）。pythonw では stdout がないので、
出力（log）はレポートファイル `docs/ai/tmp/vscode_relaunch_report.txt` へ書き、
stdout が使える環境では表示もする。

使い方:
    python vscode_graceful_restart.py <cwd>
    python vscode_graceful_restart.py --dry-run <cwd>
    python vscode_graceful_restart.py --self-test <cwd>

終了コード: 0 成功 / 1 ウィンドウなし / 2 失敗 / 3 インテグリティ不一致（UIPI）またはシェル非昇格
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
MAIN_WINDOW_CLASS = "chrome_widgetwin_1"
CLOSE_VERIFY_SECONDS = 15
INTEGRITY_NAMES = {0x1000: "Low", 0x2000: "Medium", 0x3000: "High", 0x4000: "System"}
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TOKEN_INTEGRITY_LEVEL_CLASS = 25
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

user32 = ctypes.WinDLL("user32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

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
user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.SendMessageW.argtypes = [
    ctypes.c_void_p,
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_long,
]
user32.SendMessageW.restype = wintypes.BOOL

advapi32.OpenProcessToken.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.HANDLE),
]
advapi32.OpenProcessToken.restype = wintypes.BOOL
advapi32.GetTokenInformation.argtypes = [
    wintypes.HANDLE,
    ctypes.c_int,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
advapi32.GetTokenInformation.restype = wintypes.BOOL
advapi32.GetSidSubAuthority.argtypes = [ctypes.c_void_p, wintypes.DWORD]
advapi32.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)
advapi32.GetSidSubAuthorityCount.argtypes = [ctypes.c_void_p]
advapi32.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL


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


def is_main_window(window_class: str, visible: bool) -> bool:
    """可視の Electron メインウィンドウのみがクローズ対象（helper の Chrome_WidgetWin_0 は閉じない）。"""
    return window_class.lower() == MAIN_WINDOW_CLASS and visible


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
    """code.exe が持つ可視 Electron メインウィンドウ（Chrome_WidgetWin_1）を特定。"""
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
        if not is_main_window(_window_class(hwnd), bool(user32.IsWindowVisible(hwnd))):
            return True
        found.append({
            "hwnd": hwnd,
            "pid": pid_value.value,
            "title": _window_title(hwnd),
            "visible": True,
        })
        return True

    cb = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,
        ctypes.c_void_p,
    )(_callback)
    user32.EnumWindows(cb, None, None)
    return found


def integrity_name(value: int | None) -> str:
    if value is None:
        return "unknown"
    return INTEGRITY_NAMES.get(value, f"0x{value:04x}")


def integrity_mismatch(own: int | None, target: int | None) -> bool:
    """ターゲットが実行シェルより高インテグリティなら UIPI が WM_CLOSE をフィルタする。"""
    return own is not None and target is not None and target > own


def needs_elevation(own: int | None) -> bool:
    """/RL HIGHEST のタスク登録には昇格トークンが必要（非昇格シェルでは Access denied）。"""
    return own is not None and own < 0x3000


def _read_sid(buffer: ctypes.Array[ctypes.c_char]) -> int | None:
    """GetTokenInformation のバッファはクラス固有構造そのもの（x64 では PSID が offset 0）。"""
    return ctypes.cast(ctypes.byref(buffer), ctypes.POINTER(ctypes.c_void_p))[0]


def _integrity_from_token(handle: wintypes.HANDLE) -> int | None:
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(handle, TOKEN_QUERY, ctypes.byref(token)):
        return None
    try:
        buffer = ctypes.create_string_buffer(1024)
        size = wintypes.DWORD()
        if not advapi32.GetTokenInformation(
            token, TOKEN_INTEGRITY_LEVEL_CLASS, buffer, len(buffer), ctypes.byref(size)
        ):
            return None
        sid = _read_sid(buffer)
        if not sid:
            return None
        count = advapi32.GetSidSubAuthorityCount(ctypes.c_void_p(sid))
        if not count:
            return None
        sub = advapi32.GetSidSubAuthority(ctypes.c_void_p(sid), count[0] - 1)
        return sub[0] if sub else None
    finally:
        kernel32.CloseHandle(token)


def own_integrity_level() -> int | None:
    return _integrity_from_token(kernel32.GetCurrentProcess())


def process_integrity_level(pid: int) -> int | None:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        return _integrity_from_token(handle)
    finally:
        kernel32.CloseHandle(handle)


def report_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "docs", "ai", "tmp", "vscode_relaunch_report.txt"
    )


def log(message: str) -> None:
    """stdout が使える場合は表示し、常にレポートファイルへ追記（pythonw 起動の通知口）。"""
    if sys.stdout is not None:
        try:
            print(message)
        except (OSError, ValueError):
            pass
    try:
        os.makedirs(os.path.dirname(report_path()), exist_ok=True)
        with open(report_path(), "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} entry: {message}\n")
    except (OSError, ValueError):
        pass


def print_integrity(windows: list[dict]) -> None:
    own = own_integrity_level()
    log(f"shell integrity: {integrity_name(own)}")
    for pid in sorted({w["pid"] for w in windows}):
        log(f"  pid={pid} integrity={integrity_name(process_integrity_level(pid))}")


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


def _interpreter_path() -> str:
    """タスク行動には pythonw を使う（GUI subsystem → コンソールウィンドウを作らない）。"""
    py = _python_path()
    gui = os.path.join(os.path.dirname(py), "pythonw.exe")
    return gui if os.path.exists(gui) else py


def _worker_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "vscode_relaunch_worker.py")


def _quote_cmd(arg: str) -> str:
    if " " in arg:
        return f'"{arg}"'
    return arg


def notify_target_path() -> str:
    """caller セッション ID の受け渡し先（スクラッチファイル）。

    `/TR` の 255 文字上限（KI-20261028-02）でセッション ID を埋め込めないため、
    entry がここへ書き、worker が読む。
    """
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "docs", "ai", "tmp", "vscode_relaunch_notify.txt"
    )


def write_notify_target(caller: str) -> None:
    path = notify_target_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"{caller}\n")
    except OSError as exc:
        log(f"notify target not written ({exc}); worker notify will be skipped")


def task_command_line(cwd: str, code_path: str, attempt: str) -> str:
    """タスク action。cmd.exe を経由しない（console app は交互セッションでウィンドウを作る）。

    caller（呼出し元セッション ID）は TR に埋めずスクラッチファイルで受け渡す
    （KI-20261028-02）。notify が無い場合 worker の notify はスキップされ、
    レポートファイルのみが通知口になる。
    """
    parts = [_quote_cmd(_interpreter_path()), _quote_cmd(_worker_path()), _quote_cmd(cwd), _quote_cmd(code_path), _quote_cmd(attempt)]
    return " ".join(parts)


def schedule_relaunch(cwd: str, attempt: str) -> None:
    """一発タスクを作成し即時実行。/Run が失敗しても次分でのバックストップがある。

    `/RL HIGHEST` は必須: 既定（Limited）で登録すると worker が非昇格トークンで
    Code.exe を起動し、再起動後のインスタンスが昇格しない。
    """
    code = _code_path()
    task_tr = task_command_line(cwd, code, attempt)
    if len(task_tr) > 255:
        log(f"schtasks /Create skipped: /TR would be {len(task_tr)} chars (limit 255, KI-20261028-02)")
        sys.exit(2)
    # バックストップはワーカーの最大実行時間(約4分)を余裕をもって上回らせる。
    st = (datetime.datetime.now() + datetime.timedelta(minutes=5)).strftime("%H:%M")
    subprocess.run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"], capture_output=True)
    create = subprocess.run(
        ["schtasks", "/Create", "/TN", TASK_NAME, "/TR", task_tr, "/SC", "ONCE", "/ST", st, "/RL", "HIGHEST"],
        capture_output=True,
        text=True,
    )
    if create.returncode != 0:
        detail = (create.stderr or create.stdout).strip()
        log(f"schtasks /Create failed: {detail}")
        log("/RL HIGHEST requires an elevated shell (run from the elevated VS Code instance)")
        sys.exit(2)
    run = subprocess.run(["schtasks", "/Run", "/TN", TASK_NAME], capture_output=True, text=True)
    if run.returncode != 0:
        log(
            "warning: schtasks /Run failed ("
            f"{(run.stderr or run.stdout).strip()}). relaunch will be done by the scheduled trigger (next minute)")


def _launch_code(code_path: str, cwd: str) -> None:
    """DETACHED_PROCESS で VS Code を起動（バックグラウンド、非ブロッキング）。"""
    subprocess.Popen([code_path, cwd], creationflags=0x10)


def close_and_verify(windows: list[dict], timeout: int = CLOSE_VERIFY_SECONDS) -> bool:
    """WM_CLOSE 送信後、ウィンドウ消失で判定する（返り値では判定しない）。

    この shell を抱えるウィンドウが閉じた瞬間に本スクリプトも殺されるため、
    判定はベストエフォートで、実際の再起動確認はワーカー（180 秒）が行う。
    """
    own = own_integrity_level()
    for w in windows:
        user32.SendMessageW(w["hwnd"], WM_CLOSE, 0, 0)
        log(f"WM_CLOSE sent: hwnd=0x{w['hwnd']:x} pid={w['pid']}")

    remaining = {w["hwnd"] for w in windows}
    deadline = time.time() + timeout
    while remaining and time.time() < deadline:
        present = {w["hwnd"] for w in find_code_windows()}
        remaining = {h for h in remaining if h in present}
        if not remaining:
            break
        time.sleep(1)

    if remaining:
        log(
            f"not closed within {timeout}s: {sorted(hex(h) for h in remaining)} "
            "- UIPI filter or a save dialog may be blocking. manual restart may be needed")
        if own is not None and any(integrity_mismatch(own, process_integrity_level(w["pid"])) for w in windows):
            log("hint: target window integrity is higher than this shell")
        return False
    log(f"all target windows closed within {timeout}s")
    return True


def _repo_root() -> str:
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


CANONICAL_BIN = r"S:\Documents\Kilo_Commons\Common_Operations\bin"


def _canonical_rmdir_ps1() -> str:
    """正典 bin の safe-rmdir.ps1 を解決（PATH > script フォルダ > 既定定数）。"""
    found = shutil.which("kilo-safe-rmdir.cmd")
    base = os.path.dirname(found) if found else CANONICAL_BIN
    return os.path.join(base, "safe-rmdir.ps1")


def cleanup_scratch(scratch: str) -> None:
    """scratch フォルダを Windows ゴミ箱へ（恒久削除ではない）。

    cmd.exe を経由しない（console app を経路に入れない → ウィンドウを生成しない、
    KI-20261028-01）。正典（Kilo_Commons bin）の `safe-rmdir.ps1` を powershell へ直接呼出。
    cwd をプロジェクトルートにすることで、正典のルート判定チェーンが
    `.git` からこのプロジェクトを正しく解決する。
    """
    root = _repo_root()
    ps1 = _canonical_rmdir_ps1()
    if not os.path.exists(ps1):
        log("scratch left in place (canonical safe-rmdir.ps1 not found)")
        return
    rel = os.path.relpath(scratch, root).replace("\\", "/")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1, rel],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=root,
    )
    log(f"scratch cleanup: {result.stdout.strip() or f'exit {result.returncode}'}")


def self_test(cwd: str) -> int:
    """検証: scratch フォルダで VS Code 新規可視ウィンドウを起動し、WM_CLOSE で正規クローズ。

    単一インスタンス環境では `code <path>` は可視ウィンドウを作らず既存ウィンドウを
    フォーカスするだけ（不可視 helper が増えてカウントだけ増える）ため `-n` を使う。
    """
    code = _code_path()
    scratch = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "ai", "tmp", "vscode_selftest")
    )
    os.makedirs(scratch, exist_ok=True)
    before = {w["hwnd"] for w in find_code_windows()}
    before_count = len(before)
    own = own_integrity_level()
    log(f"shell integrity: {integrity_name(own)}")
    _launch_code(code, scratch)
    new = None
    for _ in range(30):
        cur = [w for w in find_code_windows() if w["hwnd"] not in before]
        if cur:
            new = cur[0]
            break
        time.sleep(1)
    if new is None:
        log("no new visible window created (scratch folder must be a new folder)")
        return 2
    log(f"new visible window: hwnd=0x{new['hwnd']:x} pid={new['pid']} title={new['title']!r}")
    if integrity_mismatch(own, process_integrity_level(new["pid"])):
        log("UIPI: target window integrity is higher than this shell")
        return 3
    user32.SendMessageW(new["hwnd"], WM_CLOSE, 0, 0)
    for _ in range(30):
        if new["hwnd"] not in {w["hwnd"] for w in find_code_windows()}:
            log(f"self-test complete: scratch window closed normally (scratch={scratch})")
            cleanup_scratch(scratch)
            return 0
        time.sleep(1)
    log("new window did not close within 30 seconds")
    return 2


def extract_notify_session(args: list[str]) -> tuple[list[str], str]:
    """args から --notify-session <sessionID> を抽出（cwd の前後どちらでも可）。"""
    caller = ""
    rest: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--notify-session" and i + 1 < len(args):
            caller = args[i + 1]
            i += 2
        else:
            rest.append(args[i])
            i += 1
    return rest, caller


def main(argv: list[str]) -> int:
    # stdout がパイプ（cp932）で捕捉される実行環境では、タイトル内の文字（例 '◔'）が
    # UnicodeEncodeError を起こして schedule 前にクラッシュする。エスケープ表示へフォールバック。
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    args, caller = extract_notify_session(list(argv[1:]))
    mode = "run"
    if not args:
        log("usage: vscode_graceful_restart.py [--dry-run | --self-test] [--notify-session <sessionID>] <cwd>")
        return 1
    if args[0] == "--dry-run":
        mode = "dry-run"
        args = args[1:]
    elif args[0] == "--self-test":
        mode = "self-test"
        args = args[1:]
    if not args:
        log("usage: vscode_graceful_restart.py [--dry-run | --self-test] [--notify-session <sessionID>] <cwd>")
        return 1
    cwd = os.path.abspath(args[0])
    windows = find_code_windows()
    log(f"found Code.exe visible main windows: {len(windows)}")
    for w in windows:
        log(f"  hwnd=0x{w['hwnd']:x} pid={w['pid']} title={w['title']!r}")
    if not windows and mode != "self-test":
        log("no visible main window; helper windows are not closable by WM_CLOSE")
    if mode == "dry-run":
        print_integrity(windows)
        log(f"python: {_python_path()}")
        log(f"interpreter (task action): {_interpreter_path()}")
        log(f"worker: {_worker_path()}")
        log("dry-run complete (no changes)")
        return 0
    if mode == "self-test":
        return self_test(cwd)
    print_integrity(windows)
    own = own_integrity_level()
    if needs_elevation(own):
        log(
            f"shell is not elevated (integrity={integrity_name(own)}). "
            "Run from the elevated VS Code instance: /RL HIGHEST cannot be registered "
            "from a non-elevated shell, and the relaunch would not be admin.")
        return 3
    if not windows:
        log("Code.exe not running; worker will relaunch")
    else:
        blocked = [w for w in windows if integrity_mismatch(own, process_integrity_level(w["pid"]))]
        if blocked:
            log(
                "UIPI: target window integrity is higher than this shell. "
                "WM_CLOSE will be filtered. Run from a shell with the same integrity "
                "(VS Code must be launched elevated and the agent shell must match).")
            return 3

    # The relaunch task MUST be scheduled BEFORE the close. The worker runs
    # in the task scheduler (independent of VS Code); scheduling it first
    # guarantees it is already waiting even if this shell is killed when
    # VS Code closes.
    if caller:
        write_notify_target(caller)
    schedule_relaunch(cwd, datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    log("relaunch task scheduled; worker waiting for VS Code to close")
    if not windows:
        log(f"relaunch delegated to scheduled task {TASK_NAME}; VS Code should reopen in about 5-10 seconds")
        return 0
    log("this shell will be killed when its own window closes. "
          f"worker ({TASK_NAME}) is the authoritative verifier")
    return 0 if close_and_verify(windows) else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
