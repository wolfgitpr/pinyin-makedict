# docs -- 语言扩展资料

本目录记录**除中粤以外的语种能不能做、做到什么程度**。出厂默认只有中粤，其余一切语种产物都是实验版，
不得当作出厂词库。

| 文件 | 内容 |
|---|---|
| [`DIALECT_EXTENSION_RECORD.md`](DIALECT_EXTENSION_RECORD.md) | 语种调研结论、许可红线、新增语种必须遵守的判据 —— **唯一一份** |
| [`HISTORY.md`](HISTORY.md) | 仍然有效的漂移追溯结论与四条硬规则 |

> 「本项目（cpp-pinyin）只默认中粤，其他带拓展的语种联合本仓库实测准确率达标后，只在 Python 的
> 　词典制作仓库增加，cpp 里只留中粤相关、其他一切都不追踪」

## 边界（读之前先看这条）

- **架构边界的权威副本在 cpp 侧**：`cpp-pinyin/docs/Custom Chinese Dialect.md`（哪些方言可以进仓、第三方目录怎么放）
  ——扩展点清单、冻结区清单、每轮越界自检命令。本仓只保留**实验语种的调研结论**，不复制架构权威。
- 记录里出现的 `cpp-pinyin` 旧路径（`src/EngineImpl.h`、`res/dict/…`、`tools/corpus/…`）与行号，
  多是**迁移前快照**的引用；跨仓库引用前请回 cpp-pinyin 现场核对。
- 语种产物只在本仓产出（`gen/mandarin.py` / `gen/cantonese.py`、`data/sources/sanitized.txt`、
  `data/overrides/can_overrides.py` / `data/overrides/man_overrides.py`）；**新语种一律标实验版**，且**不进入 cpp-pinyin**
  （那里只有中粤）。
