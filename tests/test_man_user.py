"""`data/overrides/man_user.txt` 由 `common.parse_user_dict_lines` 解析，而文件本身是个占位符。

为什么需要这个文件：生产侧的 `data/overrides/man_user.txt` 是空的，而它隔着一条仓界挨着一个同名但语义不同的
消费侧文件（`cpp-pinyin/data/dialects/mandarin/user_dict.txt`，2,125 B，由引擎在运行时加载）。所以那些
解析规则永远跑不到真实数据上，而一个空输入分不出"规则是对的"和"规则从没运行过"。这些用例直接钉规则。
"""

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "gen"))

import common  # noqa: E402 -- needs REPO on sys.path first


def test_the_real_placeholder_is_empty() -> None:
    """The file's emptiness is part of the contract the README states: it changes no output bytes."""
    assert (REPO / "data" / "overrides" / "man_user.txt").stat().st_size == 0


def test_blank_and_comment_lines_are_skipped() -> None:
    assert common.parse_user_dict_lines(["# a header explaining the file\n", "\n", "  \n"]) == {}


def test_entries_are_key_colon_value() -> None:
    assert common.parse_user_dict_lines(["京都:jing1 du1\n"]) == {"京都": "jing1 du1"}


def test_a_colon_inside_the_value_is_kept() -> None:
    assert common.parse_user_dict_lines(["a:b:c\n"]) == {"a": "b:c"}


def test_surrounding_whitespace_is_trimmed_on_both_sides() -> None:
    assert common.parse_user_dict_lines(["  d  :  e  \n"]) == {"d": "e"}


def test_a_line_without_a_key_is_a_refusal_not_a_silent_skip() -> None:
    with pytest.raises(common.MakeDictError):
        common.parse_user_dict_lines([":orphan-value\n"])
