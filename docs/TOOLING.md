# TOOLING.md — 工具与 cpp-pinyin 冻结词典的关系、以及如何复核

**本文是工具、命令与"什么算漂移"的唯一权威。** 其他文档只写指针，不复述。
凡是标「实测」的数字都能用 §1 的命令重新跑出来。

## 1. 当前状态与复核命令

生成器在钉版本下产出 **8 张表 + 2 个 `format.txt` 标记**，与 cpp-pinyin `data/dialects/` 的冻结副本比对
（2026-10 目录重构前为 `res/dict/`）。逐字节期望值见 [`MANIFEST.sha256`](MANIFEST.sha256)。

```powershell
cd D:\python\pinyin-makedict
# 快速：只比对现有 out/dict
powershell -ExecutionPolicy Bypass -File tools\check_drift.ps1 -CppPinyinRoot <cpp-pinyin 路径> -SkipGenerate
# 权威：重新生成再逐字节比（交付判据以这一步为准）
powershell -ExecutionPolicy Bypass -File tools\check_drift.ps1 -CppPinyinRoot <cpp-pinyin 路径>
# 完整：按锁定版本重跑并逐字节比对冻结副本（版本号随 requirements.txt 走）
python tools/run_versions.py 0.55.0 3.2.0
```

`run_versions.py` 会把 `out/dict` 先备份、跑完再还原（并校验还原结果逐字节一致），所以它不会把工具的
输出留在半成品状态。

## 2. 依赖版本必须锁定（这是最重要的结论）

`gen/mandarin.py` 的 `word.txt` 由 **pypinyin 的数据表**决定，而那张表在 0.54.0 → 0.55.0 之间动过：

* 条目数 41,651 → 41,923；
* `U+9FA6..U+9FFF` 区间内 9 条 → 32 条，多出的 23 个字（`U+9FAA 龪` … `U+9FFF 鿿`）会直接进 `word.txt`；
* 另有 5 个已存在条目的读音被**改写**：`杢 jiang→jié`、`婥 nào,chuò→chuò,nào`、`笹 ti→tì`、
  `枠 zui→huà`、`𦛨 lao→láo`。

实测：拿**当前**的 cpp-pinyin 快照比对，`pypinyin==0.55.0` 能把四张普通话表**逐字节复现**，
`pypinyin==0.54.0` 不能（`mandarin/word.txt` 17502 vs 17525 行：23 个字缺失、5 个读音不同）。
**不需要任何硬编码排除表**——两种版本的差异全部来自包自带数据表。

> 判据随**快照**而变：快照换一代，复现它的版本号就可能跟着换。判据永远是"用当前快照跑一次
> `tools/check_drift.ps1`"，不是记版本号。

粤语侧同理但更细：`噚` 的候选顺序在 `ToJyutping` 3.1.0 与 3.2.0 之间不同（§5）。

因此 `requirements.txt` 采用 **精确锁定**（`==`），`common.check_dependency_versions()` 在版本不符时
**拒绝运行**，而不是默默产出另一套词典。**升级依赖 = 一次数据变更**，必须与 cpp-pinyin 侧冻结门禁的
重新冻结放在同一次改动里。

## 3. 复核时必须避开的两个陷阱（都真实发生过）

1. **`pypinyin_dict.json` 的键是十进制码点字符串**（`'12295'` = 中），不是字符。
   用 `d['中']` 查询会**对所有字符**返回 `None`，看起来极像"这个版本没有数据"，
   会得出一个自信但完全相反的结论。正确查询是 `d[str(ord(ch))]`。

2. **对比工具会把"一行缺失"报成"几十行乱序"。**
   少一行会让其后每个下标都错位。`tools/compare_dict_dirs.py` 现在先用**多重集合**判断，
   把结果分成"内容差异"和"纯顺序差异"两类，只统计**真实反转的键对**。

> 通用形式：凡是"什么都没加载"也会说一致的探针，就是假绿。对比前先断言数据真的被读进来了。

## 4. 粤语 `吒/咤`：为什么生成器要同时用 `data/sources/fanjian2.txt` 的一行和 `own_key`

出厂对这两半的要求是反向的：`word.txt` 要 `吒` 自己的键，`trans_word.txt` 要 `吒:咤` 映射。
所以 `data/sources/fanjian2.txt` 里必须有「吒,咤」那一行（它曾被上游删掉，恢复后才两半都对），
同时靠 `gen/cantonese.py` 的 `own_key = ["吒"]` 让扫描不为该字改写键。

- **别删那一行、也别删 `own_key`**：改任一处都会破坏 8 表逐字节一致，判据是 §1 的 `check_drift.ps1`。
- **别改消费侧**：把 cpp-pinyin 那行删掉虽然能让两仓对齐，但会把 `readings("吒")` 从 4 个读数变成 2 个
  （探针实测），那是**消费者可见的行为改动**。
- 决策与全部实测留在 `gen/cantonese.py` 的注释里；本节只留结论。

## 5. `噚` 的顺序差异：已实测**不影响输出**

