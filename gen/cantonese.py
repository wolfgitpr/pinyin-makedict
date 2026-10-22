import sys

import ToJyutping

from common import MakeDict, MakeDictError, load_fanjian, out_path as out_dir, source_path
from data.overrides.can_overrides import PHRASE_OVERRIDES_CANTONESE, SET_FIRST_READING_CANTONESE


class MakeCantonese(MakeDict):
    def __init__(self, out_path, overwrite_pinyin, add_pinyin, transdict, own_key=()):
        self.own_key = own_key
        super().__init__(out_path, overwrite_pinyin, add_pinyin, transdict, {}, [],
                         None, SET_FIRST_READING_CANTONESE, PHRASE_OVERRIDES_CANTONESE)

    def set_first_reading_apply(self):
        """把实测得到的读音移到首位，其余读音一个不动。

        覆写父方法的原因：两种词典的读音写法不同 —— 普通话的 default_pinyin 存规范 TONE3，写出时才转带调符；
        粤语的读音直接来自 ToJyutping、原样写出。父实现是朴素的 `x != v` 字符串比较，一旦表里的写法和字典
        里的一致就没问题，写错了却是**静默**的：匹配不上、条目等于没生效，和"这个改动本来就没影响"分不出来。

        所以要断言。目标读音不在该字的读音表里，要么是表里有错字、要么是上游数据不再提供该读音，两种情况都
        必须让这次运行失败，而不是悄无声息地再产出一份旧词典。
        """
        missing = []
        for k, v in SET_FIRST_READING_CANTONESE.items():
            cur = self.default_pinyin.get(k)
            if cur is None:
                missing.append(f"{k} (character absent from the table)")
                continue
            if v not in cur:
                missing.append(f"{k}: wanted {v}, available {cur}")
                continue
            # Reorder only. Nothing is added, nothing is removed: a reading deleted here would leave the
            # engine with no answer in whatever other context needed it.
            self.default_pinyin[k] = [v] + [x for x in cur if x != v]
        if missing:
            raise MakeDictError(
                "SET_FIRST_READING_CANTONESE does not apply:\n  " + "\n  ".join(missing) +
                "\nA reorder must name a reading that already exists; fix the table or the upstream data."
            )

    def load_dict(self):
        # Older, now dead source for phrase readings: data/sources/cccedict-canto-readings.txt (regex-parsed, keys
        # zh-converted). Superseded by the tab-separated data/sources/sanitized.txt read below.
        with open(source_path("sanitized.txt"), "r", encoding="utf-8") as f:
            for line in f:
                lyric, pinyin = line.strip().split("\t")
                if len(lyric) == 1:
                    jian = self.transdict.get(lyric, lyric)
                    # 人工表只补空位，不覆盖语料统计出来的首选读音
                    if self.default_pinyin.get(jian) is None:
                        self.default_pinyin[jian] = pinyin
                else:
                    if self.phrase_pinyin_dict.get(lyric) is None:
                        self.phrase_pinyin_dict[lyric] = pinyin

    def fill_unicode_pinyin(self):
        # Upper bound stays 0x9FFF, unlike gen/mandarin.py's: the frozen Cantonese table DOES hold characters
        # above U+9FA5 (ToJyutping has readings), so tightening to Mandarin's bound drops 15 entries -- measured.
        char_list = [chr(i) for i in range(0x4E00, 0x9FFF + 1)]

        for text in char_list:
            # own_key 里的字以本字为键，其余走 fan->jian 表（见文件末尾的 吒 注释）。
            jian = text if text in self.own_key else self.transdict.get(text, text)
            if self.default_pinyin.get(jian) is None:
                jyutping = ToJyutping.get_jyutping_candidates(jian)[0]
                jyutpingList = [x for x in jyutping[1]]
                if jyutpingList:
                    self.default_pinyin[jian] = jyutpingList

        for fan, jian in self.transdict.items():
            jian_jyutping = ToJyutping.get_jyutping_candidates(jian)[0]
            jian_jyutpingList = [x for x in jian_jyutping[1]]
            if jian_jyutpingList and self.default_pinyin.get(jian) is None:
                self.default_pinyin[jian] = jian_jyutpingList

            fan_jyutping = ToJyutping.get_jyutping_candidates(fan)[0]
            fan_jyutpingList = [x for x in fan_jyutping[1]]
            if fan_jyutpingList and fan_jyutping != jian_jyutping and self.default_pinyin.get(fan):
                self.default_pinyin[fan] = fan_jyutpingList

    def extra_tables(self):
        """`trans_word.txt`，走共享 staging 路径，确保标记仍是最后一次写。"""
        trans_word = []
        for k, v in self.transdict.items():
            # Written when the fan form was MERGED AWAY (no entry of its own), plus own_key characters,
            # which are deliberately not merged but whose mapping is still wanted -- the other half of
            # what keeps the frozen pair reproducible.
            if k != v and v in self.default_pinyin.keys() and (k in self.own_key or k not in self.default_pinyin.keys()):
                trans_word.append(f"{k}:{v}\n")
        return {"trans_word.txt": trans_word}

    def make_dict(self):
        # 四张表走同一个 writer：一个 staging 目录、一套下限、一次盖章。
        self.write_three_tables()


out_path = str(out_dir("dict", "cantonese"))

# 吒/咤 是出厂表里唯一需要"两半反向处理"的一对：word.txt 要 吒 自己的键，trans_word.txt 要 吒->咤 映射。
# 所以 data/sources/fanjian2.txt 里必须有「吒,咤」那一行（它曾被上游删掉，恢复后才两半都对），同时用 own_key 让扫描
# 不为 吒 改写键。改任一处都会破坏 8 张表逐字节一致，判据是 tools/check_drift.ps1。


# own_key：扫描时键不得按 fan->jian 表改写的字，尽管映射仍留在 transdict、照旧写进 trans_word.txt。
# 影响仅限列出的字，其余映射的键语义不变。
own_key = ["吒"]


def load_transdict():
    """The curated fan->jian table this generator scans against: data/sources/fanjian.txt + data/sources/fanjian2.txt."""
    return load_fanjian()


def main(argv=None):
    """Build the shipping Cantonese tables.

    放在 `__main__` 之后是有意的：导入本模块不得顺带重新生成词典。`--out` 让探针跑到别处去，
    不会覆盖出厂产物目录。
    """
    import argparse

    parser = argparse.ArgumentParser(description="Build the shipping Cantonese tables.")
    parser.add_argument("--out", default=out_path, help=f"output directory (default: {out_path})")
    args = parser.parse_args(argv)
    try:
        MakeCantonese(args.out, {}, {}, load_transdict(), own_key)
    except MakeDictError as error:
        # 拒绝就是一条消息加一个退出码，不是 traceback：调用方要知道是哪张表违反了哪条规则。
        print(f"build refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
