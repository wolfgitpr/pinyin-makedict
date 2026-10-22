"""本仓的自动门禁。

为什么是这三条：本仓此前**没有任何自动化检查** —— 没有 pytest、没有 CI、没有 pre-commit，唯一能查的是
`tools/check_drift.ps1`，而它需要邻仓、且只重跑两个生成器。最便宜、最能挡住"看起来成功"的三条就在这里：

1. `test_manifest_matches_a_fresh_generation` —— 重新生成 8 张表并与 `MANIFEST.sha256` 逐字节比对。
   这是最强的一条：它同时校验了生成器的确定性、语料的可读性与清单本身的正确性。
2. `test_generation_refuses_to_stamp_an_incomplete_dictionary` —— 空表与非空但过小的表必须抛错，
   而不是写成一个"已完成"的目录（从"人工跑一次"变成"每次跑都验"）。
3. `test_dependencies_are_pinned` —— `common.check_dependency_versions()` 一步到位：钉版是数据血源
   的一半，钉版漂了 8 张表就跟着漂。

**不借用邻仓的锚点门**：`..\cpp-pinyin\tools\audit_doc_anchors.py` 是跨仓硬依赖，在本仓独立 checkout
时会红；换成清单比对，价值更高且自足。锚点问题留给 cpp-pinyin 侧的门禁。
"""

from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = REPO / "MANIFEST.sha256"
TABLES = ("word.txt", "phrases_dict.txt", "phrases_map.txt", "trans_word.txt", "format.txt")


def _manifest_rows() -> dict[str, tuple[int, int, str]]:
    """{`<dialect>/<table>`: (bytes, rows, sha256)} out of the manifest's data lines."""
    rows: dict[str, tuple[int, int, str]] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, size, count, digest = line.split()
        rows[name] = (int(size), int(count), digest)
    return rows


def test_manifest_is_not_empty() -> None:
    """A manifest that lists nothing would make the comparison below vacuous."""
    rows = _manifest_rows()
    assert len(rows) == len(TABLES) * 2, f"expected {len(TABLES) * 2} entries, found {sorted(rows)}"


@pytest.mark.parametrize("dialect", ["mandarin", "cantonese"])
def test_manifest_matches_a_fresh_generation(dialect: str, tmp_path: pathlib.Path) -> None:
    """Regenerate one dialect and compare every table byte for byte with the manifest."""
    out = tmp_path / dialect
    entry = "gen/cantonese.py" if dialect == "cantonese" else "gen/mandarin.py"
    completed = subprocess.run([sys.executable, entry, "--out", str(out)], cwd=str(REPO),
                               capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    rows = _manifest_rows()
    for table in TABLES:
        key = f"{dialect}/{table}"
        assert key in rows, f"{key} is not in the manifest"
        size, count, digest = rows[key]
        data = (out / table).read_bytes()
        assert len(data) == size, f"{key}: {len(data)} bytes, manifest says {size}"
        assert hashlib.sha256(data).hexdigest() == digest, f"{key}: sha256 differs from the manifest"
        assert len(data.decode("utf-8").splitlines()) == count, f"{key}: row count differs"


def test_generation_refuses_to_stamp_an_incomplete_dictionary(tmp_path: pathlib.Path) -> None:
    """An empty table must raise, not produce a file; a too-small table must not get the marker."""
    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "gen"))
    import common  # noqa: PLC0415 -- imported here so the test can run from any cwd

    # 拒绝是 `common.MakeDictError`，宿主唯一需要接的类。这里原本抛 `ValueError`、别处抛
    # `SystemExit`，那个分裂正是让"生成器拒绝了"无法作为一件事被接住的原因。
    with pytest.raises(common.MakeDictError):
        common.write_lf_atomically(tmp_path / "empty.txt", [])

    # The marker is only written after the floors pass, so a directory holding nothing but the marker
    # can never be produced by the writer: assert the guard exists rather than re-running a generator
    # with a broken corpus (which would need a fixture we do not have).
    source = (REPO / "gen" / "common.py").read_text(encoding="utf-8")
    assert "sanity floor" in source and "format.txt" in source
    marker_write = source.index('write_lf_atomically(target / "format.txt"')
    floor_check = source.index("sanity floor")
    assert floor_check < marker_write, "the row floors must be checked BEFORE the marker is written"


def test_marker_is_written_after_every_table_including_dialect_ones() -> None:
    """`format.txt` 必须是一次生成的最后一次写，方言自己的表也算在内。

    两个生成器原本在 `write_three_tables()` 返回**之后**、也就是标记之后才写 `trans_word.txt`：在那个
    窗口里崩掉，会留下一个自称"这一代已完成"、却缺一张表的目录。修法是把方言表也走 `extra_tables()`，
    让它们同样先 staging、再落位，最后才盖章。下面这些断言钉的是形状；产物字节是否一致由
    `test_manifest_matches_a_fresh_generation` 另外钉。
    """
    common_src = (REPO / "gen" / "common.py").read_text(encoding="utf-8")
    extras = common_src.index("extras = self.extra_tables()")
    marker = common_src.index('write_lf_atomically(target / "format.txt"')
    assert extras < marker, "dialect tables must be staged BEFORE the marker is written"
    assert 'for _name in ("phrases_dict.txt", "phrases_map.txt", "word.txt", *extras)' in common_src, (
        "the replace loop must include the dialect tables, or they would stay in the staging directory"
    )

    for generator in ("gen/mandarin.py", "gen/cantonese.py"):
        text = (REPO / generator).read_text(encoding="utf-8")
        assert "def extra_tables" in text, f"{generator} must emit its own table through extra_tables()"
        make_dict = text.index("def make_dict")
        tail = text[make_dict:]
        assert "write_lf_atomically" not in tail and "os.replace" not in tail, (
            f"{generator}.make_dict must not write any table after write_three_tables() returns -- that "
            "window is the one the marker cannot protect"
        )


def test_dependencies_are_pinned() -> None:
    """`check_dependency_versions()` 把钉版规则收敛成一次调用。

    它返回一个**列表**（空 == 每条钉版都成立）：断言 `is None` 会对 `[]` 失败 —— 一个说"没有问题"的
    测试必须检查空，而不是非 None。
    """
    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "gen"))
    import common  # noqa: PLC0415

    problems = common.check_dependency_versions()
    assert problems == [], f"dependency pins drifted: {problems}"
