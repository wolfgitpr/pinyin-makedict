# pinyin-makedict

cpp-pinyin 词典的**唯一产地**。cpp-pinyin 的 `data/dialects/**`（目录重构前写作 `res/dict/**`）
只作为**生成产物快照**存在，任何词典改动都必须先改这里，再重新生成。

| 想知道什么 | 看哪里 |
|---|---|
| 仓库边界与硬约束 | [`REPO_SCOPE.md`](REPO_SCOPE.md) |
| 工具、命令、版本纪律、"什么算漂移" | [`TOOLING.md`](TOOLING.md) —— **唯一权威**，本文件不复述 |
| 这一代出厂数据应该长什么样（字节级） | [`MANIFEST.sha256`](MANIFEST.sha256) |
| 其他语种能不能做、做到什么程度 | [`docs/DIALECT_EXTENSION_RECORD.md`](docs/DIALECT_EXTENSION_RECORD.md) |

## 入口：每语种一个脚本，**路径按仓库位置解析，cwd 无关**

| 语种 | 命令 | 产物目录 |
|---|---|---|
| 普通话 | `python gen/mandarin.py` | `out/dict/mandarin/`（`gen/mandarin.py` 里的 `out_path`） |
| 粤语 | `python gen/cantonese.py` | `out/dict/cantonese/`（`gen/cantonese.py` 里的 `out_path`） |
| ~~潮州话（实验版）~~ | ~~`python teochew.py`~~ | **已出仓**：只留拓展记录，见 [`docs/DIALECT_EXTENSION_RECORD.md`](docs/DIALECT_EXTENSION_RECORD.md) |

- **cwd 无关**：仓库根由 `gen/common.py` 的 `REPO = pathlib.Path(__file__).resolve().parent` 派生，脚本据此读 `data/`。
- 两个入口都在 `if __name__ == "__main__"` 之后 ⇒ **导入不会顺带生成词典**。
- 依赖版本**精确锁定**在 [`requirements.txt`](requirements.txt)，由 `common.check_dependency_versions()`
  （在 `MakeDict.__init__` 处调用）**硬校验**：版本不符时生成器**直接报错**，而不是默默产出另一套词典。
  为什么必须钉死，见 TOOLING.md §2。
- 产物一律写在 `out/`（已 gitignore），**绝不入库**。

## 校验

```powershell
python -m pytest tests -q                                   # 本仓门禁套件
powershell -ExecutionPolicy Bypass -File tools\check_drift.ps1 -CppPinyinRoot <cpp-pinyin 路径>
```

第一条用 `CPP_PINYIN_ROOT=<cpp-pinyin 根目录>`（本机为 `D:\projects\cpp-pinyin`）指定邻仓；邻仓不在时
消费侧契约**SKIP 并打印原因**，不会假装通过。第二条是交付判据：它会**重新跑一遍生成器**再逐字节比。

**三件比对工具的分工、判定口径与退出码的唯一权威在 TOOLING.md §7**；交付序列见 §9；逐字节期望值见
[`MANIFEST.sha256`](MANIFEST.sha256)。本文件不重复这些口径。

环境上有两处会绊人：

- **PATH 陷阱**：这台机器上 `python` 可能先解析到 `miniconda3\python.exe`（没有 `pypinyin`）⇒
  `check_drift.ps1` 会以 `ModuleNotFoundError` 失败。**这是环境问题，不是仓库问题**：用
  `-Python <绝对路径>` 指定装了依赖的那个解释器。
- **离线**：两个数据依赖本仓自带 wheel（`.tools_probe/wheels/`）；`zhconv` 不带，纯离线环境要自己补。

## 产物契约（本仓是权威：每个语种目录里到底有哪些文件、谁生成谁手工维护）

cpp-pinyin 的 `data/dialects/<lang>/` 消费本仓 `out/dict/<lang>/` 的**四张表 + 一个 `format.txt` 标记**：

