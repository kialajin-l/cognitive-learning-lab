---
license: apache-2.0
language:
- en
- zh
tags:
- research
- memory
- retrieval
- verification
- llm
---

# Distributed Cognitive Learning Runtime

English | [中文说明（见文末）](#中文说明)

A research runtime that answers a bounded multiple-choice decision with a
**frozen proposal model plus external memory**, and keeps the two apart:
the model may propose, but only memory that passed verification can authorise
an answer, write back, or survive a restart.

This directory is the PR-M1/v0.1.0 candidate package.

## Current status

`PR_M1_IMPLEMENTED_LOCALLY_ACCEPTED_REAL_MODEL_SMOKE`

| Item | State |
|---|---|
| Runtime code, CLI, schemas, examples, tests | implemented; 28 tests pass |
| Isolated install + acceptance (mock provider) | run outside the repo against the built wheel, 15 steps, see `acceptance/PR-M1.md` |
| Real frozen-model call | **run** 2026-11-05, offline on CPU against the pinned local snapshot (`laya@55cf4c4e…`): `answered`, `provider_class=real`, memory reused by a second process. Note: `laya 0.3.20` loads all parameters from the checkpoint; the separately downloaded `ModernBERT-large` weights are not read at inference |
| License / authorisation to upload | runtime code is `Apache-2.0` (`LICENSE`); upstream weights keep their own licence and are not bundled. Destination repo id `WayneRR/cognitive-learning-lab` and publication revision `55cf4c4e…` were approved by the owner on 2026-11-05 |
| Published to any remote | the authoritative publication record is `RELEASE-CHECKLIST.md` and `RELEASE-MANIFEST.json` (`publication.status`); this file deliberately does not restate it |

## The chain each request walks

```text
sanitize input  ->  integrity check the store  ->  retrieve memory
  ->  (optional) acquire cited source receipts  ->  verify + promote
  ->  model proposal (never an authorisation)    ->  rule judgment
  ->  three-layer boundary                       ->  controlled writeback + replay
```

Layer separation is the point of the package, so an output carries all of them
at once instead of a single verdict: `raw_proposal`, `judgment`,
`verification`, `writeback` + `writeback_receipt`, `authorization`, `cost`,
`model`. `authorization` is `verified_judgment` only when a promoted,
hash-intact memory rule allows the answer.

Two verification types, both deliberately narrow:

- `source-consistency-v1` — a record still matches the source receipt it cites;
- `lineage-consistency-v1` — a written-back conclusion still agrees with the
  promoted records it was derived from, and adds no new support.

Neither proves the cited claim is true in the world, and no API returns a
status that suggests otherwise.

## Install

```bash
cd public-runtime
python -m pip install .            # runtime, no hard dependencies
python -m pip install ".[dev]"     # + pytest, jsonschema for the test suite
python -m pip install ".[model]"   # + laya / huggingface_hub / torch for real inference
```

Requires Python 3.10+ (accepted on 3.11.9). `requirements-lock.txt` is the full
44-package closure of the acceptance environment, read from installed
distributions rather than produced by a resolver; it was checked to resolve
satisfiable as a set in a clean venv (`uv pip install --dry-run -r
requirements-lock.txt` → 44 packages, exit 0), which downloads nothing and so is
not a claim that every wheel was re-downloaded. Resolving from `pyproject.toml`
alone drifts upward, so use the lock file as the reproducibility surface.

## Use

```bash
# readiness, without downloading anything
cognitive-runtime doctor --store ./demo.sqlite

# one request through the whole chain
cognitive-runtime infer --input <pkg>/defaults/examples/request.json --store ./demo.sqlite --namespace demo

# a second process reads the memory the first one persisted
cognitive-runtime infer --input <pkg>/defaults/examples/request.json --store ./demo.sqlite --namespace demo

# inspect / maintain the store
cognitive-runtime memory seed   --store ./seeded.sqlite --input <pkg>/defaults/examples/seed-records.jsonl
cognitive-runtime memory verify --store ./seeded.sqlite
cognitive-runtime memory inspect --store ./seeded.sqlite
cognitive-runtime memory clear --store ./seeded.sqlite --yes   # refuses without --yes

# run against the pinned checkpoint instead of the mock
cognitive-runtime --config <pkg>/defaults/laya-offline.json infer --input <pkg>/defaults/examples/request.json --store ./real.sqlite
```

`<pkg>` is the installed `cognitive_runtime/defaults` directory
(`python -c "import cognitive_runtime.config as c;print(c.DEFAULT_DIR)"`).

Exit codes: `0` = ran, and `answered` or `abstained` are both normal results;
`2` = bad or forbidden input, or a destructive command without confirmation;
`3` = not-run (the provider produced no usable proposal, so no answer was
authorised and nothing about the chain should be read as a pass).

A record the caller hands in as `verified`, `trusted`, `gold` or `expected`
is refused before the gate — see `sanitize.py`. Seeding memory is allowed, but
`memory seed` writes candidates and only `memory verify` against the receipt
registry can promote them.

## Model identity (pinned, not bundled)

- Proposal model: `convaiinnovations/laya` at
  `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`, `model.safetensors`
  842,609,210 B, SHA-256 `891102d3…cbcb8d86c` verified equal to the upstream
  LFS digest. License at that revision: `apache-2.0`.
- The snapshot ships `encoder/config.json` only. Measured 2026-11-05:
  `laya 0.3.20` builds the network untrained (`pretrained=False`) and loads
  every parameter — encoder included — from the Laya checkpoint itself, so
  inference does **not** download the `answerdotai/ModernBERT-large` weights
  (`45bb4654a4d5aaff24dd11d4781fa46d39bf8c13`, `apache-2.0`). They were
  downloaded and hash-verified independently anyway
  (`model.safetensors` = `44510fec…`, 1,583,544,840 B) and are recorded in
  `SOURCE-INVENTORY.md` §1; the real-model smoke in `acceptance/PR-M1.md` item
  2 ran with both hub flags in offline mode.
- The package never bundles weights and never trusts a cache hit blindly:
  `verify_integrity()` hashes the pinned file and refuses to run on mismatch.

`MODEL_CARD.md` carries the identity, intended use and limitations.

## What this does not claim

No Transformer parameter growth, no open-domain autonomous learning, no
stable long-term positive gain, no production readiness. The judgment rule set
is a single synthetic "Directory record: X is assigned to Y" template; the
examples are synthetic; the evidence is task- and protocol-bound.

Known limits worth reading before use:

- provenance consistency ≠ external truth;
- a memory hit short-circuits acquisition, so a newer conflicting receipt in a
  source file is not consulted until the store is cleared or the record fails
  verification;
- retrieval is `entity-token-v1`, deliberately deterministic and dumb;
- if a request re-acquires after its stored row was edited on disk, the row is
  quarantined and then rewritten from the receipt — the tampered text never
  authorises anything, but recovery is by re-verification, not by refusing the
  store forever;
- `cost.monetary_cost` is `null` because it is unknown, not because it is zero.

## Documents

| File | Purpose |
|---|---|
| `PROJECT-PLAN.zh-CN.md` | milestone scope and acceptance checkboxes |
| `ARTIFACT-SPEC.zh-CN.md` | interface, directory and manifest contract |
| `SOURCE-INVENTORY.md` | measured licenses, revisions, hashes, reuse list |
| `MODEL_CARD.md` | identity, intended use, limitations |
| `acceptance/PR-M1.md` | per-item Pass / Fail / NOT_RUN with commands |
| `RELEASE-MANIFEST.json`, `SHA256SUMS` | build identity |
| `PAPER-ARTIFACT-NOTE.md` | relation to the sealed paper experiments |
| `RELEASE-CHECKLIST.md` | what must be true before any upload |
| `TASK-LEDGER.zh-CN.md` | round-by-round execution record |
| `AGENT-HANDOFF.zh-CN.md` | contract for whoever implements the next milestone |

## Three milestone release roadmap / 三阶段发布路线

| Milestone | Target version | Deliverable | Current status |
|---|---|---|---|
| PR-M1 | v0.1.0 | Minimal complete research runtime: pinned model, structured inference, persistent memory, judgment, verification and writeback/replay | implemented; accepted locally with a real frozen-model smoke (offline CPU); publication state is recorded in `RELEASE-CHECKLIST.md` |
| PR-M2 | v0.2.0 | Easier deployment: batch/API access, simple local UI, installation checks and compatibility documentation | NOT_STARTED |
| PR-M3 | v0.3.0 | Experimental conversation and bounded web-learning loop with provenance, cancellation and resource limits | NOT_STARTED |

Each milestone produces one versioned release after its acceptance checks pass.
Later milestones preserve earlier behavior and configuration compatibility.
These are delivery goals, not claims that future capabilities already work.
PR-M3 implements an experimental learning mechanism; it does not establish
reliable open-domain autonomous learning or long-term self-growth.

三个阶段均以记忆和经验沉淀驱动的复合系统为对象，不以模型参数成长为验收条件。
阶段完成后更新同一个模型/运行时仓库；Hugging Face 为拟定主渠道，ModelScope
为可选镜像。平台具体规则、账号和仓库目标在实际发布前核实。无需公开历史实验数据。

## Release gate

The licence is answered (`LICENSE`, Apache-2.0, decided by the owner on
2026-11-05), the build no longer carries the `Private :: Do Not Upload` guard,
the real frozen-model smoke has run (offline, CPU, item 2 of
`acceptance/PR-M1.md`), and the two owner decisions are recorded: destination
repo id `WayneRR/cognitive-learning-lab` and publication revision
`55cf4c4e…` (both approved 2026-11-05). Whether this package is currently a
local candidate or a published release is stated by `RELEASE-CHECKLIST.md`
and `RELEASE-MANIFEST.json` (`publication.status`), which carry the actual
remote URL, uploaded revision and post-download verification — not by this
file.

---

# 中文说明

[English (top)](#distributed-cognitive-learning-runtime)

一个研究型运行时：用一个**冻结的提案模型加外部记忆**回答一个有界多选决策，
并把两者分开——模型只能提出建议；只有通过了校验的记忆才能授权一个答案、
写回、或在重启后继续有效。英文部分与中文部分内容一致；接口与目录契约的
中文权威文本是 `PROJECT-PLAN.zh-CN.md` 与 `ARTIFACT-SPEC.zh-CN.md`。

本目录是 PR-M1/v0.1.0 候选包。

## 当前状态

`PR_M1_IMPLEMENTED_LOCALLY_ACCEPTED_REAL_MODEL_SMOKE`

| 项 | 状态 |
|---|---|
| 运行时代码、CLI、schema、示例、测试 | 已实现；28 项测试全部通过 |
| 隔离安装 + 验收（mock provider） | 在仓库外对构建出的 wheel 执行，15 步，见 `acceptance/PR-M1.md` |
| 真实冻结模型调用 | **已运行** 2026-11-05，离线 CPU、针对固定本机快照（`laya@55cf4c4e…`）：`answered`、`provider_class=real`，记忆被第二个进程复用。注：`laya 0.3.20` 从 checkpoint 加载全部参数；单独下载的 `ModernBERT-large` 权重在推理中不被读取 |
| 许可 / 上传授权 | 运行时代码为 `Apache-2.0`（`LICENSE`）；上游权重保留各自许可且不被捆绑。上传仍需指定目标账号/仓库名并批准发布 revision |
| 是否已发布到任何远端 | 否 |

## 每个请求经过的链路

```text
输入净化  ->  存储完整性检查  ->  记忆检索
  ->  （可选）获取引用来源回执  ->  校验 + 晋升
  ->  模型提案（永远不构成授权）  ->  规则判断
  ->  三层边界                    ->  受控写回 + 重放
```

分层隔离是本包的核心目的，因此一个输出同时携带所有层而不是单一结论：
`raw_proposal`、`judgment`、`verification`、`writeback` +
`writeback_receipt`、`authorization`、`cost`、`model`。只有当一条已晋升、
哈希完好的记忆规则允许该答案时，`authorization` 才是 `verified_judgment`。

两种校验类型，都刻意保持狭窄：

- `source-consistency-v1` —— 记录仍与它引用的来源回执一致；
- `lineage-consistency-v1` —— 写回的结论仍与它所源自的已晋升记录一致，
  且没有新增支持。

两者都不证明被引用的断言在现实世界中为真，也没有任何 API 会返回
暗示相反情况的状态。

## 安装

```bash
cd public-runtime
python -m pip install .            # 运行时，无硬依赖
python -m pip install ".[dev]"     # + pytest、jsonschema（测试套件）
python -m pip install ".[model]"   # + laya / huggingface_hub / torch（真实推理）
```

需要 Python 3.10+（在 3.11.9 上验收）。`requirements-lock.txt` 是验收环境
的完整 44 包闭包，从已安装的发行版读取而非由解析器生成；已确认它在干净
venv 中作为整组可解析（`uv pip install --dry-run -r requirements-lock.txt`
→ 44 包，exit 0），该命令不下载任何东西，因此不构成"每个 wheel 都重新
下载过"的主张。仅从 `pyproject.toml` 解析会向上漂移，可复现性以锁文件为准。

## 使用

```bash
# 就绪检查，不下载任何东西
cognitive-runtime doctor --store ./demo.sqlite

# 一次请求走完整条链
cognitive-runtime infer --input <pkg>/defaults/examples/request.json --store ./demo.sqlite --namespace demo

# 第二个进程读取第一个进程持久化的记忆
cognitive-runtime infer --input <pkg>/defaults/examples/request.json --store ./demo.sqlite --namespace demo

# 检查 / 维护存储
cognitive-runtime memory seed   --store ./seeded.sqlite --input <pkg>/defaults/examples/seed-records.jsonl
cognitive-runtime memory verify --store ./seeded.sqlite
cognitive-runtime memory inspect --store ./seeded.sqlite
cognitive-runtime memory clear --store ./seeded.sqlite --yes   # 无 --yes 时拒绝执行

# 针对固定 checkpoint 而非 mock 运行
cognitive-runtime --config <pkg>/defaults/laya-offline.json infer --input <pkg>/defaults/examples/request.json --store ./real.sqlite
```

`<pkg>` 是已安装的 `cognitive_runtime/defaults` 目录
（`python -c "import cognitive_runtime.config as c;print(c.DEFAULT_DIR)"`）。

退出码：`0` = 已运行，`answered` 与 `abstained` 都是正常结果；
`2` = 输入非法或被禁止，或破坏性命令未带确认；
`3` = 未运行（provider 没有产出可用提案，因此没有任何答案被授权，
链路的任何环节都不得读作通过）。

调用方以 `verified`、`trusted`、`gold` 或 `expected` 名义递交的记录会在
门禁之前被拒收——见 `sanitize.py`。允许写入种子记忆，但 `memory seed`
只写候选记录，只有对照回执注册表的 `memory verify` 能晋升它们。

## 模型身份（固定 revision，不捆绑权重）

- 提案模型：`convaiinnovations/laya`，revision
  `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`；`model.safetensors`
  842,609,210 B，SHA-256 `891102d3…cbcb8d86c`，已验证与上游 LFS digest
  一致。该 revision 的许可：`apache-2.0`。
- 快照只附带 `encoder/config.json`。2026-11-05 实测：`laya 0.3.20`
  以未训练状态建网（`pretrained=False`），然后从 Laya checkpoint 本身
  加载全部参数——编码器也包括在内——因此推理**不会**下载
  `answerdotai/ModernBERT-large` 权重
  （`45bb4654a4d5aaff24dd11d4781fa46d39bf8c13`，`apache-2.0`）。该权重
  仍被独立下载并核验了哈希（`model.safetensors` = `44510fec…`，
  1,583,544,840 B），记录在 `SOURCE-INVENTORY.md` §1；
  `acceptance/PR-M1.md` 第 2 项的真实模型 smoke 在两个 hub 开关均为
  离线模式的条件下运行。
- 本包从不捆绑权重，也从不盲信缓存命中：`verify_integrity()` 会对固定
  文件做哈希校验，不一致即拒绝运行。

`MODEL_CARD.md` 承载身份、预期用途与限制。

## 本包不做的主张

没有 Transformer 参数增长、没有开放域自主学习、没有稳定的长期正增益、
没有生产就绪。判断规则集是一个合成的"Directory record: X is assigned
to Y"单模板；示例是合成的；证据绑定于任务与协议。

使用前值得阅读的已知限制：

- 来源一致性 ≠ 外部真实性；
- 记忆命中会短路获取步骤，因此在存储被清空或该记录校验失败之前，
  源文件中更新的冲突回执不会被查看；
- 检索是 `entity-token-v1`，刻意保持确定与"笨"；
- 如果存储行在磁盘上被改动后某请求重新获取，该行会被隔离，然后从
  回执重写——被篡改的文本永远不会授权任何东西，但恢复方式是重新
  校验，而不是永久拒绝整个存储；
- `cost.monetary_cost` 为 `null` 是因为未知，不是因为为零。

## 文档

| 文件 | 用途 |
|---|---|
| `PROJECT-PLAN.zh-CN.md` | 里程碑范围与验收勾选项 |
| `ARTIFACT-SPEC.zh-CN.md` | 接口、目录与 manifest 契约 |
| `SOURCE-INVENTORY.md` | 实测的许可、revision、哈希、复用清单 |
| `MODEL_CARD.md` | 身份、预期用途、限制 |
| `acceptance/PR-M1.md` | 逐项 Pass / Fail / NOT_RUN 及命令 |
| `RELEASE-MANIFEST.json`、`SHA256SUMS` | 构建身份 |
| `PAPER-ARTIFACT-NOTE.md` | 与封存论文实验的关系 |
| `RELEASE-CHECKLIST.md` | 任何上传之前必须为真的事项 |
| `TASK-LEDGER.zh-CN.md` | 逐轮执行记录 |
| `AGENT-HANDOFF.zh-CN.md` | 下一里程碑实现者的契约 |

## 三阶段发布路线

| 里程碑 | 目标版本 | 交付物 | 当前状态 |
|---|---|---|---|
| PR-M1 | v0.1.0 | 最小完整研究运行时：固定模型、结构化推理、持久记忆、判断、校验与写回/重放 | 已实现；本地验收通过并含真实冻结模型 smoke（离线 CPU）；未上传 |
| PR-M2 | v0.2.0 | 更易部署：批处理/API 访问、简单本地 UI、安装检查与兼容性文档 | NOT_STARTED |
| PR-M3 | v0.3.0 | 实验性对话与有界网络学习回路，带来源、取消与资源限制 | NOT_STARTED |

每个里程碑在验收检查通过后产出一个带版本的发布。后续里程碑保持早前
行为与配置兼容。这些是交付目标，不是"未来能力已经可用"的主张。
PR-M3 实现的是一个实验性学习机制；它不建立可靠的开放域自主学习或
长期自我成长。

三个阶段均以记忆和经验沉淀驱动的复合系统为对象，不以模型参数成长为
验收条件。阶段完成后更新同一个模型/运行时仓库；Hugging Face 为拟定
主渠道，ModelScope 为可选镜像。平台具体规则、账号和仓库目标在实际
发布前核实。无需公开历史实验数据。

## 发布门槛

许可问题已回答（`LICENSE`，Apache-2.0，owner 于 2026-11-05 决定），
构建不再携带 `Private :: Do Not Upload` 守卫，真实冻结模型 smoke 已经
运行（离线、CPU，`acceptance/PR-M1.md` 第 2 项）。目前阻止上传的纯属
程序事项：尚未指定目标账号与仓库名，revision `55cf4c4e…` 尚未被批准
为发布 revision。在两者都记入 `RELEASE-CHECKLIST.md` 之前，本目录是
一个本地候选——不是一个发布。
