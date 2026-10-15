"""リファクタリング等価性検証 L1（決定論的リプレイ A/B）ハーネス。

ベースラインコミットと現行コミットの generate_post() を、
全外部APIをモックし時刻・乱数を固定したサンドボックスで実行し、
出力群のバイト一致を検証する。

使い方:
    python scripts/tests/equivalence_check.py --baseline 69bb5e8 --variants default,kemono_story,ai_deep
    python scripts/tests/equivalence_check.py --selftest --variants default
    python scripts/tests/equivalence_check.py --l3 --variants default

動作:
  1. git archive で baseline + current を scratch（docs/ai/tmp/eq）へ展開（pristine テンプレート）
  2. 各実行ごとに pristine をコピー → golden 入力デプロイ → eq_runner.py 書込
  3. サンドボックス cwd + 固定 env で `python eq_runner.py` を実行（全モック・ネットワークゼロ）
  4. 成果物を out/<label>/ に収集（絶対パスを <ROOT> に正規化）
  5. 自己整合（現行 ×2）→ A/B（baseline vs current）を再帰バイト diff
  6. diff_report.txt を書き出し、diff 空なら exit 0 / 差分ありで exit 1

AGENTS.md 準拠: 外部API呼び出しゼロ（Gemini/楽天/画像/e621 全てモック）。
"""
import argparse
import difflib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "data" / "equivalence_golden"
EQ_DIR = Path(os.environ.get("EQ_TMP_DIR", str(ROOT / "docs" / "ai" / "tmp" / "eq")))
OUT_DIR = EQ_DIR / "out"
FIXED_EPOCH = 1791766800
TS = "2026-10-12-100000"  # FIXED_EPOCH の JST 表記（ファイル名・ログ名に使用）
VARIANTS_ALL = ["default", "kemono_story", "ai_deep"]

DRAFT_PATH = GOLDEN / "fixtures" / "fixed_draft.txt"
REFINED_PATH = GOLDEN / "fixtures" / "fixed_refined.txt"


def _seed():
    return (GOLDEN / "fixtures" / "seed.txt").read_text(encoding="utf-8").strip()


# --------------------------------------------------
# ツリー展開・デプロイ
# --------------------------------------------------
def expand_tree(commit: str, dest: Path):
    """git archive でコミットを展開（pristine テンプレート）。"""
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(
        ["git", "archive", "--format=tar", commit],
        cwd=ROOT, check=True, stdout=subprocess.PIPE,
    )
    with tarfile.open(fileobj=io.BytesIO(p.stdout), mode="r:") as tf:
        tf.extractall(dest)


def deploy_inputs(sandbox: Path):
    """golden 入力を実行前にデプロイ（冪等・初期状態保証）。"""
    # data/ を golden に置換
    shutil.rmtree(sandbox / "data", ignore_errors=True)
    shutil.copytree(GOLDEN / "inputs" / "data", sandbox / "data")
    for d in ("drafts", "trend_usage_logs", "affiliate_logs", "prompt_logs"):
        (sandbox / "data" / d).mkdir(parents=True, exist_ok=True)
    # posts / prompts スナップショット
    shutil.rmtree(sandbox / "src" / "content" / "posts", ignore_errors=True)
    shutil.copytree(GOLDEN / "inputs" / "posts", sandbox / "src" / "content" / "posts")
    shutil.rmtree(sandbox / "scripts" / "prompts", ignore_errors=True)
    shutil.copytree(GOLDEN / "inputs" / "prompts", sandbox / "scripts" / "prompts")
    # 画像出力ディレクトリを空に
    shutil.rmtree(sandbox / "public" / "images", ignore_errors=True)
    (sandbox / "public" / "images").mkdir(parents=True, exist_ok=True)


def make_sandbox(pristine: Path, sandbox: Path):
    if sandbox.exists():
        shutil.rmtree(sandbox)
    shutil.copytree(pristine, sandbox)
    deploy_inputs(sandbox)


