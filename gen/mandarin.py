import argparse
import re
import sys

import pypinyin
import zhconv

from common import (MakeDict, MakeDictError, load_fanjian, out_path as out_dir, override_path, source_path,
                    parse_user_dict_lines, to_marked)
from data.overrides.man_overrides import (APPEND_NEW_READINGS, OVERWRITE_PINYIN_ADDITIONS,
                                PHRASE_OVERRIDES_MANDARIN, PROMOTE_NEW_READINGS, SET_FIRST_READING)


class MakeMandarin(MakeDict):
    def __init__(self, out_path, overwrite_pinyin, add_pinyin, transdict, user_dict, force_mono,
                 promote_new_readings=None, set_first_reading=None, phrase_overrides=None,
                 append_new_readings=None):
        super().__init__(out_path, overwrite_pinyin, add_pinyin, transdict, user_dict, force_mono,
                         promote_new_readings, set_first_reading, phrase_overrides, append_new_readings)

    def load_dict(self):
        # 获取词组
        with open(source_path("cedict_ts.u8"), "r", encoding="utf-8") as f:
            for line in f:
                res = re.search(r"(.*[\u4e00-\u9fa5]) (.*[\u4e00-\u9fa5]) \[([\w :]+)] (\{([\w :]+)})?", line)
                char = res.group(2) if res else None
                if char and not re.search("[0-9A-Za-z·:，]", char):
                    if len(char) > 1 and res.group(3):
                        pinyin = res.group(3).lower().replace("u:", "v")
                        values = ["er5" if i == "r5" else i for i in pinyin.split(" ")]

                        self.phrase_pinyin_dict[char] = " ".join(values)

    def fill_unicode_pinyin(self):
        # 扫描整个 CJK 区块。哪些字在这里拿到读音由**装着的 pypinyin 数据**决定，而那是本仓最大的漂移
        # 来源 —— 实测而非假设：
        #   * pypinyin 0.54.0 有 41,651 条字典条目，0.55.0 有 41,923 条。
        #   * U+9FA6..U+9FFF 区间：0.54.0 有 9 条、0.55.0 有 32 条，多出的 23 个字（U+9FAA 龪 .. U+9FFF 鿿）
        #     在 0.55.0 下都进 word.txt、没有一条存在于 0.54.0 ⇒ 复现出厂表不需要任何排除表。
        #   * 0.55.0 还**改写**了 5 个已有条目：杢 jiang->jié、婥 nào,chuò->chuò,nào、笹 ti->tì、
        #     枠 zui->huà、𦛨 lao->láo（箭头左边是 0.54.0 的输出，右边是 0.55.0）。
        # 两个方向都是把流水线在两个版本下各跑一遍、再与 cpp-pinyin 快照 diff 验出来的。
        #
        # **哪个版本复现出厂表取决于消费侧的快照**，所以判据永远是"用当前快照跑一次
        # tools/check_drift.ps1"，而不是相信这里写的话。
        #
        # 版本钉在 requirements.txt，`common.check_dependency_versions()` 在版本不符时拒绝运行，而不是
        # 默默产出另一份词典。真要升 pypinyin：同一次改动里跑 check_drift.ps1、重新冻结 cpp-pinyin 的
        # 门禁，并记录量到的后果（上面五个字都是日文国字或罕用变体；笹 是唯一在出厂语料里出现的，
        # 两次，且不改变任何判定）。
        char_list = [chr(i) for i in range(0x4E00, 0x9FFF + 1)]
        char_list += list(self.transdict.values())
        for i in char_list:
            text = zhconv.convert(i, "zh-cn")
            if self.default_pinyin.get(text) is None:
                pinyin = pypinyin.pinyin(text, style=pypinyin.TONE3)[0][0]
                if re.search(r"([^a-z\d])", pinyin) is None:
                    self.default_pinyin[text] = [pinyin]

    def format_reading(self, reading):
        """Mandarin renders readings in marked tone form; the shared writer calls this."""
        return to_marked(reading)

    def extra_tables(self):
        """`trans_word.txt`，走共享 staging 路径，确保标记仍是最后一次写。"""
        trans_word = []
        for k, v in self.default_pinyin.items():
            t_k = zhconv.convert(k, "zh-hant")
            if t_k != k and t_k not in not_fan:
                trans_word.append(f"{t_k}:{k}\n")

        for k, v in self.transdict.items():
            if k != v and k not in self.default_pinyin.keys() and v in self.default_pinyin.keys() and k not in not_fan:
                trans_word.append(f"{k}:{v}\n")
        return {"trans_word.txt": trans_word}

    def make_dict(self):
        # 四张表（三张共享表 + trans_word.txt）走同一个 writer：一个 staging 目录、一套下限、一次盖章。
        self.write_three_tables()


