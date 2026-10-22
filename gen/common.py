import os
import pathlib
import sys
import tempfile
from collections import Counter

from pypinyin.style._tone_convert import tone3_to_tone, tone_to_tone3


# 仓库根。所有读与写都从这里派生，因此与调用者的 cwd 无关。
REPO = pathlib.Path(__file__).resolve().parent.parent

# 让仓库根进 `sys.path`。原因是本目录的脚本**按路径直接跑**（`python gen/mandarin.py`），
# 于是 Python 只把 `gen/` 放进 `sys.path`，而 `data/overrides/*.py` 是**仓库根下**的模块：
# 少了这一行，`from data.overrides.man_overrides import ...` 会报 `No module named 'data'`。
# 放在 common.py 里而不是每个生成器各写一遍，是因为三个生成器都先 import 本模块。
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def source_path(name: str) -> pathlib.Path:
    """`data/sources/` 下的一份**下载来的**输入（语料本体，从不被 import）。与 cwd 无关。"""
    return REPO / "data" / "sources" / name


def override_path(name: str) -> pathlib.Path:
    """`data/overrides/` 下的一份**手写**输入（本仓维护，其中有 Python 模块）。与 cwd 无关。"""
    return REPO / "data" / "overrides" / name


def out_path(*parts: str) -> pathlib.Path:
    """out/ 下的产出位置（同样是绝对路径）。"""
    return REPO / "out" / pathlib.Path(*parts)


def write_lf_atomically(path: pathlib.Path, lines) -> None:
    """把 `lines` 以 **LF-only UTF-8** 写进 `path`，并且是原子的。

    冻结表需要两条普通 open(..., "w") 给不了的性质：
      * 任何平台都是 LF —— 消费方逐字节比对，而它自己那份是 LF（文本模式
        给 2 字节的文件写出 3 字节）；
      * 全有或全无 —— 写到一半崩掉会留下一个**还能被解析**的截断表，半成品词典因此看起来
        是合法的。同目录下 os.replace 在 POSIX 与 Windows 上都是原子的。
    """
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # 空表是要报的失败，不是一个文件。调用方传进来的都是语料上的生成器：空说明语料空了、被过滤光了，
    # 或者某次查键失效了 —— 而此时写一张 0 字节的表并报告成功，正好是"看起来完整的坏词典"。
    materialised = list(lines)
    if not materialised:
        raise MakeDictError(f"{path.name}: refusing to write an empty table -- the generator produced no "
                         f"rows, which is a failure to report, not a file to ship")
    lines = materialised
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for line in lines:
                handle.write(line)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


#: 本生成器写出的数据格式号：每个方言目录的 `format.txt` 里只有一行 "2"。
#:
#: 只留一处常量，因为它是**跨仓契约**而不是本仓设置：消费方 cpp-pinyin 的 `checkDictFormat` 会拒绝它
#: 不认识的标记（见 cpp-pinyin `docs/STABILITY.md` §4.5），而出厂副本在
#: `cpp-pinyin/data/dialects/{mandarin,cantonese}/format.txt`。只改这个数字、不改引擎和那两个文件，
#: 得到的就是坏安装，不是一次重新构建。
DATA_FORMAT_VERSION = 2


def load_fanjian(exclude=None) -> dict:
    """data/sources/fanjian.txt(制表符) + data/sources/fanjian2.txt(逗号)，只收单字键，后者覆盖同名键。

    `exclude` 是调用方的 not_fan 集合（只有普通话传）。
    """
    excluded = exclude if exclude is not None else ()
    table = {}
    for line in source_path("fanjian.txt").read_text(encoding="utf-8").splitlines():
        key, value = line.split("\t")
        if len(key) == 1 and key not in excluded:
            table[key] = value
    for line in source_path("fanjian2.txt").read_text(encoding="utf-8").splitlines():
        key, value = line.split(",")
        if len(key) == 1 and key not in excluded:
            table[key] = value
    return table


