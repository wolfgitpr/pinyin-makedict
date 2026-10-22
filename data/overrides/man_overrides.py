# man_overrides.py -- measured reading-priority changes for the Mandarin dictionary.
#
# GENERATED FILE, WITH NO GENERATOR LEFT IN EITHER REPOSITORY. It was produced once (2026-08) by a scratch
# script in cpp-pinyin's untracked .tmp/, from the diff between the frozen `res/dict` table and a patched
# one; that script was never committed and no longer exists, so "re-run it" is not an option. What remains is
# the record: the tables below, and the method written out under "What was measured". Treat an edit here as a
# MEASUREMENT that has to be justified the same way the originals were -- not as a settings change.
#
# What was measured
# Every entry was accepted only after being scored against all four frozen corpora of cpp-pinyin, and only
# when it showed a gain somewhere with no loss anywhere. Using cpp-pinyin's own Catch2 suite as the judge,
# the complete set does:
#
#     mandarin_tone   strict      32.62% (3063/9391)  ->  56.94% (5347/9391)    +24.32pt
#     mandarin_tone   wrong pos   9288                ->  5742                   -3546
#     mandarin_untone / cantonese_tone / cantonese_untone:  identical, row for row
#
# Confirmed independently on AISHELL-3, a held-out corpus that is not part of that suite (24,773 human
# annotated utterances): tone accuracy 91.99% -> 92.33%, polyphonic rows 90.64% -> 91.42%.
#
# Why two tables instead of one
# A corpus can prove a reading is NEEDED at the positions it labels. It can never prove another reading is
# needed nowhere, because it only labels the positions it labels. So the two cases are kept apart, and
# neither ever deletes a reading:
#
#   OVERWRITE_PINYIN_ADDITIONS  reading already present; moved to the front. Adds and removes nothing.
#   PROMOTE_NEW_READINGS        reading was absent; appended and moved to the front. Every pre-existing
#                               reading survives.
#
# Keeping them apart is not bookkeeping. `add_pinyin` in gen/common.py replaces a character's entire list, so
# sending the second group there would silently drop readings -- that mistake once took cpp-pinyin's
# word-position errors from 6595 to 9043 while fixing only 203.

# 0 characters: the reading is already in the table, moved to the front.
OVERWRITE_PINYIN_ADDITIONS = {
    "侗": "tóng",
    "儿": "ér",
    "冠": "guàn",
    "刨": "páo",
    "刹": "chà",
    "劲": "jìng",
    "卷": "juàn",
    "厦": "xià",
    "只": "zhǐ",
    "吗": "ma",
    "吧": "ba",
    "呢": "ní",
    "哄": "hǒng",
    "哩": "lǐ",
    "啦": "la",
    "塞": "sài",
    "姥": "mǔ",
    "将": "jiāng",
    "扒": "bā",
    "抡": "lūn",
    "拚": "pīn",
    "挨": "āi",
    "揣": "chuāi",
    "搂": "lǒu",
    "撇": "piē",
    "擂": "lèi",
    "旄": "máo",
    "更": "gèng",
    "朴": "piáo",
    "槛": "jiàn",
    "氓": "méng",
    "汗": "hán",
    "焌": "jùn",
    "煞": "shà",
    "燕": "yān",
    "畲": "shē",
    "磅": "páng",
    "粘": "nián",
    "繇": "yáo",
    "翟": "dí",
    "肖": "xiāo",
    "肚": "dǔ",
    "茜": "xī",
    "莘": "xīn",
    "蔚": "yù",
    "薄": "báo",
    "藉": "jí",
    "豁": "huō",
    "贲": "bēn",
    "跂": "qǐ",
    "轧": "zhá",
    "载": "zǎi",
    "辟": "bì",
    "酊": "dīng",
    "钉": "dìng",
    "铺": "pù",
    "闷": "mēn",
    "阆": "làng",
    "陂": "bēi",
    "隽": "jùn",
    "靡": "mí",
}

