"""run_versions.py -- 在指定的 (pypinyin, ToJyutping) 版本对下真正把生成器跑一遍，
并把结果与 cpp-pinyin 的冻结表做漂移比对。

每个生成器都把 `out_path = "out/dict/<lang>"` 写死。本 harness 早期版本试图比这更聪明（runpy 跑一遍，
再带不同 out_path 重调构造函数），结果造成了**假失败**：脚本自己模块级的 `skip_default_pinyin` 是对的，
而 harness 传的是构造函数的空默认值，于是一个本该被跳过的字反复冒出来、看起来像工具的 bug。这条教训值得
留着：**按代码真正被使用的方式去跑它**，把副作用挪开，而不是把调用改道。

所以：备份 out/dict，让脚本写到它们本来写的地方（在子进程里跑，好让选定的包版本生效），比对，然后还原。

⚠️ 因此它在运行期间会**覆盖** out/dict（生成器写死了那个路径），并在 `finally` 里还原、之后自比字节。
需要跨崩溃保住它就得自己备份 —— harness 自己那份是 `out/dict.prefrozen-backup`。

退出码（本 harness 的，不是生成器的）：
  0  = 每个生成器都退 0，且比对没发现漂移。
  1  = DRIFT：新产物与冻结树不一致 —— 任何 `DIFFERS`/`MISSING` 行，或者比对根本没跑成、没给出判定。
  其它 = 失败生成器的退出码（那些才是该先修的东西：写了一半的树说明不了漂移；打印的
       `=== <gen> (exit N) ===` 行和下面的 `DRIFT:` 行用来区分这两种情况）。
  9  = out/dict 没能从备份干净还原。

    python tools/run_versions.py 0.54.0 3.1.0
    python tools/run_versions.py 0.55.0 3.2.0 --keep

这两个包不一定装着；wheel 会下载一次到 .tools_probe/wheels，解包到 .tools_probe/pkg-<name>-<version>。
"""
import argparse
import os
import time
import pathlib
import shutil
import subprocess
import sys
import zipfile

REPO = pathlib.Path(__file__).resolve().parent.parent
PROBE = REPO / ".tools_probe"
WHEELS = PROBE / "wheels"
OUT = REPO / "out" / "dict"
BACKUP = REPO / "out" / "dict.prefrozen-backup"
# 2026-10：路径由 res/dict 迁到 data/dialects，且不应再硬编码某一台机器的盘符。
# 默认指向本机实际检出的 cpp-pinyin；换机器用 CPP_PINYIN_DICT 覆盖。
FROZEN = pathlib.Path(os.environ.get(
    "CPP_PINYIN_DICT", r"D:\projects\cpp-pinyin\data\dialects"))