# ê 折叠成 e 是**方言属性**，所以走 `MakeDict(preserve_e_hat=...)` 构造参数而不是模块级状态：模块级
# 状态在"一个进程里先后跑两个方言"时会静默互染。实测代价：某语种金标 86.91% → 60.17%（−26.74pt），
# 因为 ê 与 e 被折成同一个韵母，词条的 zêg8 与字表的 zeg8 永远对不上。普通话折叠是对的（pypinyin 只在
# ê/e 可互换的音节写 ê），默认 False 保持普通话/粤语既有行为逐字节不变。
# 依据：docs/DIALECT_EXTENSION_RECORD.md 第 4 节（无声调化必须按语种实现）。


def canon_reading(r: str, preserve_e_hat: bool = False) -> str:
    """把读音规范化为唯一的 **TONE3 数字**写法，中性调统一写作 5。

    为什么规范形式选 TONE3 而不是带调符（这一点是实测纠正过来的）：
    fill_unicode_pinyin() 从 pypinyin 取到的本来就是 TONE3（pai4），所以 TONE3 是流水线里天然已有的
    表示；选带调符会把它整体改写成另一种写法，改动会顺着 default_pinyin 传到下游的
    clip_long_phrase()。实测后果：default_pinyin 里同一个读音以两种写法各留一份，6272 个字受影响、
    1162 个字的**首位**读数被改动，短语表从 6026 行涨到 7872 行。只把比较键统一到流水线原有写法，
    才是不改变任何既有语义的做法。

    为什么不能直接用 pypinyin 的转换（两条都是实测出来的）：
      * tone_to_tone3 对中性调不收敛：tone_to_tone3("ma") 得 "ma"，与 "ma5" 不相等，
        所以 吗/吧/啦 三个字仍会被当成两个读音。
      * tone3_to_tone **不幂等**：对已经带调符的值再调用会破坏它（"me" -> "me" -> "me,me"），
        实测直接造成 25 个字出现重复读音。

    本函数的幂等性由结构保证：整数调一进来就被剥掉，再走一遍时输入已是纯音节或 5，路径不变。

        ma / ma5    -> ma5
        MEI5        -> mei5
        dong4/dòng  -> dong4
        nv3 / nǚ    -> nv3
        lv4 / lǜ    -> lv4
        er  / er5   -> er5
        er2 / ér    -> er2

    ü 统一写成 **v**（pypinyin 的写法），不转成 u：lù 与 lǜ 是两个不同的音节，必须一直可区分。
    写成 u 会丢掉这个区别，取词时无法还原——实测后果是 路/论/露/怒 等约 45 个字的读音被写成 lǜ/nǜ，
    比原始字典**多**了 917 个错误位置（56.94% 掉到 52.66%）。规范形式里保住 v，to_marked 就不需要
    猜测，直接用「v -> ü」出字即可。

    写出前另有一步把它转成带调符（word.txt 的既有格式），两处职责分开。
    """
    if not r:
        return r
    # tone_to_tone3 同时胜任两条分支：带调符转成数字（dòng -> dong4），已是数字则原样返回。
    r = tone_to_tone3(r)
    if r.endswith("-1"):                 # uniform 写法（MEI5 -> mei-1、ê1 -> e1-1）
        r = r[:-2]
    syllable = r[:-1] if (r and r[-1].isdigit()) else r
    tone = r[-1] if (r and r[-1].isdigit()) else "5"
    # preserve_e_hat is a PARAMETER, not module state: two dialects in one process must not be able
    # to change each other's folding (the module-global version did, silently -- see the note above).
    if not preserve_e_hat:
        syllable = syllable.replace("ê", "e")
    return syllable + tone


def to_marked(r: str) -> str:
    """规范形式（TONE3）-> 带调符，供 word.txt / phrases_dict.txt 输出。

    只做**确定性**的改写，不猜测：
      * v -> ü：规范形式用 pypinyin 的 v 记 ü（nv3 / lv4），输出要求写 ü。
      * 中性调：本仓库写不带调符（ma5 -> ma），tone3_to_tone 会保留 "ma5"。
      * ê -> e：与字典既有写法一致。

    先前这里靠「基础音节以 nu/lu 开头」反推 ü，是错的：lù（路）与 lǜ（吕）本来是两个音节，
    反推把 lù 写成了 lǜ，实测让 45 个字出错、多出 917 个错误位置。既然规范形式保住了 v，
    就不需要反推，写成 v 的才是 ü。
    """
    m = tone3_to_tone(r.replace("v", "ü")) if "v" in r else tone3_to_tone(r)
    if m.endswith("5"):
        m = m[:-1]
    return m.replace("ê", "e")



