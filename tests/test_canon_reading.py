import pathlib
import sys
"""`preserve_e_hat` 是实例开关，不是模块状态。

为什么需要这个文件：这个开关原本是模块级常量 `common.PRESERVE_E_HAT`，新方言想打开它只能在构造
`MakeDict` **之前**赋值。一个进程里先后建两个方言时，第二次赋值会静默改写第一次的折叠方式 ——
代价是实测量到的：金标 86.91% -> 60.17%（−26.74pt），因为 ê 与 e 被折成了同一个韵母。改成构造参数后
两个实例互不影响；下面这些用例就是把这件事钉住。
"""

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "gen"))

import common


def test_the_module_global_is_gone():
    """A global would silently win over the parameter, so its absence is the contract."""
    assert not hasattr(common, "PRESERVE_E_HAT")


def test_canon_reading_folds_e_hat_by_default():
    assert common.canon_reading("ê") == "e5"


def test_canon_reading_keeps_e_hat_when_asked():
    assert common.canon_reading("ê", preserve_e_hat=True) == "ê5"


def test_two_instances_do_not_contaminate_each_other():
    """The interleaved construction is the case the module-global version got wrong."""
    folding = common.MakeDict("folding", {"x": "ê"}, {})
    preserving = common.MakeDict("preserving", {"x": "ê"}, {}, preserve_e_hat=True)
    # Constructed AFTER `preserving`, and still folding: instance state did not leak backwards.
    assert folding.overwrite_pinyin["x"] == "e5"
    assert preserving.overwrite_pinyin["x"] == "ê5"
