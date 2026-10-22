"""生成的表不得依赖 set 的迭代顺序。

`phrases_map.txt` is built by joining per-character phrase-length numbers into ONE string per key. The
producer used to write `list(set(v))`, i.e. it emitted whatever order CPython's hash table happened to
have; for small ints that is ascending today, but it is an implementation detail, and the same shape with
strings would change between processes. `sorted(set(v))` makes the order a property of the DATA.

A behavioural test would need a full generation run (every table); this guard is on the source instead,
which is the level the defect lived at: the forbidden construct is `list(set(`.
"""

import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]


def test_common_py_never_joins_a_set_without_sorting_it() -> None:
    source = (REPO / "gen" / "common.py").read_text(encoding="utf-8")
    assert "list(set(" not in source, (
        "gen/common.py again builds an output string from an unsorted set; use sorted(set(...)) -- the "
        "output bytes must not depend on the hash table's layout"
    )


def test_the_two_phrase_length_sites_are_sorted() -> None:
    source = (REPO / "gen" / "common.py").read_text(encoding="utf-8")
    assert source.count("sorted(set(") >= 2, "expected both phrase-length sites to sort"