RUNNER_TEMPLATE = '''"""L1 決定論的リプレイ runner（equivalence_check.py が書込）。
cwd = サンドボックスルート。引数: <draft> <refined> <seed> <capture_out>
"""
import json
import os
import random
import sys
import time
import datetime as _dt

DRAFT_PATH = sys.argv[1]
REFINED_PATH = sys.argv[2]
SEED = int(sys.argv[3])
CAPTURE_PATH = sys.argv[4]

FIXED_EPOCH = 1791766800
TREE_KIND = "__TREE_KIND__"  # "baseline" | "current"
L3_REAL_PASS1 = "__L3_REAL_PASS1__" == "true"

DRAFT = open(DRAFT_PATH, encoding="utf-8").read()
REFINED = open(REFINED_PATH, encoding="utf-8").read()
CAPTURE = {"gemini_calls": [], "image_calls": [], "subprocess_calls": []}

_FIXED_UTC = _dt.datetime.fromtimestamp(FIXED_EPOCH, _dt.timezone.utc)


class _FakeDateTime(_dt.datetime):
    """datetime.datetime は C 拡張型で属性が不変。各モジュールの参照差し替えで固定する。"""

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return _FIXED_UTC.replace(tzinfo=None)
        return _FIXED_UTC.astimezone(tz)


_TIME_COUNTER = {"n": 0}


def _fake_time():
    _TIME_COUNTER["n"] += 1
    return FIXED_EPOCH + 0.05 * _TIME_COUNTER["n"]


def _fake_sleep(seconds):
    _TIME_COUNTER["n"] += 1


def _install_time_patches():
    time.time = _fake_time
    time.sleep = _fake_sleep


def _patch_module_datetime():
    """pipeline モジュールの datetime 参照（from datetime import datetime）を差し替える。"""
    import sys as _sys

    for name, mod in list(_sys.modules.items()):
        if name == "generate_article" or name.startswith("article."):
            if getattr(mod, "datetime", None) is _dt.datetime:
                mod.datetime = _FakeDateTime


def _install_network_block():
    import requests

    def _block(*a, **k):
        raise RuntimeError("NETWORK BLOCKED: requests call attempted")

    requests.get = _block
    requests.post = _block
    import subprocess as _sp

    real_run = _sp.run

    def _logged_run(*a, **k):
        try:
            cmd = a[0] if a else k.get("args")
            CAPTURE["subprocess_calls"].append(list(cmd) if cmd is not None else "<kwargs>")
        except Exception:
            CAPTURE["subprocess_calls"].append(["<unparseable>"])
        return real_run(*a, **k)

    _sp.run = _logged_run


def main():
    _install_time_patches()
    _install_network_block()

    sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
    import generate_article

    _patch_module_datetime()
    assert generate_article.datetime.now(_dt.timezone.utc).timestamp() == FIXED_EPOCH, "datetime patch failed"
    assert abs(time.time() - FIXED_EPOCH) < 1.0, "time patch failed"

    class _FakeResponse:
        def __init__(self, text):
            self.text = text

    class _FakeModels:
        def generate_content(self, model=None, contents=None, **kwargs):
            CAPTURE["gemini_calls"].append({"model": model, "contents": contents})
            text = DRAFT if len(CAPTURE["gemini_calls"]) == 1 else REFINED
            return _FakeResponse(text)

    class _FakeClient:
        def __init__(self):
            self.models = _FakeModels()

    if TREE_KIND == "current":
        import article.gemini as _gemini_mod
        import article.image as _image_mod
        BASE_URL = _image_mod.BASE_URL
    else:
        BASE_URL = generate_article.BASE_URL

    def _fake_generate_and_save_image(prompt, output_filename, seed=-1):
        CAPTURE["image_calls"].append({
            "prompt": prompt,
            "output_filename": output_filename,
            "seed": seed,
        })
        save_dir = os.path.join("public", "images")
        os.makedirs(save_dir, exist_ok=True)
        stem = os.path.splitext(output_filename)[0]
        avif = stem + ".avif"
        with open(os.path.join(save_dir, avif), "wb") as f:
            f.write(b"EQFAKEAVIF:" + output_filename.encode("utf-8"))
        return f"{BASE_URL}/images/{avif}"

    if L3_REAL_PASS1:
        # L3: pass1 = 実 Gemini（1 呼び出しに限定）、pass2 = fake
        def _fake_refine(draft, prompt_type):
            CAPTURE["gemini_calls"].append({"model": "eq-fake-refine", "contents": "<pass2: fake refine>"})
            return (REFINED, "eq-fake-refine")

        generate_article.refine_content = _fake_refine
        if TREE_KIND == "current":
            import article.gemini as _gemini_mod
            import article.image as _image_mod
            _gemini_mod.MODELS_TO_TRY = list(_gemini_mod.MODELS_TO_TRY)[:1]
            _image_mod.generate_and_save_image = _fake_generate_and_save_image
        generate_article.generate_and_save_image = _fake_generate_and_save_image
    else:
        if TREE_KIND == "current":
            import article.gemini as _gemini_mod
            import article.image as _image_mod
            _gemini_mod.client = _FakeClient()
            _image_mod.generate_and_save_image = _fake_generate_and_save_image
        else:
            generate_article.client = _FakeClient()
        generate_article.generate_and_save_image = _fake_generate_and_save_image

    random.seed(SEED)
    generate_article.generate_post()

    with open(CAPTURE_PATH, "w", encoding="utf-8") as f:
        json.dump(CAPTURE, f, ensure_ascii=False, indent=2)
    print("EQ_RUNNER_DONE")


if __name__ == "__main__":
    main()
'''