冻结与生成都是同一组读音、首读音都是 `cam4`，只有候选顺序不同
（3.1.0 `cam4,cam6,jing1 cam4,cam3` vs 3.2.0 `cam4,cam6,cam3,jing1 cam4`）。
实测 44 条含 `噚` 的粤语语料行，两种词典的 `query()` 输出**完全相同**；
`readings("噚")` 的列表顺序不同，但那只是候选顺序，不是判定读音。

真正的来源是 `ToJyutping` 的版本，不是 `data/sources/sanitized.txt` 的上游排序变化（`sanitized.txt` 从未包含 `噚`）。

## 6. 门槛与已知残留

* `tools/check_drift.ps1` **先比字节**（SHA-256），值映射**只用来描述**差异落在「键/值」还是「纯顺序」
  ⇒ **纯顺序差异照样计 drift、脚本 `exit 1`**。要看差异明细请用 `tools/compare_dict_dirs.py`
  （它把「内容」与「顺序」分开报，且顺序差异**不算**失败 —— 两件的判定面不同，见 §7）。
* `out/`、`.tmp/`、`.tools_probe/pkg-*/`、`.tools_probe/wheels/` 都是过程产物，不入库。
* cpp-pinyin 侧的 `data/dialects/`（重构前 `res/dict/`）是**冻结输入，不在本仓库修改**；本仓库只负责
  生成与比对。

### 旧历史怎么取回

本仓的未推送历史被压缩过几轮，压缩前的**锚点分支与标签都已删除**，`git branch`/`git tag` 里已经找不到
它们。目前本机只剩两条取回路径：

1. `.tmp/` 下的两个 `*.bundle`（`--all` 打的全量包），`git bundle list-heads` 能列出压缩前各分支的尖端；
2. `git reflog` —— 旧提交对象目前仍在库里可达，但 reflog 到期或 `gc` 之后就没有了。

所以要长期留档，靠的是 bundle；**删 `.tmp/` 前先确认这两个文件还留不留**。

## 7. 三件"比对"工具：口径的唯一权威

本仓有三件工具都在回答"生成物和冻结表差在哪"。**"什么算漂移"的口径以本节为准**——三件都只**引用**它，
不再各自写一套判定（口径单点化，**不合并代码**：三者的输入/退出口径不同，合并会改变门禁本体的形状）。

| 工具 | 角色 | 判定面 |
|---|---|---|
| `tools/check_drift.ps1` | **门禁（字节权威）**：跑生成器 + 与 `<cpp-pinyin>/data/dialects` 逐字节比对 | 判据 = **逐字节**；**比哪些方言/表由两棵树的目录派生**（不写死中粤 8 个文件，见 §8）；`0 drift` 即"出厂数据 = 生成物" |
| `tools/run_versions.py` | **依赖版本矩阵**：在指定 (pypinyin, ToJyutping) 下跑生成器。⚠️ 它**直接写 `out/dict`**（生成器硬编码该路径），跑完在 `finally` 里用备份还原、并自比字节 ⇒ 会**短暂覆盖 `out/dict`**；崩溃时真基线留在 `out/dict.prefrozen-backup` | **不自己写判定**——它 subprocess **调用** `tools/compare_dict_dirs.py` 比 `out/dict` 与冻结表；自己只做 before/after 自比，回答"这次运行有没有改动产物"（与"是否漂移"不是同一个问题）。**退出码**：`0` = 生成器全 0 且比较给出 `RESULT: byte-identical`；`1` = **发现漂移**（比较报 `DIFFERS`/`MISSING`，或比较压根没跑成）；生成器自身失败则透传它的码 |
| `tools/compare_dict_dirs.py` | **归因**：两份生成树的逐行 diff | 把差异分成 **CONTENT**（内容/键值不同 ⇒ 会改变引擎输出）与 **ORDER**（同集合不同顺序；对 `word.txt` 仍算内容，因为首读音是默认读音） |

两条边界（别误读）：

1. **行数 ≠ 字节**：只有上表第一件能证明"逐字节一致"；第二件报的是"漂移存在"这一信号；第三件负责**定因**。
2. **两侧方向相反**：本仓工具是"生成物 → 本仓冻结表"（生产侧视角）；cpp-pinyin 侧那件
   （`tools/pinyin_makedict_output.py`）是"本仓冻结表 ← `out/dict`"（消费侧视角，且只比表名+行数）。
   三件跨仓工具的职责总表在 **cpp-pinyin 的 `tools/board/README.md`**（那是我方与消费者之间的边界权威）。

## 8. "写死的清单"这一族坑与三条规矩

新增方言/表/配置时，代码里往往还有一份**隐式清单**要跟着改。漏改不会报错，而是**静默变窄**——
工具照跑、门禁照绿。实测抓到三处，其中两处在词典仓：

