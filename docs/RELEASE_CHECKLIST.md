# 发布清单（词典仓）

这份文件是**发布当天照着走**的清单，不是设计文档。设计理由见 `docs/TOOLING.md` 与 `docs/HISTORY.md`。

## 0. 单一权威（同一个事实只允许一处）

| 事实 | 唯一权威 | 谁在验 |
|---|---|---|
| 8 张表的**字节** | `MANIFEST.sha256` | `tests/test_data_gates.py::test_manifest_matches_a_fresh_generation`（重跑生成器再逐字节比） |
| 三个数据依赖的**版本** | `requirements.txt`（全部 `==`） | `common.check_dependency_versions()` |
| 消费侧现在**实际装着**什么 | 邻仓 `cpp-pinyin` 的 `data/dialects/` | `tools/check_drift.ps1`（经 `tools/run_all_gates.py --cpp-root` 调用） |
| 解释器下限 | `pyproject.toml` 的 `requires-python` | 本清单 §1 第 3 条（在 3.10 上跑一遍） |

**别在别处再写一遍这些数字**：本文件刻意不抄任何字节数、行数或 sha，抄一份就是多一个会漂移的权威。

## 1. 发布前必须成立的四件事

```bash
pip install -r requirements.txt -r requirements-dev.txt
python tools/run_all_gates.py --cpp-root <cpp-pinyin 检出路径>
```

必须看到 `RESULT: 4 gate(s) passed`，逐条含义：

1. `delivery` —— 两张方言表从语料重新生成后，与 `MANIFEST.sha256` **逐字节**相同；
2. `pins` —— 三个数据依赖装在钉死的版本上；
3. `suite` —— 全套契约/读音/顺序/错误模型测试（发布前是 24 passed、1 skipped，跳过项会自己说明原因）；
4. `drift` —— 生成的表与邻仓 `data/dialects/` **仍然一致**（这是"这份数据还能被那个库消费"的唯一判据）。

第 4 条需要 PowerShell；在 Linux/macOS 上它会 **SKIP 并说明原因**——那种情况下必须**另外**在一台 Windows 或装了 pwsh 的机器上补跑，或者手工核对 `MANIFEST.sha256` 与邻仓文件的 sha256。

## 2. 发布当天的步骤

1. 确认工作树干净：`git status --porcelain` 为空；
2. 跑 §1 的四条门禁，全绿；
3. 打标签：`git tag -a dict-v2.0.0 -m "dictionary tables consumed by cpp-pinyin v2"`（版本跟随邻仓 v2 线）；
4. 触发发布预备：GitHub Actions → **Dictionary release preparation** → `workflow_dispatch`，`version` 填 `2.0.0`；
5. 下载产物并核对：`pinyin-makedict-2.0.0.tar.gz` 与同名 `.sha256`，且压缩包内是 `mandarin/` 与 `cantonese/` 两个目录、共 10 个文件（8 张表 + 2 个 `format.txt`）；
6. 把产物的 sha256 与 `MANIFEST.sha256` 的对应关系写进 GitHub Release 说明（**别改** `MANIFEST.sha256` 本身，它描述的是表，不是压缩包）；
7. 推送标签：`git push origin dict-v2.0.0`。

## 3. 这一仓**没有**的东西（别以为有）

- **没有 PyPI 包**：`pyproject.toml` 开头就写明它不是一个包，没有 build backend，产物是八张 `.txt` 表；
- **发布预备工作流从没跑过**：`release_prep.yml` 是 `workflow_dispatch` 专用，第一次跑就是在发布当天——所以 §2 第 5 步的核对必须真做；
- **CI 的第一次运行就是它的第一次验证**：`.github/workflows/` 是 2026-10-23 才加进来的，在此之前本仓的判据只有本机 `pytest`。

## 4. 出问题时先看哪里

| 现象 | 先看 |
|---|---|
| `delivery` 红 | 依赖版本是否被换过（`pip freeze` 对照 `requirements.txt`）；语料是否被改过（`git status data/sources`） |
| `pins` 红 | `requirements.txt` 与已装版本不一致——这是**数据血缘**问题，不是环境噪音 |
| `drift` 红 | 邻仓是否已更新到新表；若是，先更新邻仓再看，别改词典迁就旧库 |
| 生成器报"incomplete dictionary" | 表为空或过小会被拒写（`tests/test_data_gates.py` 有对应断言），检查语料读取路径 |