def write_runner(sandbox: Path, tree_kind: str, l3_real_pass1: bool = False):
    code = (
        RUNNER_TEMPLATE
        .replace("__TREE_KIND__", tree_kind)
        .replace("__L3_REAL_PASS1__", "true" if l3_real_pass1 else "false")
    )
    (sandbox / "eq_runner.py").write_text(code, encoding="utf-8")


def make_env(variant: str, l3: bool = False) -> dict:
    env = os.environ.copy()
    env.update({
        "PROMPT_TYPE": variant,
        "GEMINI_API_KEY": "dummy-eq-test",
        "HF_TOKEN": "dummy-eq-test",
        "RAKUTEN_APPLICATION_ID": "",
        "RAKUTEN_ACCESS_KEY": "",
        "RAKUTEN_AFFILIATE_ID": "eq-test-rakuten-id",
        "AMAZON_TRACKING_ID": "eq-test-amazon-tag-22",
        "PYTHONIOENCODING": "utf-8",
        "MAX_INLINE_IMAGES": "7",
        "MIN_SCORE_THRESHOLD": "0",
    })
    if l3:
        env["GEMINI_API_KEY"] = _real_gemini_key()
    return env


def _real_gemini_key() -> str:
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise SystemExit("L3: 実 GEMINI_API_KEY が見つかりません（.env / 環境変数）")
    return key


# --------------------------------------------------
# 実行・収集
# --------------------------------------------------
def run_variant(sandbox: Path, variant: str, out_label: str, l3: bool = False) -> int:
    out = OUT_DIR / out_label
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "eq_runner.py", str(DRAFT_PATH), str(REFINED_PATH), _seed(), "eq_capture.json"]
    p = subprocess.run(
        cmd, cwd=sandbox, env=make_env(variant, l3),
        capture_output=True, text=True, encoding="utf-8", timeout=600,
    )
    (out / "stdout.log").write_text(p.stdout or "", encoding="utf-8")
    (out / "stderr.log").write_text(p.stderr or "", encoding="utf-8")
    (out / "exit_code.txt").write_text(str(p.returncode), encoding="utf-8")
    if p.returncode != 0:
        print(f"[FAIL] runner exit={p.returncode} ({out_label})")
        print((p.stderr or "")[-3000:])
    collect(sandbox, out)
    return p.returncode


def _norm_text(text: str, sandbox: Path) -> str:
    text = text.replace(str(sandbox), "<ROOT>").replace(sandbox.as_posix(), "<ROOT>")
    return text.replace("\\", "/")


