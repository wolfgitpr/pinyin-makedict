"""Measured Cantonese corrections -- two tables, fixing two different failures.

Both are obtained by MEASUREMENT, never by judgement. Both are also deliberately CONSERVATIVE in the same way:
neither one deletes a reading, because no corpus can prove a reading is never needed -- it only marks the
positions it marks. Deleting a reading would leave the engine with no answer in whatever other context needed
it, and nothing here justifies that.

    SET_FIRST_READING_CANTONESE   changes the ORDER of a single character's readings. This is what the engine
                                  says when NO phrase entry applies. Pure reorder: nothing added, nothing
                                  removed.
    PHRASE_OVERRIDES_CANTONESE    changes what a PHRASE ENTRY reads. This is what the engine says when one DOES
                                  apply. Existing entries only; no entry is invented here.

The second table exists because the first provably cannot fix everything. The Cantonese sweep found 19
characters with many wrong positions whose best reorder measured exactly 0: their first reading was already the
one the corpus wants, and they were still read wrong. Only a phrase entry can produce that. 跌 is the proof --
default dit3, corpus wants dit3 at all 213 of its positions, wrong in 97 of them, because the entry `跌打` was
written tit3,daa2.

WHY THE OBVIOUS RULE FOR CHOOSING REORDERINGS IS WRONG
The sweep tries EVERY reading of every candidate and keeps the one that measures best:

    python .tmp/scratch/sweep_poly.py --lang cantonese --min-wrong 10 --limit 40

"Put the reading the corpus asks for most often first" was the first version of that sweep and it is measurably
wrong: of the 35 candidates it proposed, 20 measured exactly 0 and several negative. 到 is the clearest case --
the corpus asks for dou2 in 58% of 579 occurrences, but 241 of those accept BOTH dou2 and dou3, so moving dou2
forward destroys 239 passes to win 86 and measures -153. Under the corrected rule 到 measures 0, i.e. its
current order is already the best available and it is correctly left alone.

WHY THE VALUES ARE IN tone3 FORM WITHOUT TONE MARKS
Cantonese readings reach word.txt straight from ToJyutping as tone3 ("maa3"), and gen/cantonese.py writes them
without the to_marked() conversion gen/mandarin.py performs. Both mechanisms match an exact string, so an override
has to be written in the notation the pipeline actually holds. Marked form would not match anything and the
entry would be silently ignored -- which is why the generator now aborts instead of skipping when a target is
absent (a silent no-op is indistinguishable from "this change had no effect").

MEASUREMENTS: the per-entry numbers below are ISOLATED (single-entry) readings from the sweeps. The combined,
whole-set numbers came out of the same work and are NOT stored in this repository. The two sets legitimately
differ, because changing one reading changes which other positions pass.
"""

# Ordered by measured gain. Each value must already be present among the character's readings; the generator
# refuses to run otherwise, so a typo fails loudly rather than quietly doing nothing.
SET_FIRST_READING_CANTONESE = {
    # 嗎 wrong in 102 of 102 occurrences. The particle reading; the corpus never wants the maa1 that the
    # dictionary currently puts first.
    "嗎": "maa3",
    # 嚟 wrong in 42 of 52. lei4 is the ordinary written-Cantonese form.
    "嚟": "lei4",
    # 鱲 wrong in 33 of 33.
    "鱲": "laap6",
    # 玩 wrong in 32 of 32.
    "玩": "waan2",
    # 吓 wrong in 30 of 30.
    "吓": "haa5",
    # 更 wrong in 27 of 40.
    "更": "gang3",
    # 行 wrong in 70 of 149 -- a genuine word-sense split, and this only moves the default; the other reading
    # stays available for the contexts that need it. Corpus wants haang4 67 times against hang4 50.
    "行": "haang4",
    # Smaller but measured strictly positive.
    "處": "cyu3",
    "腸": "coeng2",
    "玉": "juk6",
    "園": "jyun2",
    "咪": "mai5",
    "隊": "deoi2",
    "被": "bei6",
    "頂": "deng2",
}

# Corrected readings for EXISTING phrase entries, in sanitized.txt notation (space-separated tone3) because that
# is exactly the form load_dict() stores in phrase_pinyin_dict.
#
# HOW THE ENTRIES WERE FOUND -- exhaustive, not judgemental
# Every one of the 1484 phrase entries was compared against the corpus at every position it covers, across all
# its occurrences. A phrase entry sets the reading of EVERY character it spans, so an entry cannot be judged by
# its own first character: `紀念` might have had a correct nim6 half and a wrong gei3 half, and only measuring
# both says which. Of the 311 entries that occur in the corpus at all, these 10 were contradicted by a strict
# majority of at least 3 occurrences. No others were found, which is a useful result in itself -- the phrase
# table is largely correct, and this repairs a few defects rather than a pattern.
#
# Each entry differs from sanitized.txt in exactly ONE position, which is not a coincidence: these are
# individual upstream reading errors.
#
# MEASURED EFFECT, whole set applied together, both languages, all four corpora:
#     cantonese polyphone exact  39551 -> 39712 of 40639   97.32% -> 97.72%   (+161)
#     cantonese_tone rows         5209 -> 5359 of 6352                       (+150)
#     cantonese_untone rows       5905 -> 6009 of 6352                       (+104)
#     mandarin -- every row and the polyphone figure byte-identical             (0)
#
# Only entries that ALREADY EXIST may be corrected. Adding a phrase introduces a lookup the engine did not
# perform before -- a different kind of change, to be measured as such rather than riding along inside a
# correction table. The generator aborts if a key here is absent.
PHRASE_OVERRIDES_CANTONESE = {
    # 97 wrong positions, the largest phrase defect in either language. Corpus wants dit3,daa2.
    "跌打": "dit3 daa2",
    # 紀: gei2 is what the corpus wants; gei3 ("to record") is CEDICT's reading for 紀念 read as a verb.
    "紀念": "gei2 nim6",
    # 道: dou6 in 大道.
    "大道": "daai6 dou6",
    # 扒: paa2 (to rake/pull) rather than paa4 (to climb).
    "扒飯": "paa2 faan6",
    "沒有": "mut6 jau5",
    # 數: sou3 (number) rather than ou3; 數據 is "data".
    "數據": "sou3 geoi3",
    # 企: kei5 (to stand) rather than kei2.
    "企業": "kei5 jip6",
    "河粉": "ho4 fan2",
    # 脾: bei2 -- the 脾 in 雞脾 (chicken drumstick); a different reading from 脾氣's pei4.
    "雞脾": "gai1 bei2",
    # 到: dou3 (arrive) after 睇.
    "睇到": "tai2 dou3",
}