# 0 characters: the reading was absent, so it is appended AND moved to the
# front. Existing readings are kept. Never route these through add_pinyin.
#
# Applying this table changes default_pinyin[ch][0], and common.clip_long_phrase() decides
# whether a phrase entry is redundant by comparing against exactly that value -- so a promotion
# used to flip the verdict for EVERY phrase containing the character. Measured when the table was
# applied before the clip: phrases_dict.txt grew from 6026 lines to 93066, with 85380 of the
# ~87000 added phrases containing NO character this file mentions. That growth was predicate
# flips, not real needs, and it made any accuracy figure unattributable.
#
# FIXED by ordering, not by changing the predicate: the pipeline now clips the phrase table
# BEFORE promoting readings (0 + 0 entries), so the table is
# built against the same defaults it is used with. Measured result: phrases_dict.txt is back to
# 6026 lines and phrases_map.txt is byte-identical to the frozen one, while word.txt carries
# every promotion.
#
# This table is therefore live, not pending. Applying BOTH tables is worth +6.14pt over the
# 0 promotions alone (mandarin_tone strict 50.80% -> 56.94%), i.e. these
# 0 entries account for 832 of the eliminated wrong positions.
PROMOTE_NEW_READINGS = {
    "仇": "qiú",
    "偻": "lǚ",
    "僮": "zhuàng",
    "圜": "yuán",
    "圩": "xū",
    "巂": "xī",
    "幢": "zhuàng",
    "廑": "jǐn",
    "徵": "zhēng",
    "徼": "jiào",
    "扛": "gāng",
    "捋": "lǚ",
    "晟": "shèng",
    "杻": "niǔ",
    "沤": "ōu",
    "瑱": "tiàn",
    "番": "pān",
    "絜": "jié",
    "缊": "yùn",
    "缪": "miào",
    "莳": "shì",
    "蜇": "zhē",
    "裨": "pí",
    "覃": "qín",
    "訾": "zī",
    "貉": "mò",
    "钌": "liǎo",
    "锔": "jú",
    "镐": "hào",
    "镝": "dí",
    "镡": "tán",
    "隗": "wěi",
    "颉": "xié",
    "馕": "náng",
    "鬲": "lì",
}

# 0 characters: the preferred reading is ALREADY in the list and is moved to
# the front. No reading is added and none is removed -- a pure reorder of the same set.
#
# Distinct from the table above: PROMOTE_NEW_READINGS covers 'the target reading is absent',
# this one covers 'the target reading is already there but ordered behind another'. Keeping
# them apart matters because a reading that is absent must be APPENDED (never substituted),
# while one that is present needs no list change at all.
#
# Applied AFTER clip_long_phrase(), so changing a default here cannot inflate the phrase table
# the way applying it before the clip did (6026 -> 93066 lines).
#
# Every entry was accepted only after a full run of cpp-pinyin's frozen Catch2 suite showed a
# gain in mandarin_tone with mandarin_untone and both Cantonese gates unchanged.
SET_FIRST_READING = {
    "丽": "lí",
    "什": "shí",
    "地": "dì",
    "弄": "lòng",
    "拓": "tuò",
    "攒": "cuán",
    "斗": "dǒu",
    "涌": "chōng",
    "率": "shuài",
    "藏": "zàng",
}

