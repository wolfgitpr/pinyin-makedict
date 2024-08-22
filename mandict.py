import re

import pypinyin
import zhconv

from common import MakeDict
from pypinyin.style._tone_convert import tone3_to_tone


class MakeMandarin(MakeDict):
    def __init__(self, out_path, overwrite_pinyin, add_pinyin, transdict, user_dict):
        super().__init__(out_path, overwrite_pinyin, add_pinyin, transdict, user_dict)

    def load_dict(self):
        # 获取词组
        with open("data/cedict_ts.u8", "r", encoding="utf-8") as f:
            for line in f:
                res = re.search(r"(.*[\u4e00-\u9fa5]) (.*[\u4e00-\u9fa5]) \[([\w :]+)] (\{([\w :]+)})?", line)
                char = res.group(2) if res else None
                if char and not re.search("[0-9A-Za-z·:，]", char):
                    if res.group(3):
                        pinyin = res.group(3).lower().replace("u:", "v")
                        values = ["er5" if i == "r5" else i for i in pinyin.split(" ")]

                        self.phrase_pinyin_dict[char] = " ".join(values)

    def fill_unicode_pinyin(self):
        char_list = [chr(i) for i in range(0x4E00, 0x9FFF + 1)] + list(self.transdict.values())
        for i in char_list:
            text = zhconv.convert(i, "zh-cn")
            if self.default_pinyin.get(text) is None:
                pinyin = pypinyin.pinyin(text, style=pypinyin.TONE3)[0][0]
                if re.search(r"([^a-z\d])", pinyin) is None:
                    self.default_pinyin[text] = [pinyin]

    def make_dict(self):
        self.pos_dict.clear()
        with open(f"{self.out_path}/phrases_dict.txt", "w", encoding='utf-8') as f:
            for raw_phrase, raw_pinyin in self.phrases_dict_out.items():
                clip_pinyin = raw_pinyin.split(" ")
                phrase_size = len(raw_phrase)
                if 1 < phrase_size == len(clip_pinyin) <= 4:
                    tonePinyin = ",".join([tone3_to_tone(x) for x in clip_pinyin])
                    f.write(f"{raw_phrase}:{tonePinyin}\n")
                    for i, (text, pinyin) in enumerate(zip(raw_phrase, clip_pinyin)):
                        if text in self.map_keys:
                            self.pos_dict.setdefault(text, []).append(phrase_size)

        with open(f"{self.out_path}/phrases_map.txt", "w", encoding='utf-8') as f:
            for k, v in self.pos_dict.items():
                map_pos = "".join([str(x) for x in list(set(v))])
                f.write(f"{k}:{map_pos}\n")

        with open(f"{self.out_path}/word.txt", "w", encoding='utf-8') as f:
            for k, v in self.default_pinyin.items():
                if len(k) == 1:
                    v_list = ",".join([tone3_to_tone(item) for item in v if item])
                    f.write(f"{k}:{v_list}\n")

        with open(f"{self.out_path}/trans_word.txt", "w", encoding='utf-8') as f:
            for k, v in self.default_pinyin.items():
                t_k = zhconv.convert(k, "zh-hant")
                if t_k != k:
                    f.write(f"{t_k}:{k}\n")

            for k, v in self.transdict.items():
                if k != v and k not in self.default_pinyin.keys() and v in self.default_pinyin.keys():
                    f.write(f"{k}:{v}\n")


out_path = "dict/mandarin"
overwrite_pinyin = {
    "儿": "er5", "了": "le5", "呢": "ne5", "曾": "ceng2", "重": "chong2", "地": "de5", "藏": "cang2", "都": "dou1",
    "还": "hai2", "弹": "tan2", "着": "zhe5", "的": "de5", "哦": "o4", "盛": "sheng4", "哟": "you5", "喔": "o1",
    "湮": "yan1", "拓": "ta4", "系": "xi4", "谁": "shei2", "什": "shen2", "么": "me5", "扛": "kang2"
}

extra_pinyin = {"濛": "meng2", "尅": "kei2"}

chinese_transdict = {}
with open("data/fanjian.txt", "r", encoding="utf-8") as f:
    for line in f:
        k, v = line.strip('\n').split('	')
        if len(k) == 1:
            chinese_transdict[k] = v

with open("data/fanjian2.txt", "r", encoding="utf-8") as f:
    for line in f:
        k, v = line.strip('\n').split(',')
        if len(k) == 1:
            chinese_transdict[k] = v

user_dict = {}

with open("data/man_user.txt", "r", encoding="utf-8") as f:
    for line in f:
        k, v = line.strip('\n').split(':')
        user_dict[k] = v

MakeMandarin(out_path, overwrite_pinyin, extra_pinyin, chinese_transdict, user_dict)
