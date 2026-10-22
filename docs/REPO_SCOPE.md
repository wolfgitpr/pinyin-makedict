# pinyin-makedict -- 词典唯一产地

本仓库是 cpp-pinyin 词典的**唯一产地**。cpp-pinyin 的 `data/dialects/**`（目录重构前写作 `res/dict/**`）
只作为**生成产物快照**存在，任何词典改动都必须先改这里，再重新生成。

## 0. 现行结论（判据永远是"现在跑一次"）

| 项 | 现行 | 依据 |
|---|---|---|
| 生成物 vs cpp 侧快照 | **中粤 8 张表 + 2 个 `format.txt` 逐字节一致（0 漂移）** | 判据命令见 `TOOLING.md` §1；逐字节期望值见 `MANIFEST.sha256` |
| 钉定依赖 | `pypinyin==0.55.0` · `ToJyutping==3.2.0` · `zhconv==1.4.3` | `requirements.txt` + `common.check_dependency_versions()` 运行时硬校验；理由见 `TOOLING.md` §2 |
| 两个历史差异（23 字 + 5 读音、`吒:咤`） | **均已归零**；根因是依赖数据版本与 `data/sources/fanjian2.txt` 的一行，**不是**扫描范围或过滤表 | 结论与教训：`docs/HISTORY.md`；`吒` 的机制：`TOOLING.md` §4 |
| 二进制线（`.cpdict`） | **已按裁决停用**：从未被消费，各语言接口共用同一份文本表 | `TOOLING.md` §11 |
| 本仓在发布链上 | **不编号、不维护 CHANGELOG**；数据面的"版本"是各语种目录里的 `format.txt` | `README.md` 末节、`TOOLING.md` §10 |

> 判据随**快照**而变：cpp-pinyin 每换一代快照，"用哪个依赖版本复现它"就可能跟着换。所以"当前是否一致"
> 只由跑判据命令回答，任何写死的行数都只能当**当时的读数**引用。

## 硬约束（来自 cpp-pinyin 侧实测）

1. **短语匹配只在简体键上进行。** `EngineImpl::assemble()` 在进 `queryRawInto()` 之前就把每个
   token 的首字经 `toSimp()` 转换；`DictUtil::loadAdditionalDict()` 则把用户词条的键**原样编码**。
   因此 `user_dict.txt` 里用**繁体**写的词条**永远不命中，且 `loadUserDict()` 仍返回 true**
   （静默失效）。实测：同一批 8 条修正，繁体键 0 影响，简体键使粤语 `trans_word` 路线
   74.14% → 89.18%、整体 94.7901% → 94.8554%。
2. **单字 user_dict 词条无效。** `EngineImpl::rebuildPhraseIndex()` 跳过所有长度不在 2..4 的键，
   而 K5 窗口只探测长度 2–4，所以覆盖必须写成短语。
3. **单读音字不进短语窗口。** `queryRawInto()` 在 `!hasPolyphonic(char)` 时直接返回，
   短语层无法影响它 —— 即使字表里给了多读音，也要靠词条让窗口打开。

## 目录约定

* 生成物写 `out/dict/<lang>/`（已 gitignore）。**不要**另起输出根：本仓只有 `out/dict/` 一个产地。
* 依赖版本**精确锁定**在 `requirements.txt`，并在 `common.check_dependency_versions()` 里硬校验：
  版本不符时生成器**直接报错**，而不是默默产出另一套词典。见 `TOOLING.md` §2。
* 校验、比对与交付的**命令和口径唯一权威在 `TOOLING.md`**（§1 命令、§7 三件工具、§9 交付序列）；
  本文件不复述。
* **旧历史怎么取回**同样在 `TOOLING.md` §6 的「旧历史怎么取回」；引旧 SHA 前先读那一节。