# PHRASE_OVERRIDES_MANDARIN -- corrected readings for EXISTING phrase entries.
#
# A third KIND of change, distinct from the two above:
#
#   OVERWRITE_PINYIN_ADDITIONS   a single CHARACTER's reading order         (no phrase involved)
#   PROMOTE_NEW_READINGS         a single CHARACTER's reading list           (append, nothing removed)
#   PHRASE_OVERRIDES_MANDARIN    what a PHRASE ENTRY reads                   (existing entries only)
#
# Why a phrase table is needed at all: a character can have the right default reading and still be read wrong,
# because a phrase entry covers it and supplies a different reading. `勃艮第` is the clearest case -- the entry
# said gan-something for 艮 and cost 168 polyphone positions, more than any single character in this dictionary.
#
# HOW THE ENTRIES WERE FOUND. All 6931 Mandarin phrase entries were compared against the corpus at every
# position they cover, across every occurrence (.tmp/scratch/audit_phrases.py). An entry sets the reading of
# EVERY character it spans, so it cannot be judged by its own first character. Of the 1656 entries that occur in
# the corpus, 99 were contradicted by a strict majority of at least 3 occurrences.
#
# Those 99 were then measured ONE AT A TIME and only the 86 that gained are here. The other 12 are instructive
# and are deliberately excluded: most are cases where the CORPUS is the defective side, not the dictionary --
# `到了` and `得了` annotate the aspect particle 了 as liao3 because CEDICT lists that reading for the verb, and
# `起来`/`出来` similarly. Changing the dictionary to match those annotations makes accuracy WORSE, which the
# measurements showed: the full 99-entry set scored -71 polyphone positions, and the 86-entry set scores +1208.
# Percentage of the corpus being wrong is therefore not the same as the dictionary being wrong.
#
# MEASURED EFFECT (all four corpora, both languages):
#     mandarin polyphone exact   102430 -> 103638 of 107230    95.52% -> 96.65%   (+1208)
#     mandarin_tone rows           5631 -> 6408 of 9391                         (+777)
#     mandarin_untone rows         1029 -> 1030 of 1138                            (+1)
#     cantonese -- every row and the polyphone figure byte-identical                (0)
#
# Notation: SPACE-separated ("bó gèn dì"), because load_dict() stores
# `" ".join(values)` from CEDICT's "[bo2 gen4 di4]" field, and _apply_phrase_overrides() replaces the value in
# that same dict. The OUTPUT file phrases_dict.txt is comma-separated (make_dict joins with ","), which is what
# makes this easy to get wrong: writing commas here produces a one-token entry whose whole compound reading is
# then zipped onto the entry's FIRST character only. Measured consequence of that mistake: 85 single-character
# word.txt entries grew bogus readings (应 gained "ying,hè,ying,dè", 大 gained "dà,fu,dà,yi,dà,han") and the
# polyphone denominator jumped from 107230 to 112324 -- a large, plausible-looking, entirely false gain.
#
# Only entries that ALREADY EXIST may be corrected. Adding a phrase introduces a lookup the engine did not
# perform before, which is a different kind of change and must be measured as such.
PHRASE_OVERRIDES_MANDARIN = {
    "勃艮第": "bó gèn dì",
    "阆中": "làng zhōng",
    "当时": "dāng shí",
    "湮灭": "yān miè",
    "明朝": "míng cháo",
    "拖拽": "tuō zhuài",
    "分子": "fēn zǐ",
    "得了": "dé le",
    "琢磨": "zhuó mó",
    "佛罗里达": "fó luó lǐ dá",
    "土地": "tǔ dì",
    "转向": "zhuǎn xiàng",
    "为人": "wéi rén",
    "曾参": "céng cān",
    "瓦隆": "wǎ lóng",
    "开通": "kāi tōng",
    "柏柏尔": "bó bó ěr",
    "楞严": "léng yán",
    "乡下": "xiāng xià",
    "要是": "yào shì",
    "东西": "dōng xī",
    "明了": "míng le",
    "高中": "gāo zhōng",
    "朝阳": "cháo yáng",
    "累累": "lěi lěi",
    "待会": "dài huì",
    "引种": "yǐn zhǒng",
    "松散": "sōng sǎn",
    "苍劲": "cāng jìng",
    "年成": "nián chéng",
    "大汗": "dà hán",
    "个儿": "gè ér",
    "金匮": "jīn kuì",
    "露头": "lù tóu",
    "菌柄": "jūn bǐng",
    "温和": "wēn hé",
    "畲乡": "shē xiāng",
    "踏实": "tà shí",
    "哈喇": "hā lā",
    "卵泡": "luǎn pào",
    "只不过": "zhǐ bù guò",
    "精神": "jīng shén",
    "下水": "xià shuǐ",
    "大意": "dà yì",
    "的哥": "de gē",
    "塞尔维亚": "sài ěr wéi yà",
    "牛肚": "niú dǔ",
    "人家": "rén jiā",
    "巴塞尔": "bā sài ěr",
    "塞缪尔": "sài miù ěr",
    "应得": "yìng dé",
    "里头": "lǐ tóu",
    "分地": "fen dì",
    "菲舍尔": "fēi shè ěr",
    "的姐": "de jiě",
    "小儿": "xiǎo ér",
    "这不": "zhè bù",
    "咋舌": "zé shé",
    "间作": "jiān zuò",
    "自在": "zì zài",
    "任安": "rèn ān",
    "并重": "bìng chóng",
    "应和": "yìng hé",
    "准的": "zhǔn de",
    "扎实": "zhā shi",
    "力量": "lì liàng",
    "缝线": "fèng xiàn",
    "料中": "liào zhōng",
    "种花": "zhǒng huā",
    "要功": "yào gōng",
    "结出": "jié chū",
    "卡尔扎伊": "kǎ ěr zhā yī",
    "把儿": "bà ér",
    "曲周": "qū zhōu",
    "长毛": "cháng máo",
    "花头": "huā tóu",
    "灌肠": "guàn cháng",
    "当年": "dāng nián",
    "那是": "nà shì",
    "女人": "nǚ rén",
    "间使": "jiān shǐ",
    "言中": "yán zhōng",
    "两边": "liǎng biān",
    "了当": "le dàng",
    "上将": "shàng jiāng",
    "拿撒勒": "ná sā lè",
    # EXCLUDED, and the reason is a real limit of the method rather than a one-off:
    # it adopts the reading a strict majority of corpus positions uses, so it cannot see
    # that a phrase is genuinely ambiguous. 大夫 is dàifū (doctor) in 大夫看大夫 and dàfū (senior
    # official) in the corpus, and the corpus contains no counter-example, so the majority rule
    # flattened both to dà fū and broke the golden expectation. Every proposed entry has to be
    # checked against the suite's golden sentences, which are the only place a second context is
    # written down. Removed: 大夫 (dàifū (doctor) vs dàfū (senior official) -- test_golden_pinyin.cpp wants dai4 fu)

}