| 位置 | 症状（实测） | 现在的把守 |
|---|---|---|
| `tools/compare_dict_dirs.py` 的 `LANGS` | `out/dict` 里已有第三方言时，拿它与自己的副本比对仍打印 `RESULT: byte-identical` ⇒ **忽略一整个方言还报全绿** | 改为从树/manifest **派生**（`dialects_present()` / `table_names()`）；`FALLBACK_FILES` 仅兜底 |
| `tools/check_drift.ps1` 的 `$files`（曾 2 方言 × 4 表写死） | `out/dict` 或 `data/dialects` 里多出第三方言时，**字节权威**仍只比那 8 个文件、照打 `0 drift` ⇒ **忽略一整个方言还报全绿**（实测反例：`out/dict/hakka` 与 `data/dialects/teochew` 同时存在，旧版仍 `0 drift`/`exit 0`） | 改为从两棵树的目录 + `dialect.json` 的 `required_tables` **派生**（`Get-SubDirNames`/`Get-TableNames`，与 `compare_dict_dirs.py` 同源）；`$FALLBACK_TABLES` 仅兜底；两侧都没有方言目录时 `exit 4` **拒绝报绿** |
| cpp 侧 `tools/pinyin_makedict_output.py` 的 `REQUIRED_TABLES` | 与 `dialect.json` 的 `required_tables` 是两份权威 | `MANIFEST MISMATCH:` **硬失败** |

> 第 2 行代价最高：**门禁本体**也在写死清单，而它是"出厂数据 = 生成物"的唯一字节权威。

**三条规矩**（新增同类东西时照此办）：

1. **能从树或 manifest 派生的，一律派生**——不要在代码里再写一份。
2. **不能派生的（如写进 header 的槽位号），必须自带一致性自检**，且失败要**响亮**（点名 + 非零退出），
   不要只打印一行日志。
3. **判断标准**：问自己"新增方言/表/配置时，是否必须有人**记得**改这一处？"——答案为"是"就属于这一族，
   必须落到规矩 1 或 2 上。
   **例外（很重要）**：如果那份"清单"本身就是**刻意写死的契约/白名单**，
   硬编码才是要点 —— 这时**不要**把它改成"从目录派生"。实测例子：cpp-pinyin 的
   `python/tools/build_native.py` 写着 `DIALECTS = ("mandarin", "cantonese")`，注释说明它
   **故意不**读 `data/dialects/*`，因为"本项目只出两个方言，散落目录不得混进 wheel"；
   `REQUIRED_TABLES` 也是刻意的（"半拷贝的词典不能冒充完整"）。这类清单的要求是**写清理由**，
   而不是派生 —— 把它"修"成派生的，反而会放进本该被挡住的东西。
   区分一句话：**这份清单是在描述现实（⇒ 派生），还是在规定现实（⇒ 写死 + 写清理由）？**

## 9. 面向开发者的最小操作序列

**定位**：本仓是**生成器**，cpp-pinyin 的 `data/dialects/` 是**冻结输入、不在本仓修改**（§1 与 §6）；
生成是**开发者偶发动作**，不是每次构建的一步。因此这里给的是**一条可照做的序列**，不是自动化流水线。

1. 生成（写 `out/dict/<lang>/`）：
   ```powershell
   cd D:\python\pinyin-makedict
   python gen/mandarin.py ; python gen/cantonese.py
   ```
2. 交付（把 4 张表拷进 cpp-pinyin，**只这一侧允许人工**）：
   ```powershell
   robocopy out\dict\mandarin D:\projects\cpp-pinyin\data\dialects\mandarin /NJH /NJS
   robocopy out\dict\cantonese D:\projects\cpp-pinyin\data\dialects\cantonese /NJH /NJS
   ```
3. **验证（权威在这一步，不在上一步的人工拷贝）**：跑 §1 里那条"权威"命令（不带 `-SkipGenerate`）。
   判据：`check_drift.ps1` 会**重新跑一遍生成器**再与 `data/dialects` 逐字节比 —— 只有它报全表
   byte-exact 才算交付成立。**不要凭"我拷过了"下结论。**

## 10. 字典格式契约号（与库版本正交）

`format.txt` 的内容就是**字典格式契约号**：两仓当前都是 `2`（本仓 `out/dict/{mandarin,cantonese}/format.txt`、
cpp-pinyin `data/dialects/mandarin/format.txt` 实测一致）。
- 消费侧把它钉在 cpp-pinyin 的 `tests/cpp/test_dict_format_marker.cpp`；
- 它与库版本（cpp-pinyin `2.0.0`）**正交**：格式升级改这个数字、库升级走 semver，两者不必同步；
- 引用时请写"字典格式 = 2（`format.txt`）"，不要写成"版本 2"以免与库版本混淆。

## 11. 二进制线（`.cpdict`）：已按裁决停用

用户裁决：**确定不使用二进制**。理由不是"没时间做"，而是它**从未被消费过** —— 消费侧加载器在
cpp-pinyin 的 `src/` 里零命中，而各语言接口本来就共用同一份文本表 `data/dialects/<lang>/`。
相关代码（`binary/`、`tools/check_binary.py`、`tools/check_index.py`）已删除，历史仍在 git 里。

**若将来重启**：不要从 `git log` 里捞旧文件后直接跑，先回答三件事 —— ①消费侧加载器谁写、
②端到端等价门禁怎么落地、③二进制与文本表**双份数据**的漂移由谁负责（`check_drift` 只管文本）。