out_path = str(out_dir("dict", "mandarin"))
overwrite_pinyin = {
    "儿": "er5", "了": "le5", "呢": "ne5", "曾": "ceng2", "重": "chong2", "地": "de5", "藏": "cang2", "都": "dou1",
    "还": "hai2", "弹": "tan2", "着": "zhe5", "的": "de5", "哦": "o4", "盛": "sheng4", "哟": "yo5", "喔": "o1",
    "湮": "yan1", "拓": "ta4", "系": "xi4", "谁": "shei2", "什": "shen2", "么": "me5", "扛": "kang2", "攒": "zan3",
    "嗯": "n4", "喳": "zha1", "哋": "di4", "嘅": "ge3", "粘": "zhan1", "恁": "nen4", "嗌": "ai4", "褪": "tui4"
}

extra_pinyin = {"濛": "meng2", "尅": "kei2"}

force_mono = ["喳", "褪"]

not_fan = ["吒"]



# Measured reading-priority changes; see data/overrides/man_overrides.py for how they were obtained and what
# they cost. Merged rather than written into the literal above so the measured table stays regenerable
# and the hand-maintained entries stay reviewable.
overwrite_pinyin.update(OVERWRITE_PINYIN_ADDITIONS)


def load_configured_inputs():
    """两个吃数据的输入，在**构建开始时**读，而不是在导入本模块时读。

    两者原本都是模块级的（`load_fanjian(...)` 和遍历 `data/overrides/man_user.txt` 的循环），于是 `import mandarin`
    会从 `data/` 读约 155 kB。两者本来都不在导入时写盘 —— 但"没有副作用"和"没有 I/O"是两个承诺，读者能
    依赖的是窄的那个。

    `user_dict` 读的是 `data/overrides/man_user.txt`，它**有意**是空的：这是普通话侧手写覆盖条目的占位文件，**不是**
    消费侧的 `data/dialects/mandarin/user_dict.txt`（那个文件是运行时喂引擎的另一套机制）。在这里读它只是
    保留历史形状；README 的契约表说的是同一件事。
    """
    user_dict = {}
    with open(override_path("man_user.txt"), "r", encoding="utf-8") as f:
        # 空行与 `#` 行会被跳过，所以这个文件可以带一段解释自己是什么的表头 —— 它正需要：一个空文件
        # 挨着一个同名但语义不同的消费侧文件，是个容易踩的坑（README 已写明）。规则本身在
        # `common.parse_user_dict_lines` 里，由测试覆盖。
        user_dict = parse_user_dict_lines(f)
    return load_fanjian(not_fan), user_dict


def main(argv=None):
    """Build the shipping Mandarin tables.

    放在 `__main__` 之后是有意的：导入本模块不得顺带重新生成词典。`--out` 让探针跑到别处去，
    不会覆盖出厂产物目录。
    """
    parser = argparse.ArgumentParser(description="Build the shipping Mandarin tables.")
    parser.add_argument("--out", default=out_path, help=f"output directory (default: {out_path})")
    args = parser.parse_args(argv)
    chinese_transdict, user_dict = load_configured_inputs()
    try:
        MakeMandarin(args.out, overwrite_pinyin, extra_pinyin, chinese_transdict, user_dict, force_mono,
                     PROMOTE_NEW_READINGS,
                     SET_FIRST_READING,
                     PHRASE_OVERRIDES_MANDARIN,
                     APPEND_NEW_READINGS)
    except MakeDictError as error:
        # 与 `cantonese.py` 同一契约：拒绝就是一条消息加一个退出码，导入本模块的宿主也能接住。
        print(f"build refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