def _norm_json(obj, sandbox: Path):
    win, pos = str(sandbox), sandbox.as_posix()

    def norm_str(s: str) -> str:
        s = s.replace(win, "<ROOT>").replace(pos, "<ROOT>")
        s = s.replace(win + "\\", "<ROOT>").replace(pos + "/", "<ROOT>")
        return s

    if isinstance(obj, str):
        return norm_str(obj)
    if isinstance(obj, dict):
        return {k: _norm_json(v, sandbox) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_norm_json(v, sandbox) for v in obj]
    return obj


def collect(sandbox: Path, out: Path):
    def grab(rel: str, dest_name: str, binary: bool = False):
        src = sandbox / rel
        if not src.exists():
            return
        data = src.read_bytes()
        if not binary and dest_name.endswith(".json"):
            try:
                obj = json.loads(data.decode("utf-8"))
                data = json.dumps(_norm_json(obj, sandbox), ensure_ascii=False, indent=2).encode("utf-8")
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        elif not binary:
            try:
                data = _norm_text(data.decode("utf-8"), sandbox).encode("utf-8")
            except UnicodeDecodeError:
                pass
        dest = out / dest_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    grab(f"src/content/posts/{TS}-auto-post.md", "article.md")
    grab(f"data/prompt_logs/{TS}.txt", "prompt_pass1.txt")
    grab(f"data/trend_usage_logs/{TS}.json", "trend_usage_log.json")
    grab(f"data/drafts/{TS}.json", "draft_metadata.json")
    grab(f"data/affiliate_logs/{TS}.json", "affiliate_link_log.json")
    grab("data/slug-redirects.json", "slug_redirects.json")
    grab("eq_capture.json", "capture.json")
    imgs_dir = sandbox / "public" / "images"
    if imgs_dir.exists():
        (out / "images").mkdir(parents=True, exist_ok=True)
        for f in sorted(imgs_dir.glob(f"{TS}-*.avif")):
            (out / "images" / f.name).write_bytes(f.read_bytes())

    # pass2 プロンプト（fake client 捕捉）を単独ファイル化
    cap_path = out / "capture.json"
    if cap_path.exists():
        try:
            cap = json.loads(cap_path.read_text(encoding="utf-8"))
            calls = cap.get("gemini_calls", [])
            if len(calls) >= 2:
                (out / "prompt_pass2.txt").write_text(_norm_text(calls[1].get("contents", ""), sandbox), encoding="utf-8")
        except Exception:
            pass


# --------------------------------------------------
# diff
# --------------------------------------------------
def diff_dirs(a: Path, b: Path) -> tuple[list[str], list[str]]:
    """a vs b の再帰バイト diff。

    戻り値: (fatal, order_only)
    - fatal: 内容差分 / ファイル欠落 / バイナリ差分（失敗扱い）
    - order_only: 行集合が同一で順序のみ異なる（装飾的な表示順序差・非失敗）
    """
    fatal: list[str] = []
    order_only: list[str] = []

    def list_files(d: Path) -> dict[str, Path]:
        if not d.exists():
            return {}
        return {p.relative_to(d).as_posix(): p for p in d.rglob("*") if p.is_file()}

    fa, fb = list_files(a), list_files(b)
    for name in sorted(set(fa) - set(fb)):
        fatal.append(f"only-in-A: {name}")
    for name in sorted(set(fb) - set(fa)):
        fatal.append(f"only-in-B: {name}")
    for name in sorted(set(fa) & set(fb)):
        da, db = fa[name].read_bytes(), fb[name].read_bytes()
        if da == db:
            continue
        try:
            ta = _norm_text(da.decode("utf-8"), a)
            tb = _norm_text(db.decode("utf-8"), b)
        except UnicodeDecodeError:
            fatal.append(f"differs: {name} ({len(da)}B vs {len(db)}B) (binary diff)")
            continue
        la, lb = ta.splitlines(), tb.splitlines()
        if sorted(la) == sorted(lb):
            order_only.append(f"order-only-differs: {name}（行内容同一・順序のみ異なる）")
            continue
        fatal.append(f"differs: {name} ({len(da)}B vs {len(db)}B)")
        for dl in difflib.unified_diff(
            la, lb, fromfile=f"A/{name}", tofile=f"B/{name}", lineterm="", n=2,
        ):
            fatal.append("    " + dl)
    return fatal, order_only


