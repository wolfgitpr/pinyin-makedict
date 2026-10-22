# `data/`：两类输入，两种维护方式

这个目录放生成器的全部输入。**两类文件的来源与责任完全不同，所以分开放**——混在一起时，"这个文件能不能改"要靠记忆回答，而记忆会过期。

## `sources/` —— 下载来的语料，本仓不写

| 文件 | 是什么 | 版本 / 出处 | 许可 | 能不能改 |
|---|---|---|---|---|
| `cedict_ts.u8` | CC-CEDICT 汉语词典（简繁 + 拼音） | 头部自带 `date=2023-04-16T01:18:48Z`、`entries=121646` | **CC BY-SA 4.0**（头部带许可 URL） | **不能**。要更新就整份替换，并同步 `MANIFEST.sha256` |
| `cccedict-canto-readings.txt` | CC-CEDICT 粤语读音表 | 头部自带 `Version 2015-09-23` | **CC BY-SA 3.0**（Pleco Software, cccanto.org） | **不能**，同上 |
| `sanitized.txt` | 粤语字→读音的制表符表（现行粤语主输入） | 由上游 `ToJyutping` 包的 `trie.txt` 派生 | 随上游 | **不能**；派生规则见 `docs/TOOLING.md` |
| `fanjian.txt` | 繁→简单字表（制表符） | 上游 `kfcd/pinyin` | 随上游 | **不能** |
| `fanjian2.txt` | 繁→简补充表（逗号），覆盖同名键 | 上游 `kfcd/pinyin` | 随上游 | **不能**；但见下面那条例外 |

`sanitized.txt` 与 `fanjian2.txt` 的"不能改"是有来历的：两仓曾经各持一份、悄悄漂移，根因就是有人手工改了其中一行的副本。现在的规矩是**改上游、重新派生、更新 `MANIFEST.sha256`**，而不是就地编辑（`docs/HISTORY.md` 记着这条教训）。

## `overrides/` —— 本仓手写的，改了要跑测试

| 文件 | 是什么 | 谁在用 |
|---|---|---|
| `man_overrides.py` | 普通话的读音增补/改写表（**Python 模块**，有注释记录每条为什么加） | `gen/mandarin.py` |
| `can_overrides.py` | 粤语的词组读音覆盖与首读音重排（Python 模块） | `gen/cantonese.py` |
| `man_user.txt` | 普通话 `user_dict` 的**占位输入**，当前 **0 字节** | `gen/mandarin.py` |

`man_user.txt` 空着是**有意**的：它证明"用户词典这条输入路径存在并且被解析"，而不是"这里有数据"。它和消费侧 `cpp-pinyin/data/dialects/mandarin/user_dict.txt`（2125 B，引擎运行时加载）**同名不同义**，跨仓界看很容易搞混——`tests/test_man_user.py` 守着这条区别。

改 `overrides/` 里的任何一份之后，必须让 `MANIFEST.sha256` 与消费仓重新对齐：

```powershell
python gen/mandarin.py --out .tmp\mandarin
python gen/cantonese.py --out .tmp\cantonese
python tools\compare_dict_dirs.py <生成目录> ..\cpp-pinyin\data\dialects
powershell -ExecutionPolicy Bypass -File tools\check_drift.ps1 -CppPinyinRoot ..\cpp-pinyin
```

`MANIFEST.sha256` 是"这一代出厂数据应该长什么样"的字节级期望值；生成物不入库，所以没有它就没有可核对的固定值。

## 许可提醒

`sources/` 里有两份 CC BY-SA 的语料。它们**不进入**发布的词表（生成物是派生数据），但如果你要把本仓的输入语料再分发，请保留 `sources/` 文件头部的版权与许可声明——那也是删掉它们就违反许可的地方。
