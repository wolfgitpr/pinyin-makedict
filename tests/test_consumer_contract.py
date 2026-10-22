"""消费树必须就是清单所写的那些字节。

为什么需要这个文件：`MANIFEST.sha256` 钉住了"一次生成应该长什么样"，而
`test_manifest_matches_a_fresh_generation` 已经证了"新生成 == 清单"。还缺三角形的另一条边：**消费树**
（`cpp-pinyin/data/dialects/<lang>/`）此前没有任何自动检查 —— 字节权威在 `tools/check_drift.ps1` 里，
那要人手动跑、还要一套装了钉版依赖的 Python 环境。有了这一条，一次 `pytest` 就钉住三个角：
生成 -> 清单 -> 消费树。

邻仓是可选的。它不在时本测试**SKIP 并打印原因**，而不是通过：一次什么都没量到的绿，正是本仓一直
在找的那种失败模式。
"""

from __future__ import annotations

import hashlib
import os
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = REPO / "MANIFEST.sha256"

#: Where the consumer checkout usually is. `CPP_PINYIN_ROOT` overrides it (CI, other machines).
DEFAULT_CONSUMER = REPO.parent / "cpp-pinyin"


def _manifest_rows() -> dict[str, tuple[int, int, str]]:
    rows = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, size, count, digest = line.split()
        rows[name] = (int(size), int(count), digest)
    assert rows, "the manifest loaded 0 rows -- refusing to compare against nothing"
    return rows


def _consumer_root() -> pathlib.Path:
    root = pathlib.Path(os.environ.get("CPP_PINYIN_ROOT", str(DEFAULT_CONSUMER)))
    if not (root / "data" / "dialects").is_dir():
        pytest.skip(
            f"consumer checkout not found at {root} (set CPP_PINYIN_ROOT to its root); "
            "this check would otherwise pass while measuring nothing"
        )
    return root


def test_manifest_is_not_empty() -> None:
    """A manifest with no rows would make every comparison below vacuous."""
    assert len(_manifest_rows()) == 10, "expected 10 rows: 8 tables + 2 format.txt files"


def test_consumer_tree_matches_the_manifest() -> None:
    """`cpp-pinyin/data/dialects/**` must hold exactly the bytes `MANIFEST.sha256` describes."""
    consumer = _consumer_root()
    rows = _manifest_rows()
    problems = []
    for name, (size, count, digest) in rows.items():
        path = consumer / "data" / "dialects" / name
        if not path.is_file():
            problems.append(f"{name}: missing from the consumer tree")
            continue
        data = path.read_bytes()
        if len(data) != size:
            problems.append(f"{name}: {len(data)} bytes, manifest says {size}")
            continue
        if hashlib.sha256(data).hexdigest() != digest:
            problems.append(f"{name}: sha256 differs from the manifest")
            continue
        if len(data.decode("utf-8").splitlines()) != count:
            problems.append(f"{name}: row count differs from the manifest")
    assert not problems, "the consumer tree drifted from the producer's manifest:\n  " + "\n  ".join(problems)
