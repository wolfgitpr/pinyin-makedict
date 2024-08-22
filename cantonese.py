import re

import ToJyutping
import zhconv

from common import MakeDict


class MakeCantonese(MakeDict):
    def __init__(self, out_path, overwrite_pinyin, add_pinyin, transdict):
        super().__init__(out_path, overwrite_pinyin, add_pinyin, transdict)

    def load_dict(self):
        with open("data/cccedict-canto-readings.txt", "r", encoding="utf-8") as f:
            for line in f:
                res = re.search(r"(.*[\u4e00-\u9fa5]) (.*[\u4e00-\u9fa5]) \[([\w :]+)] (\{([\w :]+)})?", line)
                key = res.group(2) if res else None
                if key and not re.search("[0-9A-Za-z·:，]", key):
                    if res.group(5):
                        key = "".join(self.transdict.get(x, x) for x in list(key))
                        pinyin = res.group(5).lower()
                        values = [i.replace(":", "") for i in pinyin.split(" ")]
                        self.phrase_pinyin_dict[key] = " ".join(values)

    def fill_unicode_pinyin(self):
        char_list = [chr(i) for i in range(0x4E00, 0x9FFF + 1)]

        for text in char_list:
            jian = zhconv.convert(text, "zh-cn")
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

    def make_dict(self):
        self.pos_dict.clear()
        with open(f"{self.out_path}/phrases_dict.txt", "w", encoding='utf-8') as f:
            for raw_phrase, raw_pinyin in self.phrases_dict_out.items():
                clip_pinyin = raw_pinyin.split(" ")
                phrase_size = len(raw_phrase)
                if 1 < phrase_size == len(clip_pinyin) <= 4:
                    tonePinyin = ",".join(clip_pinyin)
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
                    v_list = ",".join([item for item in v if item])
                    f.write(f"{k}:{v_list}\n")

        with open(f"{self.out_path}/trans_word.txt", "w", encoding='utf-8') as f:
            for k, v in self.default_pinyin.items():
                t_k = zhconv.convert(k, "zh-hant")
                if t_k != k:
                    f.write(f"{t_k}:{k}\n")

            for k, v in self.transdict.items():
                if k != v and k not in self.default_pinyin.keys() and v in self.default_pinyin.keys():
                    f.write(f"{k}:{v}\n")


out_path = "dict/cantonese"

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

# 按繁简字读音相同处理
MakeCantonese(out_path, {}, {}, chinese_transdict)