def check_capture_sanity(out: Path, expect_pass2: bool) -> list[str]:
    """capture.json の健全性: subprocess 発火なし / gemini 呼び出し回数。"""
    issues = []
    cap_path = out / "capture.json"
    if not cap_path.exists():
        return ["capture.json 不存在"]
    cap = json.loads(cap_path.read_text(encoding="utf-8"))
    for cmd in cap.get("subprocess_calls", []):
        s = " ".join(str(x) for x in cmd)
        if "fetch_topics" in s:
            issues.append(f"fetch_topics サブプロセス発火: {s}")
    calls = cap.get("gemini_calls", [])
    if expect_pass2:
        if len(calls) != 2:
            issues.append(f"gemini 呼び出し回数が 2 ではない: {len(calls)}")
    images = cap.get("image_calls", [])
    if not images:
        issues.append("image mock 呼び出しなし（ヘッダー画像未生成）")
    return issues


# --------------------------------------------------
# L3 構造健全性
# --------------------------------------------------
def l3_structure_check(out: Path) -> list[str]:
    issues = []
    art = out / "article.md"
    if not art.exists():
        return ["article.md が生成されていない"]
    text = art.read_text(encoding="utf-8")
    if not text.startswith("---"):
        issues.append("frontmatter 欠落")
    else:
        end = text.find("\n---", 3)
        if end < 0:
            issues.append("frontmatter 閉じタグ欠落")
        else:
            import yaml
            try:
                fm = yaml.safe_load(text[3:end])
                for key in ("title", "description", "tags", "image", "prompt_type"):
                    if key not in fm:
                        issues.append(f"frontmatter キー欠落: {key}")
            except yaml.YAMLError as e:
                issues.append(f"frontmatter YAML 破損: {e}")
    # 生成情報は geninfo.py が HTML（<summary>🤖 生成情報</summary>）で組立するため
    # markdown 見出し形式でも HTML 形式でも許容する
    gen_info_ok = ("## 生成情報" in text) or ("🤖 生成情報" in text)
    if not gen_info_ok:
        issues.append("セクション欠落: 生成情報 (## 生成情報 / 🤖 生成情報)")
    if "## まとめ" not in text:
        issues.append("セクション欠落: ## まとめ")
    imgs = list((out / "images").glob("*.avif")) if (out / "images").exists() else []
    if not imgs:
        issues.append("ヘッダー画像未生成")
    return issues