# 精确版本号，不写范围：这两个包都**自带数据**，而数据在版本之间动过。
# pypinyin 0.55.0 对 0.54.0：word.txt 背后的字典从 41651 条变成 41923 条，U+9FA6..U+9FFF 新增 23 个字、
# 5 个读音被改写；实测 0.55.0 逐字节复现四张普通话表，0.54.0 不能。
# ToJyutping 3.1.0 -> 3.2.0 改了 噚 的候选**顺序**（集合与首读音都没变）。
# 升依赖等于一次**数据变更**：真要升就同一次改动里跑 check_drift.ps1 并重新冻结 cpp-pinyin 的门禁
# （TOOLING.md）；无意中的升版必须在这里响亮失败，而不是默默产出一份不同的词典。
EXPECTED_VERSIONS = {
    "pypinyin": "0.55.0",
    "ToJyutping": "3.2.0",
    "zhconv": "1.4.3",
}

# A wrong version is a wrong dictionary, so this is a hard stop rather than a warning.
STRICT_VERSIONS = os.environ.get("PINYIN_MAKEDICT_ALLOW_VERSION_DRIFT") != "1"


class MakeDictError(Exception):
    """本包**有意**抛出的每一种拒绝共用一个基类。

    为什么要一个基类：拒绝原本分三种信号 —— `ValueError`（要写空表）、`RuntimeError`（版本漂移、行数低于
    下限）和 `SystemExit`（数据表不适用）。前两种能被 `except Exception` 接住，但 `SystemExit` 派生自
    `BaseException`，把生成器当库用的宿主根本接不住 —— 拒绝会直接结束**宿主**进程。现在调用方只需要接
    `MakeDictError`，各入口的 `main()` 会把它变成退出码加一条 stderr 消息。

    它**有意**不继承 `RuntimeError`/`ValueError`：顺手接住那两类的调用方本来就是碰巧接住的，让这种写法
    继续工作等于把这个类要消除的歧义保留下来。
    """


def parse_user_dict_lines(lines) -> dict:
    """`key:value` 行 -> dict。空行与 `#` 行跳过；值里的其余冒号原样保留。

    抽成函数是为了让规则能脱离磁盘文件被测：唯一调用方 `mandarin.load_configured_inputs()` 吃的那个文件
    当前是空的，规则留在里面就永远跑不到。
    """
    parsed = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if not key:
            raise MakeDictError(f"malformed user-dict line (no key): {line!r}")
        parsed[key] = value.strip()
    return parsed


def check_dependency_versions(strict=None) -> list:
    """Verify that the installed package versions are the ones the frozen tables were built with.

    Returns the list of problems (empty when clean). Raises when strict. Set
    PINYIN_MAKEDICT_ALLOW_VERSION_DRIFT=1 to downgrade this to a warning, e.g. when intentionally
    evaluating a bump.
    """
    import importlib

    if strict is None:
        strict = STRICT_VERSIONS
    problems = []
    for name, want in EXPECTED_VERSIONS.items():
        try:
            mod = importlib.import_module(name)
        except ImportError as e:  # noqa: PERF203
            problems.append(f"{name} is not installed ({e})")
            continue
        got = getattr(mod, "__version__", None)
        if got is None:
            # ToJyutping ships no __version__; fall back to the installed distribution metadata.
            try:
                from importlib.metadata import version as _dist_version
                got = _dist_version(name)
            except Exception:  # noqa: BLE001
                got = "unknown"
        if got != want:
            problems.append(f"{name}: installed {got}, expected exactly {want}")

    if problems and strict:
        raise MakeDictError(
            "dependency version drift -- this generator would emit a DIFFERENT dictionary than the "
            "one cpp-pinyin ships:\n  - " + "\n  - ".join(problems)
            + "\n\nFix: pip install -r requirements.txt"
            + "\nDeliberate bump: PINYIN_MAKEDICT_ALLOW_VERSION_DRIFT=1, then re-run "
              "tools/check_drift.ps1 and re-freeze the cpp-pinyin gates in the same change."
            + "\nSee TOOLING.md."
        )
    return problems