def unpack(pkg_name: str, version: str, import_name: str) -> pathlib.Path:
    dest = PROBE / f"pkg-{pkg_name.lower()}-{version}"
    if (dest / import_name / "__init__.py").exists():
        return dest
    WHEELS.mkdir(parents=True, exist_ok=True)
    whl = next(iter(WHEELS.glob(f"{pkg_name.lower()}-{version}-*.whl")), None)
    if whl is None:
        print(f"downloading {pkg_name}=={version} ...")
        r = subprocess.run([sys.executable, "-m", "pip", "download", f"{pkg_name}=={version}",
                            "--no-deps", "-d", str(WHEELS)], capture_output=True, text=True,
                           encoding="utf-8")
        if r.returncode != 0:
            print(r.stdout[-500:], r.stderr[-800:])
            raise SystemExit(f"could not download {pkg_name}=={version}")
        whl = next(iter(WHEELS.glob(f"{pkg_name.lower()}-{version}-*.whl")), None)
    if whl is None:
        raise SystemExit(f"wheel for {pkg_name}=={version} not found in {WHEELS}")
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(whl) as z:
        z.extractall(dest)
    print(f"unpacked {whl.name} -> {dest}")
    return dest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pypinyin")
    ap.add_argument("tojyutping")
    ap.add_argument("--lang", choices=["mandarin", "cantonese", "both"], default="both")
    ap.add_argument("--keep", action="store_true",
                    help="leave the freshly generated files in out/dict instead of restoring")
    args = ap.parse_args()

    pypkg = unpack("pypinyin", args.pypinyin, "pypinyin")
    topkg = unpack("ToJyutping", args.tojyutping, "ToJyutping")

    state_before = None
    if OUT.exists():
        if BACKUP.exists():
            # A crashed earlier run leaves the true baseline here; deleting it would hand the next
            # run a contaminated state to call its baseline. Keep it, stamped.
            stale = BACKUP.with_name(BACKUP.name + "." + time.strftime("%Y%m%d-%H%M%S"))
            BACKUP.rename(stale)
            print(f"previous backup kept at {stale}")
        shutil.copytree(OUT, BACKUP)
        print(f"backed up {OUT} -> {BACKUP}")
        state_before = {p.relative_to(OUT): p.read_bytes() for p in OUT.rglob("*") if p.is_file()}

    # Put the chosen package versions first on the path of the child, and mark them so that
    # `import pypinyin` / `import ToJyutping` cannot silently fall back to the installed ones.
    #
    # ALLOW_VERSION_DRIFT is set because choosing a version IS this harness's purpose: the hard guard
    # in gen/common.py exists so that an *accidental* bump cannot silently emit a different dictionary,
    # while this harness deliberately produces the other dictionary in order to diff it. The guard
    # still runs and still reports; only its hard stop is lifted. `python gen/mandarin.py` by hand stays
    # guarded.
    env = dict(os.environ, PYTHONIOENCODING="utf-8",
               PYTHONPATH=os.pathsep.join([str(topkg), str(pypkg)]),
               PINYIN_MAKEDICT_ALLOW_VERSION_DRIFT="1")

    gens = (["gen/mandarin.py", "gen/cantonese.py"] if args.lang == "both"
            else [f"gen/{args.lang}.py"])
    rc = 0
    try:
        for gen in gens:
            r = subprocess.run([sys.executable, gen], cwd=REPO, env=env,
                               capture_output=True, text=True, encoding="utf-8")
            print(f"\n=== {gen} (exit {r.returncode}) ===")
            print((r.stdout or "").strip())
            if r.stderr:
                print("stderr tail:", r.stderr.strip()[-1200:])
            rc = rc or r.returncode

        print(f"\n{'=' * 70}\ngenerated into: {OUT}\n{'=' * 70}")
        # 比对的判定必须进**退出码**，不能只进日志：否则一次表全都不一致的运行仍会退 0 —— 一盏没人会
        # 注意到其错误的绿灯，除非有人手动去读 RESULT 行。它的 stdout 被捕获（原来是继承）以便既能原样
        # 打印又能判定；打印出来的文本没有变。
        cmp_proc = subprocess.run([sys.executable, "tools/compare_dict_dirs.py", str(OUT), str(FROZEN)],
                                  cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8")
        print((cmp_proc.stdout or "").rstrip())
        if cmp_proc.stderr:
            print("stderr tail:", cmp_proc.stderr.strip()[-1200:])
        # compare_dict_dirs.py deliberately exits 0 for CONTENT/ORDER differences -- attributing a
        # version difference is its job, and only MISSING files are structural failure for it (see
        # TOOLING.md §7). So its return code alone cannot answer "is there drift": the verdict line
        # decides, and a comparison that fails to run at all counts as drift (fail loud, never green).
        drift = (cmp_proc.returncode != 0
                 or "RESULT: byte-identical" not in (cmp_proc.stdout or ""))
        if drift:
            print(f"DRIFT: output under {OUT} does not match {FROZEN} "
                  f"(compare_dict_dirs.py exit {cmp_proc.returncode}) -> exiting 1")
            # A generator failure keeps its own code (it is the first thing to fix, and its partial
            # tree makes the comparison meaningless anyway); the two cases stay tellable apart by the
            # `=== <gen> (exit N) ===` lines and this `DRIFT:` line.
            rc = rc or 1
    finally:
        # Restore in finally: a crash, a failed comparison or Ctrl-C must not leave the other
        # version's dictionaries sitting in out/dict looking like the baseline.
        if state_before is not None and not args.keep:
            shutil.rmtree(OUT)
            shutil.copytree(BACKUP, OUT)
            after = {p.relative_to(OUT): p.read_bytes() for p in OUT.rglob("*") if p.is_file()}
            same = after == state_before
            print(f"\nout/dict restored from backup -- identical to before: {same}")
            shutil.rmtree(BACKUP, ignore_errors=True)
            if not same:
                print("WARNING: out/dict did NOT restore cleanly")
                rc = rc or 9
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
