"""生成器的拒绝只有**一个**可捕获的类，CLI 把它变成一条消息加一个退出码。

为什么需要这个文件：拒绝原本分三种 —— `ValueError`（空表）、`RuntimeError`（版本漂移、行数下限）和
`SystemExit`（数据表不适用）。前两种能被 `except Exception` 接住；`SystemExit` **不能**，所以把生成器
当库用的宿主可能因为一个数据问题被结束进程。`MakeDictError` 现在是唯一的基类，这些用例保证它保持唯一。
"""

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "gen"))

import common  # noqa: E402 -- needs REPO on sys.path first


def test_the_base_class_is_catchable_as_an_exception() -> None:
    assert issubclass(common.MakeDictError, Exception)


def test_the_base_class_is_not_a_system_exit() -> None:
    """The point of the change: a refusal must never be able to kill the importing host."""
    assert not issubclass(common.MakeDictError, SystemExit)


def test_an_empty_table_raises_the_one_class(tmp_path: pathlib.Path) -> None:
    with pytest.raises(common.MakeDictError):
        common.write_lf_atomically(tmp_path / "empty.txt", [])


def test_the_mandarin_cli_reports_a_refusal_without_a_traceback(monkeypatch, tmp_path: pathlib.Path, capsys) -> None:
    import mandarin  # noqa: PLC0415 -- imported here so the test can run from any cwd

    def refuse(*_args, **_kwargs):
        raise common.MakeDictError("planted refusal")

    monkeypatch.setattr(mandarin, "MakeMandarin", refuse)
    code = mandarin.main(["--out", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 1
    assert "build refused: planted refusal" in captured.err


def test_the_mandarin_cli_returns_zero_when_the_build_succeeds(monkeypatch, tmp_path: pathlib.Path) -> None:
    import mandarin  # noqa: PLC0415

    monkeypatch.setattr(mandarin, "MakeMandarin", lambda *_args, **_kwargs: None)
    assert mandarin.main(["--out", str(tmp_path)]) == 0