class MakeDict:
    def __init__(self, out_path, overwrite_pinyin, add_pinyin, trans_dict=None, user_dict=None, force_mono=None,
                 promote_new_readings=None, set_first_reading=None, phrase_overrides=None,
                 append_new_readings=None, preserve_e_hat=False):
        """`force_mono` 默认 `{}` 会变成所有实例共享的可变默认值 —— 这个坑是静默的。所以这里是 `None`
        + 新建 set：子类改了它，影响不到另一个子类。其余参数**有意**保持位置参数：生成器都按位置调用。"""
        if trans_dict is None:
            trans_dict = {}
        if user_dict is None:
            user_dict = {}
        if promote_new_readings is None:
            promote_new_readings = {}
        if set_first_reading is None:
            set_first_reading = {}
        if phrase_overrides is None:
            phrase_overrides = {}
        if append_new_readings is None:
            append_new_readings = {}
        # 两个方言都从这里构造，产物又都依赖钉版数据（普通话走 pypinyin、粤语走 ToJyutping），
        # 所以版本校验放在这一个咽喉点，而不是每个入口各写一次。
        check_dependency_versions()
        # Before the first canon_reading() call below: the flag decides how ê folds, so it must exist
        # before any reading is normalised.
        self.preserve_e_hat = preserve_e_hat
        self.out_path = out_path
        # 同样统一到规范形式。overwrite_pinyin 的字面量本来写的是带调符（如 侗:"tóng"），
        # 而 phrase_map 里的读音会被下面的 count_phrase() 也规范化；两边写法一致后，
        # 那边那句过滤 `x != v` 才能匹配到同一个读音。若写法不一致，同一个读音会以两种写法各留
        # 一份，输出出现重复——实测：侗 生成 tóng,dòng,tóng，而正确形式是 tóng,dòng。
        self.overwrite_pinyin = {k: canon_reading(v, preserve_e_hat) for k, v in overwrite_pinyin.items()}
        self.add_pinyin = add_pinyin
        self.promote_new_readings = promote_new_readings
        self.set_first_reading = set_first_reading
        self.phrase_overrides = phrase_overrides
        self.append_new_readings = append_new_readings
        self.transdict = trans_dict
        self.user_dict = user_dict
        self.force_mono = set() if force_mono is None else force_mono

        self.phrases_dict_out = {}
        self.phrase_pinyin_dict = {}
        self.pos_dict = {}
        self.phrase_map = {}
        self.default_pinyin = {}
        self.pos_map_dict = {}
        self.map_keys = []
        self.short_phrase_dict = {}
        self.new_phrase_dict = {}

        print(f"make dict -> {self.out_path}")

        os.makedirs(self.out_path, exist_ok=True)
        self.load_dict()
        if self.user_dict:
            self.phrase_pinyin_dict.update(self.user_dict)
        self.count_phrase()
        self.fill_unicode_pinyin()
        self.add_default_pinyin()
        self.extract_polyphone()
        # 短语表必须**在**提升默认读音之前裁剪：clip_long_phrase() 用 default_pinyin[ch][0] 判断词条是否
        # 最小，提升会改这个值，把包含该字的**每一条**短语的判定翻面——实测先提升：phrases_dict.txt 从
        # 6026 行涨到 93066 行，新增的 85380 条不含任何被改动的字（是判定翻转，不是真实需求）。
        # 短语表是相对**原始**默认读音而言最小的（冻结短语表正是原始生成器逐字节复现的），所以先按原始默认
        # 裁剪、再提升，提升只影响 word.txt；clip_long_phrase 只读不写，两者先后对它是等价的。
        self.clip_long_phrase()
        self.promote_new_readings_apply()
        # Append-at-the-end restorations, for readings that a phrase correction removed. Placed with the other
        # reading changes (after the clip) for the same reason: the clip judges a phrase entry by
        # default_pinyin[ch][0], and appending does not touch index 0, so the phrase verdict cannot flip.
        self.append_new_readings_apply()
        # 实测得到的首位读音改写，同样放在裁剪之后，理由见 set_first_reading_apply()。
        self.set_first_reading_apply()
        # 写出前的最后一道保证：默认读音统一为 canon_reading 的规范写法并去重。
        #
        # 不能只依赖 count_phrase() 里的规范化：那之后还有来源会写入未规范化的值——
        # fill_unicode_pinyin() 的 tone3 结果、add_pinyin、promote_new_readings 与
        # set_first_reading 的手写条目。只要有一处写法不同，同一读音就会以两种写法各留一份，
        # 输出出现重复项（实测：么 写出 me,me，扛 写出 káng,káng）。
        self.canonicalise_default()
        self.make_dict()

    def load_dict(self):
        pass

    # 短语表的定点更正，默认无操作，由各语言按需提供。
    # 与 SET_FIRST_READING 不同：那个改**单字默认读音的顺序**（只重排，影响"没有词条命中时读什么"），这个改
    # **词条本身读什么**（影响"该词条覆盖的位置读什么"）。一个字的默认读音已最优却仍大量读错，只能是词条在
    # 插手——粤语 跌 默认 dit3 本是对的，因词条「跌打」写成 tit3,daa2 而错了 97 次。只允许替换已存在的词条，
    # 键不在词表里直接报错（新增词条等于让引擎多做一次原本不做的查表，是另一类改动）；值须写成 sanitized.txt 的写法（空格分隔 tone3）。
    def _apply_phrase_overrides(self):
        overrides = getattr(self, "phrase_overrides", None) or {}
        missing = []
        for k, v in overrides.items():
            if k not in self.phrase_pinyin_dict:
                missing.append(k)
                continue
            self.phrase_pinyin_dict[k] = v
        if missing:
            raise MakeDictError(
                "phrase_overrides names entries that are not in the phrase source: "
                + ", ".join(missing)
                + "\nThis table corrects existing entries only. Adding a phrase is a different kind of change "
                  "(it introduces a lookup the engine did not perform before) and must not ride along silently."
            )

    def count_phrase(self):
        # 短语表的定点更正必须在任何派生步骤之前落地。
        # 为什么不能放到最后直接改 phrases_dict.txt：那张表是**派生**的，不是照抄 sanitized.txt——clip_long_phrase()
        # 按「该词能不能用默认读音拼出来」决定一条词条留不留，所以改一条短语的读音会改它自己的去留，顺带也改
        # **别的**长词的裁剪结果（长词首尾两字与短词表同音就被裁掉）。放最后改等于绕过这套规则，得到的表与
        # 「一次生成」不是同一个东西；放在这里（load_dict 之后）等价：后面的词频统计、去留判定、规范化看到的都是更正后的读音。
        self._apply_phrase_overrides()

        # 统一读音写法后再统计频率：phrase_map 的读音来自 CEDICT（带调符 "dòng"），fill_unicode_pinyin() 给的是
        # TONE3（"dong4"）。Counter() 会把同一个读音按两种写法各数一次，词频排序不可信，而且那句 `x != v` 的过滤
        # 匹配不到同一个读音，输出里同一个读音会留下两份——实测侗 生成 tóng,dòng,tóng（应为 tóng,dòng），共 61 个字
        # 受影响，全部出现在 CEDICT 票数持平的场合。统一到 canon_reading 的规范形式（TONE3）；该函数幂等，转换无条件安全。
        for k, v in self.phrase_pinyin_dict.items():
            values = v.split(" ")
            phrase_size = len(values)
            if len(k) < 10:
                for text, pinyin in zip(k, values):
                    if phrase_size > 1:
                        self.pos_dict.setdefault(text, []).append(phrase_size)
                    self.phrase_map.setdefault(text, []).append(pinyin)
        # 统计频率
        for k, v in self.phrase_map.items():
            value = v
            count = Counter(value)
            sorted_list = sorted(count.items(), key=lambda x: x[1], reverse=True)
            self.phrase_map[k] = [word for word, count in sorted_list]

        # 默认拼音，{k:中文,v:最高频拼音}
        self.default_pinyin = {k: v for k, v in self.phrase_map.items()}
        for k, v in self.overwrite_pinyin.items():
            self.default_pinyin[k] = [v] + [x for x in self.default_pinyin.get(k, []) if x != v]

    # 补充Unicode码中剩余中文:拼音
    def fill_unicode_pinyin(self):
        pass

    def add_default_pinyin(self):
        for k, v in self.add_pinyin.items():
            self.default_pinyin[k] = [v]

    # 追加读音并置顶。与另外几张表的区别：overwrite_pinyin 要求该读音**本已存在**、只移到首位（纯重排，不增不减）；
    # add_pinyin 把该字整个读音列表**替换**为 {v}（原有读音全丢）；set_first_reading 目标读音本已在列表里、只置顶。
    # 为什么必须单独有"追加"这张表：语料只能证明"某读音在它标注的那些位置被需要"，**永远无法证明**另一读音在任何地方
    # 都不被需要，所以在原读音上做替换是一条会静默收窄覆盖面的路径；"追加 + 置顶"是不含删除的那个版本。实测（cpp-pinyin
    # 冻结 Catch2 套件，四语料）：35 个字属此类，`readings removed = 0` 必须守住，替换写法曾把词位错误 6595 拉到 9043 只修好 203 处。须在 add_default_pinyin() **之后**调用：那一步会覆盖整个列表，先追加等于白做。
    def promote_new_readings_apply(self):
        for k, v in self.promote_new_readings.items():
            rest = [x for x in self.default_pinyin.get(k, []) if x and x != v]
            self.default_pinyin[k] = [v] + rest

    # 追加读音到列表**末尾** —— 不置顶、不删除。位置（首位/末位）是**行为**不是排版：没有词条命中时
    # 引擎读的是**首位**读音，把读音追加到末尾正是那条实测（整体错误数 6595 涨到 9043、只修好 203 处）
    # 发生的场景；反过来把本应保持首位的读音**置顶**，会把正确的首位读音顶掉。同一份读音只差位置，
    # 实测就差 1101 个精确位置和 699 行 —— 这就是这张表存在的理由。
    def append_new_readings_apply(self):
        for k, v in self.append_new_readings.items():
            cur = self.default_pinyin.get(k, [])
            if v not in cur:
                self.default_pinyin[k] = [x for x in cur if x] + [v]


    # 把某个字的首位读音改成实测得到的答案，**其余读音全部保留**（不移除任何候选）。
    #
    # 与 promote_new_readings 的分工：那个用于「目标读音原先不在列表里」，这个用于「目标读音本来就在、
    # 只是排在后面」。二者的共同点是都只改顺序、不删读音——删读音会让引擎在别的上下文里无解。
    #
    # 位置在 clip_long_phrase() **之后**，这是刻意的：短语过滤拿 default_pinyin[ch][0] 判断词条是否
    # 冗余，在这里改默认值就不会引起短语表翻面（那曾经把短语表从 6026 行撑到 93066 行）。
    def set_first_reading_apply(self):
        for k, v in self.set_first_reading.items():
            cur = self.default_pinyin.get(k)
            if cur is None:
                continue
            rest = [x for x in cur if x and x != v]
            self.default_pinyin[k] = [v] + rest

    # 规范化目标是 **TONE3**、不是 word.txt 的带调符（后者由 to_marked() 写出时转换）：这样下游
    # clip_long_phrase() 看到的 default_pinyin[ch][0] 才与流水线原本写法一致；改用带调符会让它整体
    # 换写法，短语表从 6026 行涨到 7872 行。
    def canonicalise_default(self):
        for k, v in self.default_pinyin.items():
            self.default_pinyin[k] = list(dict.fromkeys(canon_reading(x, self.preserve_e_hat) for x in v))

    # 提取多音字
    def extract_polyphone(self):
        # 中文 -> 该字参与的短语长度集合。**有序**，不存未排序的 set：set 的迭代顺序是实现细节
        # （字符串还跨进程变化），而这些数字要拼进 phrases_map.txt —— 输出字节不能依赖哈希表布局。
        self.pos_dict = {k: sorted(set(v)) for k, v in self.pos_dict.items()}
        for k, v in self.phrase_map.items():
            if len(v) > 1:
                self.pos_map_dict[k] = (self.phrase_map[k], "".join([str(x) for x in self.pos_dict[k]]))
        # 多音字列表
        self.map_keys = self.pos_map_dict.keys()

    # 裁剪长词
    def clip_long_phrase(self):
        # 2字短语
        for k, v in self.phrase_pinyin_dict.items():
            if len(k) == 2:
                self.short_phrase_dict[k] = v

        # 以短词裁剪长词
        for raw_phrase, raw_pinyin in self.phrase_pinyin_dict.items():
            if len(raw_phrase) > 2:
                clip_phrase = raw_phrase
                clip_pinyin = raw_pinyin.split(" ")

                # 长词首尾2个字在短词列表内且读音相同者均删除，重复操作数次
                for _ in range(3):
                    short_phrase = clip_phrase[:2]
                    if short_phrase in self.short_phrase_dict.keys():
                        if self.short_phrase_dict[short_phrase] == " ".join(clip_pinyin[:2]):
                            clip_phrase = clip_phrase[2:]
                            clip_pinyin = clip_pinyin[2:]

                    short_phrase = clip_phrase[-2:]
                    if short_phrase in self.short_phrase_dict.keys() and self.short_phrase_dict[
                        short_phrase] == " ".join(clip_pinyin[-2:]):
                        clip_phrase = clip_phrase[:-2]
                        clip_pinyin = clip_pinyin[:-2]

                # 剩余词语，读音与默认拼音相异者输出
                if len(clip_phrase):
                    sta = False
                    for idx in range(len(clip_phrase)):
                        text = clip_phrase[idx]
                        if self.default_pinyin.get(text) and idx < len(clip_pinyin) and clip_pinyin[idx] != \
                                self.default_pinyin[text][0]:
                            sta = True
                            break
                    if sta:
                        self.phrases_dict_out[raw_phrase] = raw_pinyin

        # 可用默认拼音拼读的2字短词筛除，剩余加入输出
        for k, v in self.short_phrase_dict.items():
            if self.default_pinyin.get(k[0]) and self.default_pinyin.get(k[1]):
                search = f"{self.default_pinyin.get(k[0])[0]} {self.default_pinyin.get(k[1])[0]}"
                if search != v:
                    self.phrases_dict_out[k] = v

    # 输出
    def make_dict(self):
        pass

    # ---- shared table writers ----------------------------------------------------------------------
    # 两个方言原本各写一份 phrases_dict.txt / phrases_map.txt / word.txt，形状相同、只有三处不同，
    # 现在统一放在这里：format_reading()（普通话转带调符，粤语原样写出）、phrase_allowed()（普通话
    # 丢掉含 force_mono 字的短语）、map_key_allowed()（普通话也把这些字从 phrases_map.txt 里去掉）。
    # 粤语传 force_mono=[] 且不覆写读音钩子，四张表由同一份代码的默认行为产出。
    # trans_word.txt **有意**不在这里：两个方言的来源不同，参数化只会更难读。
    def format_reading(self, reading):
        """How one reading is rendered on the way out. Default: verbatim (Cantonese)."""
        return reading

    def phrase_allowed(self, raw_phrase):
        """May this phrase be written at all? Default: not if it contains a force_mono character."""
        for text in self.force_mono:
            if text in raw_phrase:
                return False
        return True

    def map_key_allowed(self, key):
        """May this character appear in phrases_map.txt? Default: not if it is force_mono."""
        return key not in self.force_mono

    def extra_tables(self):
        """方言自己的表，走和另外三张表**同一条** staging 路径。

        为什么要这个钩子：`trans_word.txt` 以前由各生成器在 `write_three_tables()` 返回**之后**、也就是
        在 `format.txt` 之后才写。在那个窗口里崩掉，会留下一个自称"这一代已经写完"、却握着缺失的或上一代
        `trans_word.txt` 的目录 —— 正是标记要防的混代状态。所以方言产出的每一张表都从这个 dict 回去，
        由 `write_three_tables` 在盖章之前统一 staging、查下限、落位。

        返回 `{filename: lines}`；默认不产出任何表。
        """
        return {}

    def write_three_tables(self):
        # 方言目录自报它用哪个数据格式代写出，引擎读任何表之前先校验这个标记（见 cpp-pinyin
        # docs/STABILITY.md §4.5）。这是那个承诺的生产侧，写在这里 —— 所有生成器都调的那一个地方。
        #
        # 每张表都走 write_lf_atomically：LF（消费方逐字节比对，自己那份是 LF；文本模式会给 2 字节的
        # 文件写出 3 字节）+ 原子替换（半截表仍然可解析，这正是"看起来合法的坏词典"的来源）。
        # 顺序上 format.txt **最后**写：它是"这一代数据已写完"的标记，先写它等于让半成品目录自报完成。
        target = pathlib.Path(self.out_path)
        # 目录级 staging：四张表先写进同级的 `.staging` 目录，全部成功后才逐表 `os.replace` 进正式目录，
        # 最后才写 format.txt。少了这一步仍有一种中间态 —— 前两张表已是新一代、第三张还是旧的，而目录
        # 此刻只是"没有标记"，不是"没有坏数据"。代价：多一次同盘 rename（缺省是原子的，且不跨文件系统）。
        staging = target.with_name(target.name + ".staging")

        # 先删标记，再写表：只靠"最后写标记"挡不住**同代重生成** —— 崩在中间留下的是"新表 + 旧标记 = 2"，
        # 那是一棵看起来完整、实际混合了两代的目录，引擎读它不会报错。删掉标记之后，同样的崩溃留下的是
        # "没有标记"的目录，而引擎对"有 dialect.json 却没有 format.txt"是**拒绝**的，于是坏状态变成响声
        # 而不是坏词典。
        (target / "format.txt").unlink(missing_ok=True)

        self.pos_dict.clear()
        lines = []
        for raw_phrase, raw_pinyin in self.phrases_dict_out.items():
            clip_pinyin = raw_pinyin.split(" ")
            phrase_size = len(raw_phrase)
            if 1 < phrase_size == len(clip_pinyin) <= 4 and self.phrase_allowed(raw_phrase):
                tonePinyin = ",".join(self.format_reading(x) for x in clip_pinyin)
                lines.append(f"{raw_phrase}:{tonePinyin}\n")
                for i, (text, pinyin) in enumerate(zip(raw_phrase, clip_pinyin)):
                    if text in self.map_keys:
                        self.pos_dict.setdefault(text, []).append(phrase_size)
        write_lf_atomically(staging / "phrases_dict.txt", lines)

        write_lf_atomically(
            staging / "phrases_map.txt",
            (f"{k}:{''.join([str(x) for x in sorted(set(v))])}\n"
             for k, v in self.pos_dict.items() if self.map_key_allowed(k)))

        write_lf_atomically(
            staging / "word.txt",
            (f"{k}:{','.join(self.format_reading(item) for item in v if item)}\n"
             for k, v in self.default_pinyin.items() if len(k) == 1))

        # 方言自己的表（今天只有 `trans_word.txt`）也进**同一个** staging 目录，于是"标记最后写"这条
        # 规则同样覆盖它们 —— 见 `extra_tables()`。它们在查下限之前、盖章之前写入，并在下面同一轮落位。
        extras = self.extra_tables()
        for _extra_name, _extra_lines in extras.items():
            write_lf_atomically(staging / _extra_name, _extra_lines)

        # 盖章前的最后一道闸。`write_lf_atomically` 已经拒绝**空表**；这里是同一条规则的另一半：表非空
        # 但小得不合常理，说明语料是被读错了而不是没有。下限离真实数字很远（实测 word.txt 17,525 /
        # phrases_dict.txt 6,975 / phrases_map.txt 1,003 行），所以它抓的是"哪里出了大问题"，不是
        # "词典大小变了一点"。
        for _name, _floor in (("word.txt", 1000), ("phrases_dict.txt", 100), ("phrases_map.txt", 100)):
            _written = staging / _name
            _rows = sum(1 for _ in _written.read_text(encoding="utf-8").splitlines()) if _written.is_file() else 0
            if _rows < _floor:
                raise MakeDictError(
                    f"{_name}: wrote {_rows} row(s), below the {_floor}-row sanity floor -- refusing to write "
                    f"the completion marker, because a directory that says 'this generation is done' on top of "
                    f"{_rows} rows is exactly the 'looks valid, is not' dictionary the marker exists to prevent")
        # 逐表落位（上面那些写操作都落在 staging 里）。
        for _name in ("phrases_dict.txt", "phrases_map.txt", "word.txt", *extras):
            os.replace(staging / _name, target / _name)
        # 全部表（含方言自己的）就位之后才盖章；staging 目录此时应为空，删掉它。
        try:
            staging.rmdir()
        except OSError:
            pass
        write_lf_atomically(target / "format.txt", [f"{DATA_FORMAT_VERSION}\n"])
