"""compare_dict_dirs.py -- exact per-file diff between two copies of a generated dictionary tree.

`tools/check_drift.ps1` reports "line count" and stops, which is enough to notice drift but not to
attribute it. This prints the actual differing lines, so a drift claim is auditable rather than
believed.

Two categories are kept apart on purpose, because they mean very different things here:

  * CONTENT difference -- a line exists on one side and not the other, or the same key has a different
    reading. This changes what the engine outputs.
  * ORDER difference -- the two files hold exactly the same lines but in a different sequence. For
    `word.txt` this is still real content, because the FIRST reading of a key is the engine's default
    reading; but the order of the KEYS is not consulted by the engine at all, which is why the count
    of positional differences is reported next to the count of reversed pairs.

Run:  python tools/compare_dict_dirs.py <dirA> <dirB> [--max N]
"""
import argparse
import json
from collections import Counter
from pathlib import Path

# Table names used only when a tree carries no dialect.json (the producer's out/dict has none). When a
# manifest IS present its required_tables is the authority and this list is just the fallback.
FALLBACK_FILES = ["word.txt", "phrases_dict.txt", "phrases_map.txt", "trans_word.txt"]


def dialects_present(a_root: Path, b_root: Path) -> list[str]:
    """方言 id 从两棵树里派生，绝不来自本文件里的一张表。

    写死 ["mandarin", "cantonese"] 会在加第三个方言的那天静默变窄 —— 而那正是本仓存在的原因 ——
    并且它会在只比了三个中的两个的情况下报告"全部一致"。消费侧那件工具已经从目录列表派生；现在两边都是。
    """
    return sorted({p.name for root in (a_root, b_root) if root.is_dir()
                   for p in root.iterdir() if p.is_dir()})


def manifest_tables(root: Path, lang: str) -> list[str] | None:
    """required_tables from that dialect's dialect.json, or None when there is no usable manifest."""
    manifest = root / lang / "dialect.json"
    if not manifest.is_file():
        return None
    try:
        tables = json.loads(manifest.read_text(encoding="utf-8")).get("required_tables")
    except (OSError, ValueError):
        return None
    return [str(t) for t in tables] if isinstance(tables, list) and tables else None


def table_names(a_root: Path, b_root: Path, lang: str) -> list[str]:
    """Union of both sides' declared tables, keeping the historical four first so output stays stable."""
    names: list[str] = []
    for root in (a_root, b_root):
        for t in (manifest_tables(root, lang) or FALLBACK_FILES):
            if t not in names:
                names.append(t)
    return [t for t in FALLBACK_FILES if t in names] + [t for t in names if t not in FALLBACK_FILES]