| cpp 侧 `data/dialects/<id>/` 里的文件 | 来源 |
|---|---|
| `word.txt` / `phrases_dict.txt` / `phrases_map.txt` / `trans_word.txt` | **本仓生成**：三张共享表由 `common.MakeDict.write_three_tables()` 一次写出，各生成器的 `make_dict()` 调用它；`trans_word.txt` 由各生成器的 `extra_tables()` 提供 |
| `format.txt` | **本仓生成**：字典格式契约号，见 TOOLING.md §10 |
| `user_dict.txt` | **cpp 侧人工维护**，本仓**不产出**（生成器全文无它的写入点） |
| `License.txt` | **cpp 侧人工维护**，本仓**不产出** |
| `dialect.json` | **cpp 侧维护**（声明 `required_tables`/`optional_tables`/`assets`） |
| 本仓 `data/overrides/man_user.txt` | **本仓手写输入**（当前 **0 字节**），喂给 `MakeMandarin` 的 `user_dict`，条目在生成期并入词组读音表，**不会**产出第四张表 |

> ⚠️ **两个近名文件，别混**：
> `data/overrides/man_user.txt`（**本仓**，0 字节，普通话生成器的可选输入 —— 条目会进生成期的 `user_dict` 表；
> 当前为空，所以那条分支从未真正产出过内容）与 cpp-pinyin 的
> `data/dialects/mandarin/user_dict.txt`（**消费侧**，2,125 字节，**运行时**由引擎 `loadUserDict()` 读）。
> 前者缺失或为空**不改变任何产物字节**；后者改了会直接影响引擎对用户自定义词的读音。
> 本仓既**不产出**也不**读取**消费侧的 `user_dict.txt`，两者只是名字像。

**消费侧的权威副本**：`cpp-pinyin/docs/NEW_DIALECT_PLAYBOOK.md` §5 第 6/7 条（新语种怎么落地、
三条可执行判据、以及"新语种只留在本仓"由 cpp 侧 `DialectSetGate` 把守）。本仓不复述那份内容。

### 数据许可：生成的四张表**不是** Apache-2.0

根目录 `LICENSE.txt` 的 Apache-2.0 **只覆盖生成脚本**。生成出来的表是**派生数据**，随上游字典走：

| 语种 | 上游 | 数据许可 | 权威文本 |
|---|---|---|---|
| 普通话 | CC-CEDICT（MDBG） | **CC BY-SA 4.0** | cpp 侧 `data/dialects/mandarin/License.txt` |
| 粤语 | CC-Canto / CC-CEDICT 粤语读音（2015-09-23） | **CC BY-SA 3.0** | cpp 侧 `data/dialects/cantonese/License.txt` |

`License.txt` 为什么不由本仓产出，见上一张表的同名行。**再分发 `out/dict/**` 的人必须连带那份
`License.txt`** —— 否则分发出去的就是一份没有署名、也没有 share-alike 声明的 CC BY-SA 衍生数据。
（cpp 侧的安装规则会把 `data/dialects/<lang>/` 整个目录装进包里；本仓这一节只负责把**归属**说清。）

## 语种范围

**除中粤（普通话、粤语）以外的一切语种产物都是「实验版」**：不得当作出厂词库，数字只能写成「实验分支
达到 X%」，且**只在**本仓记录。调研结论与边界见 [`docs/DIALECT_EXTENSION_RECORD.md`](docs/DIALECT_EXTENSION_RECORD.md)。

## Open-source softwares used

+ [cc-edict](https://cc-cedict.org/wiki/)
  The dictionary source.

+ [pinyin](https://github.com/kfcd/pinyin)
  The fan-jian dictionary source.

## 版本与编号

本仓**不编号、也不维护 CHANGELOG** —— 它产出的是**数据**（各语种词典表），由 cpp-pinyin 作为消费者读取；
给一个数据产出工具编版本号，只会让下游依赖一个从未承诺过的编号。发布相关的约定见 cpp-pinyin 的
cpp 仓的 `docs/RELEASE_CHECKLIST.md`。

数据自身的格式代由每个方言目录里的 **`format.txt`** 自报（引擎在读任何表之前校验它，
见 cpp-pinyin `docs/STABILITY.md` 的政策 R13）——**数据面的"版本"是那个标记，不是本仓的编号**。