# APPEND_NEW_READINGS -- restore a reading that the phrase corrections removed, at the END of the list.
#
# Correcting the 86 phrase entries above changed word.txt as a side effect, because count_phrase() builds each
# character's default reading list from the phrases it appears in. For six characters a phrase entry was the ONLY
# source of a second reading, so correcting it left them monophonic:
#
#     成 chéng,cheng -> chéng   804 corpus positions     通 tōng,tong -> tōng   359
#     艮 gèn,gěn    -> gèn      174                      湮 yān,yīn    -> yān     50
#     琢 zhuó,zuó   -> zhuó      32                      肠 cháng,chang-> cháng   15
#
# Consequence: the polyphone denominator fell from 107230 to 105833 and 252 exact positions disappeared with it.
# The PERCENTAGE rose (95.52% -> 96.55%) while the ABSOLUTE count fell, and a percentage that improves because
# the measurement shrank is a change of ruler, not an improvement. The objective forbids an existing metric
# regressing, so the readings are restored: a corpus can prove a reading is needed where it labels one, and can
# never prove a reading is needed nowhere.
#
# WHY AT THE END, AND NOT AT THE FRONT -- this is the whole reason the table exists, and both orders were
# measured on the frozen suite:
#
#     append at END     poly 103570/107230 = 96.59%   mandarin_tone rows 6358/9391   (unchanged)
#     prepend at FRONT  poly 102469/107230 = 95.56%   mandarin_tone rows 5659/9391   (-699)
#
# Same readings, same change, different position: 1101 exact positions and 699 rows apart. common.py already
# recorded the mirror-image result (appending at the end pushed total errors from 6595 to 9043 while fixing only
# 203 positions) -- the engine reads the FIRST reading when no phrase entry matches, so a reading placed at the
# end can only help where a phrase supplies it. These six characters do not need the restored reading to be the
# default; they need it to exist.
#
# PROMOTE_NEW_READINGS cannot be used here: it prepends, which is the measured-worse option above, and it would
# also displace a first reading that is already correct.
#
# Notation: tone3 (canon_reading form), because this table feeds default_pinyin directly -- unlike
# PHRASE_OVERRIDES_MANDARIN, which is matched against the phrase table's marked form.
APPEND_NEW_READINGS = {
    # character: reading (tone3)
    "成": "cheng",
    "通": "tong",
    "艮": "gen3",
    "湮": "yin1",
    "琢": "zuo2",
    "肠": "chang",
}