def read_lines(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").splitlines()


def key_of(line: str) -> str:
    return line.rsplit(":", 1)[0] if ":" in line else line


def count_reversals(a: list[str], b: list[str], max_pairs: int) -> tuple[int, list[tuple[str, str]]]:
    """Index pairs (i, j), i < j, where the two sequences disagree on relative order.

    Uses set indexes over the key of each line: a pair is reversed when A puts key X before key Y and
    B puts Y before X. Reported as a count plus a few examples, because a pure reorder of two adjacent
    keys makes every later index differ, and printing "104 positions differ" for a one-line move is
    technically true and completely misleading.
    """
    ia = {key_of(x): i for i, x in enumerate(reversed(a))}
    ib = {key_of(x): i for i, x in enumerate(reversed(b))}
    keys = [k for k in ia if k in ib]
    pairs: list[tuple[str, str]] = []
    n = 0
    for i, x in enumerate(keys):
        for y in keys[i + 1:]:
            if (ia[x] < ia[y]) != (ib[x] < ib[y]):
                n += 1
                if len(pairs) < max_pairs:
                    pairs.append((x, y))
    return n, pairs


def compare(a_root: Path, b_root: Path, max_examples: int = 8) -> int:
    """Compare two trees and return the exit code. Prints; never parses arguments (see `main`).

    Separated from argument parsing so `--self-test` exercises the SAME code the CLI runs, instead of a
    second copy of it that could agree with the tests and disagree with the tool.
    """
    content_files = order_files = missing_files = compared = 0
    for lang in dialects_present(a_root, b_root):
        for name in table_names(a_root, b_root, lang):
            pa, pb = a_root / lang / name, b_root / lang / name
            if not pa.exists() or not pb.exists():
                where = [str(p) for p in (pa, pb) if not p.exists()]
                print(f"{lang}/{name}: MISSING ({', '.join(where)})")
                missing_files += 1
                continue

            compared += 1
            ba, bb = pa.read_bytes(), pb.read_bytes()
            if ba == bb:
                print(f"{lang}/{name}: IDENTICAL ({len(ba)} bytes, {len(read_lines(pa))} lines)")
                continue

            la, lb = read_lines(pa), read_lines(pb)
            ca, cb = Counter(la), Counter(lb)
            only_a = sorted((ca - cb).elements())
            only_b = sorted((cb - ca).elements())

            if only_a or only_b:
                print(f"{lang}/{name}: DIFFERS (content)  bytes {len(ba)} vs {len(bb)}, "
                      f"lines {len(la)} vs {len(lb)}")
                for x in only_a[:max_examples]:
                    print(f"    only in A: {x}")
                if len(only_a) > max_examples:
                    print(f"    ... {len(only_a) - max_examples} more only-in-A")
                for x in only_b[:max_examples]:
                    print(f"    only in B: {x}")
                if len(only_b) > max_examples:
                    print(f"    ... {len(only_b) - max_examples} more only-in-B")
                content_files += 1
                continue

            n_rev, pairs = count_reversals(la, lb, max_examples)
            print(f"{lang}/{name}: DIFFERS (order only)  bytes {len(ba)} vs {len(bb)}, "
                  f"same {len(la)} lines, {n_rev} reversed key pair(s)")
            for x, y in pairs:
                print(f"    A puts {x!r} before {y!r}; B puts {y!r} before {x!r}")
            if n_rev > len(pairs):
                print(f"    ... {n_rev - len(pairs)} more reversed pair(s)")
            order_files += 1

    print()
    if missing_files:
        print(f"RESULT: {missing_files} file(s) MISSING"
              + (f"; {content_files} differ in content" if content_files else "")
              + (f"; {order_files} in order only" if order_files else ""))
    elif compared == 0:
        # 什么都没比、也什么都没缺：两棵树里都没有方言目录。这里不能打印 "RESULT: byte-identical" 并
        # 退 0 —— 路径写错、树没生成、两个空目录都会被读成"两棵树一致"，而那是本工具绝不能凭空造出来的
        # 答案。用 4，与 `check_drift.ps1` 对同一处境的判定对齐。（MISSING 分支留在它上面：树里有方言
        # 但没有表属于结构性失败，不是"空比较"。）
        print("RESULT: NOTHING COMPARED -- neither tree has a dialect directory with tables, so this run "
              "says nothing about them (wrong path? ungenerated dialect? empty directory?)")
        return 4
    elif content_files == 0 and order_files == 0:
        print("RESULT: byte-identical")
    elif content_files == 0:
        print(f"RESULT: no content differences; {order_files} file(s) differ in line order only")
    else:
        print(f"RESULT: {content_files} file(s) differ in content"
              + (f", {order_files} in order only" if order_files else ""))
    # A missing file is structural, not an expected version difference: only that is a failure.
    return 1 if missing_files else 0


def self_test() -> int:
    """Prove the verdicts, including the one this tool got wrong: an empty comparison is not agreement."""
    import contextlib
    import io
    import tempfile

    def run(a: Path, b: Path) -> tuple[int, str]:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = compare(a, b)
        return code, buffer.getvalue()

    failures: list[str] = []
    ran = 0

    def expect(label: str, ok: bool, detail: object = "") -> None:
        nonlocal ran
        ran += 1
        print(f"{'PASS' if ok else 'FAIL'}  self-test: {label}" + ("" if ok else f"  -> {detail}"))
        if not ok:
            failures.append(label)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        def make_tree(name: str, word: str) -> Path:
            """One dialect carrying the FULL fallback table set.

            The tool compares every table either side could have, so a fixture that writes only
            `word.txt` measures MISSING files rather than the verdict the case is about -- measured: that
            is exactly how the first version of this self-test failed all four of its cases.
            """
            lang = root / name / "mandarin"
            lang.mkdir(parents=True)
            (lang / "word.txt").write_text(word, encoding="utf-8")
            for extra in FALLBACK_FILES[1:]:
                (lang / extra).write_text("", encoding="utf-8")
            return root / name

        empty_a, empty_b = root / "a", root / "b"
        empty_a.mkdir()
        empty_b.mkdir()
        code, out = run(empty_a, empty_b)
        expect("two empty trees are NOT byte-identical", code == 4 and "NOTHING COMPARED" in out, (code, out))

        only_a = make_tree("only_a", "a 1\n")
        code, out = run(only_a, empty_b)
        expect("a table on one side only is MISSING (exit 1)", code == 1 and "MISSING" in out, (code, out))

        same = make_tree("same", "a 1\n")
        code, out = run(only_a, same)
        expect("identical trees report byte-identical (exit 0)", code == 0 and "byte-identical" in out, (code, out))

        other = make_tree("other", "a 1\nb 2\n")
        code, out = run(only_a, other)
        expect("a content difference is reported (exit 0, text says DIFFERS)",
               code == 0 and "DIFFERS (content)" in out, (code, out))

        reordered = make_tree("reordered", "a 1\nc 3\n")
        code, out = run(only_a, reordered)
        expect("a different key set is content, not order", code == 0 and "DIFFERS (content)" in out, (code, out))

    print(f"self-test: {ran} case(s), {len(failures)} failure(s)"
          + (": " + "; ".join(failures) if failures else ""))
    if not ran:
        print("self-test: NO CASES RAN -- a self-test that checks nothing must not report success")
        return 1
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a", nargs="?")
    ap.add_argument("b", nargs="?")
    ap.add_argument("--max", type=int, default=8, help="max examples to print per file")
    ap.add_argument("--self-test", action="store_true", help="prove the verdicts on planted trees, then exit")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.a or not args.b:
        ap.error("two directory arguments are required (or --self-test)")
    return compare(Path(args.a), Path(args.b), args.max)


if __name__ == "__main__":
    raise SystemExit(main())