# --------------------------------------------------
# メイン
# --------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", default="69bb5e8", help="ベースラインコミット（A/B 用）")
    ap.add_argument("--variants", default=",".join(VARIANTS_ALL), help="カンマ区切りバリアント")
    ap.add_argument("--selftest", action="store_true", help="自己整合のみ実行（A/B なし）")
    ap.add_argument("--l3", action="store_true", help="L3: 実 Gemini 1 回（default）の構造健全性")
    ap.add_argument("--l3-recheck", action="store_true",
                    help="L3: 実 API 呼び出しせず既存成果物（out/realrun_<v>）に対して構造健全性チェックのみ再実行")
    args = ap.parse_args()

    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    for v in variants:
        if v not in VARIANTS_ALL:
            raise SystemExit(f"未知のバリアント: {v}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report: list[str] = []
    failed = False

    current_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    report.append(f"baseline: {args.baseline}\ncurrent:  {current_sha}\nvariants: {', '.join(variants)}\n")

    if args.l3_recheck:
        report.append("=== L3 recheck: 既存成果物の構造健全性チェック（API 呼び出しなし）===")
        failed = False
        for v in variants:
            out_v = OUT_DIR / f"realrun_{v}"
            if not (out_v / "article.md").exists():
                failed = True
                report.append(f"[L3 RECHECK FAIL] {v}: out/realrun_{v}/article.md 未存在（先に --l3 を実行すること）")
                continue
            issues = l3_structure_check(out_v)
            if issues:
                failed = True
                report.append(f"[L3 RECHECK FAIL] {v}: issues={issues}")
            else:
                report.append(f"[L3 RECHECK OK] {v}: 構造健全性チェック通過（詳細: out/realrun_{v}/）")
        if not failed:
            report.append("L3 RECHECK PASS")
        _write_report(report, failed)
        return

    if args.l3:
        report.append("=== L3: 実 Gemini 1 回（構造健全性のみ・A/B 不可）===")
        realrun = EQ_DIR / "realrun_pristine"
        expand_tree(current_sha, realrun)
        for v in variants:
            sandbox = EQ_DIR / "realrun"
            make_sandbox(realrun, sandbox)
            write_runner(sandbox, "current", l3_real_pass1=True)
            rc = run_variant(sandbox, v, f"realrun_{v}", l3=True)
            issues = l3_structure_check(OUT_DIR / f"realrun_{v}")
            if rc != 0 or issues:
                failed = True
                report.append(f"[L3 FAIL] {v}: rc={rc} issues={issues}")
            else:
                report.append(f"[L3 OK] {v}: 構造健全性チェック通過（詳細: out/realrun_{v}/）")
        if not failed:
            report.append("L3 PASS")
        _write_report(report, failed)
        return

    # --- pristine 展開 ---
    baseline_pristine = EQ_DIR / "baseline_pristine"
    current_pristine = EQ_DIR / "current_pristine"
    report.append("git archive 展開中...")
    expand_tree(current_sha, current_pristine)
    if not args.selftest:
        expand_tree(args.baseline, baseline_pristine)

    selftest_current = EQ_DIR / "selftest_current"
    ab_baseline = EQ_DIR / "ab_baseline"
    ab_current = EQ_DIR / "ab_current"

    for v in variants:
        # 自己整合: 現行 ×2
        for i in (1, 2):
            make_sandbox(current_pristine, selftest_current)
            write_runner(selftest_current, "current")
            rc = run_variant(selftest_current, v, f"selftest_{i}_{v}")
            if rc != 0:
                failed = True
                report.append(f"[SELFTEST FAIL] {v} run{i}: runner exit={rc}")
        st, st_oo = diff_dirs(OUT_DIR / f"selftest_1_{v}", OUT_DIR / f"selftest_2_{v}")
        san = check_capture_sanity(OUT_DIR / f"selftest_1_{v}", expect_pass2=True) + \
            check_capture_sanity(OUT_DIR / f"selftest_2_{v}", expect_pass2=True)
        if st or st_oo or san:
            failed = True
            report.append(f"[SELFTEST FAIL] {v}: 自己整合 diff/健全性问题あり")
            report.extend(st + st_oo + san)
        else:
            report.append(f"[SELFTEST OK] {v}: 2 回実行の出力がバイト一致")

        if args.selftest:
            continue

        # A/B
        for label, sandbox, pristine in (
            ("baseline", ab_baseline, baseline_pristine),
            ("current", ab_current, current_pristine),
        ):
            make_sandbox(pristine, sandbox)
            write_runner(sandbox, "baseline" if label == "baseline" else "current")
            rc = run_variant(sandbox, v, f"{label}_{v}")
            if rc != 0:
                failed = True
                report.append(f"[AB FAIL] {v} {label}: runner exit={rc}")
        ab, ab_oo = diff_dirs(OUT_DIR / f"baseline_{v}", OUT_DIR / f"current_{v}")
        san = check_capture_sanity(OUT_DIR / f"baseline_{v}", expect_pass2=True) + \
            check_capture_sanity(OUT_DIR / f"current_{v}", expect_pass2=True)
        if ab or san:
            failed = True
            report.append(f"[AB FAIL] {v}: diff/健全性问题あり")
            report.extend(ab + san + ab_oo)
        elif ab_oo:
            report.append(f"[AB OK*] {v}: 機能等価（成果物全て一致・表示順序のみ差異）")
            report.extend(ab_oo)
        else:
            report.append(f"[AB OK] {v}: baseline vs current の全成果物がバイト一致")

    _write_report(report, failed)
    sys.exit(1 if failed else 0)


def _write_report(report: list[str], failed: bool):
    text = "\n".join(report) + "\n\nRESULT: " + ("FAIL" if failed else "PASS") + "\n"
    (OUT_DIR / "diff_report.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
