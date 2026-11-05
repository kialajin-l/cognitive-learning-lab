# 公开包来源与许可清单（SOURCE-INVENTORY）

版本：v2（PR-M1 第 1 步产物，第 5 步验收后更新）。日期：2026-11-05。状态：`AUDIT_COMPLETE / PACKAGE_BUILT / MOCK_ACCEPTED / REAL_MODEL_SMOKE_NOT_RUN / NOT_UPLOADED`。

本文件是公开产物，按 `ARTIFACT-SPEC.zh-CN.md` 第 15 行要求**不含本机绝对路径**；本机路径与缓存位置记录在 `TASK-LEDGER.zh-CN.md`，构建时由 allowlist 排除。

## 审计方法

- 外部仓库全程只读，未写入、未 checkout、未 stash。
- 每条结论的证据类型标注为：`H`=文件 sha256 实测；`G`=git 跟踪状态/commit 实测；`M`=包元数据（PyPI `metadata()` / HF `model_info(files_metadata=True)`）；`F`=文件系统大小实测；`D`=文档正文；`R`=本地实测运行（命令 + 退出码，见 `acceptance/PR-M1.md`）。
- 未实测的项显式标注 `未验证`，不进入验收计数。

## 1. 上游模型资产

| 项 | 值 | 证据 |
|---|---|---|
| 模型仓库 | `convaiinnovations/laya` | M |
| 固定 revision | `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851` | M（该 revision 解析成功，等于仓库 HEAD） |
| 上游 lastModified | 2026-09-24T05:39:22Z | M |
| 权重许可 | `apache-2.0`（HF card_data `license` 字段 + tag `license:apache-2.0`） | M |
| `model.safetensors` | 842,609,210 B；上游 LFS sha256 `891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c` | M |
| 本机快照同一文件 sha256 | `891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c` | H |
| 完整性结论 | 本机权重与上游 LFS oid **逐字节一致** | H+M |
| `tokenizer/tokenizer.json` | 3,583,228 B | M+F |
| `rl_agent_config.json` | 745 B | M+F |
| `encoder/config.json` | 2,083 B | M+F |
| 编码器上游 | `answerdotai/ModernBERT-large`，revision `45bb4654a4d5aaff24dd11d4781fa46d39bf8c13`，许可 `apache-2.0` | M（配置文件声明 + HF 元数据） |
| 编码器权重（上游） | `model.safetensors` 1,583,544,840 B；上游 LFS oid `44510fec5d3a81a1877f225637b869495f18e55f6f23a09abb9be0acc030295f` | M+F |
| 编码器权重（属主自下载副本） | `model.safetensors` 1,583,544,840 B，实测 sha256 **等于**上游 oid `44510fec…`（2026-11-05 属主经镜像/迅雷自行下载后提供本地路径，本会话只校验不下载）；同批 4 个附属文件大小全部与基准一致，实测 sha256：`config.json` `55dca680…`、`tokenizer.json` `9fd55248…`、`tokenizer_config.json` `3cd2017f…`、`special_tokens_map.json` `ea97ecdb…` | H+F |
| 编码器附属文件（上游基准） | `tokenizer.json` 2,132,967 B、`tokenizer_config.json` 20,810 B、`config.json` 1,194 B、`special_tokens_map.json` 694 B | M+F |
| **编码器权重在推理中的实际作用（实测修正）** | `laya 0.3.20` 以 `pretrained=False` 建网，**全部参数（含编码器）来自 Laya checkpoint**（`load_state_dict(strict=True)`）；快照内的 `encoder/config.json` 只作配置读取。`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` 下真实 `infer` 成功，证明无任何隐式联网获取。编码器权重下载后**未参与**本次 smoke | H+D |

**获取方式（实测修正，2026-11-05）**：上文「正式路径需要两次下载」是依据上游卡片与快照布局的推断；实测 `laya/agent.py` 的加载路径（`pretrained=False` + 本地 `encoder/config.json` + 本地 `tokenizer/`）使**真实推理只需 Laya 快照一次获取**。编码器权重由属主另行下载并校验（上行实测 sha256），但在 `laya 0.3.20` 的推理中不参与计算——保留该记录是因为：未来版本若改回 `pretrained=True` 或换用其它加载路径，该 1.47 GiB 依赖会立即复活。`rl_agent_config.json` 的 `encoder` 字段仍为该 repo ID。

**模型能力面**：有限选项的 typed choice/score，`model_id="laya:root"`；**不是自由文本生成模型**。`rl_agent_config.json` 声明 `max_len=512`、`head_max_len=192`、`amp_dtype=bf16`、`fine_tuned_from_checkpoint=true`（7313 updates / 1 epoch）。`calibration_status=uncalibrated`，置信度不得当作校准概率。

## 2. 第三方运行时依赖

| 包 | 本机版本 | 许可 | 角色 | 正式路径必需 |
|---|---|---|---|---|
| `laya` | 0.3.20 | Apache-2.0（PyPI `License`，Author `Convai Innovations`） | 模型加载与推理运行时 | 是 |
| `huggingface_hub` | 1.33.0 | Apache-2.0 | `snapshot_download` | 是 |
| `jsonschema` | 4.26.0 | MIT | schema 校验 | 是 |
| `torch` | 本机已安装 `2.14.0+cpu`（`import torch` 实测，R）；经 `laya` 间接引入，**未在 AnchorJudge `pyproject` 声明** | `License-Expression` 实测为 `Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT`（M，`importlib.metadata`） | 张量后端 | 是（M1 必须显式固定） |
| Python | 3.11.9（AnchorJudge 要求 `>=3.10`） | — | 运行时 | 是 |

`requirements-lock.txt` 现为**完整 44 包闭包**：原 23 条 pin 之外，另把干净环境安装同样会拉入的 21 个传递依赖（torch 的 `sympy`/`networkx`/`mpmath`/`jinja2`、httpx 的 `anyio`/`h11`/`httpcore`/`certifi`/`idna`、huggingface_hub 的 `rich`/`typer`/`shellingham` 等）按本机 `importlib.metadata` 实测版本补齐（R）。全部 44 条在新建 venv 中 `uv pip install --dry-run -r` 可共同解出（`Resolved 44 packages`，exit 0，R）；但 dry-run 只取元数据、不下载 wheel，也未固定包 hash，因此**不**等于逐字节复现。仅用 `uv pip compile pyproject.toml` 求解会上漂（torch 2.15.0、transformers 5.22.1、numpy 2.4.6、pytest 9.2.0、typing-extensions 4.16.0，2026-11-05 实测），因为 `pyproject` 只钉了 laya / huggingface_hub / jsonschema——复现口径以本锁文件为准。44 包许可逐项登记在 `THIRD_PARTY_NOTICES.md`。

## 3. 外部仓库 AnchorJudge：不作为依赖，不复制其源码

| 事实 | 值 | 证据 |
|---|---|---|
| commit | `40a8378d96098d6c5968ec251446c2994dd70ee9`，2026-09-26，共 6 次提交，分支 `feature/laya-adapter` | G |
| 远程 | `git remote -v` 为空，**无远程仓库** | G |
| 工作树 | **不干净**：`probe.py`、`provider.py`、`questions.py`、`tests/test_questions.py` 已修改未提交；`.tmp/` 未跟踪 | G |
| 许可声明 | `pyproject.toml:10` 写 `license = { text = "Apache-2.0" }`，但仓库内**无 LICENSE / COPYING / NOTICE 文件**，源码无版权头 | G+D |
| schema 一致性 | 其 README 声称与本仓库 schema「逐字节一致」，**input schema 实测不一致**：AnchorJudge `866c1c1bad69c62e5708e605c642358a24cf99482f74b75215e8e426439b72a9` vs 本仓库 `d23f7b1a0a70f7818eec46eb8a5734cf05efcb5c1a0bb90d2933ca8953b2ffae`；output schema 一致（`22ae39d2…`）。差异为本仓库新增 `memory_evidence[].content`（maxLength 2000） | H |

**决策与理由**：许可全文缺失 + 被引用代码处于未提交状态 → 没有可审计、可再分发的基线。公开包只参照其**行为契约**（revision 强制门禁、`provider_class ∈ {mock, real}`、abstain 阈值、错误降级不冒充成功）在 `public-runtime/` 内重写，不复制源码、不声明依赖。本包以本仓库 schema 版本为准，并在本节记录差异。

## 4. 本仓库自有代码引用点

许可现状（审计时点的事实，保留原文）：全仓 tracked 文件 grep `licen|copying|copyright` **0 命中**，根目录**无 LICENSE 文件**，`runners/` 文件头无版权声明；git 作者单一（`kialajin`）。`PROJECT-PLAN.zh-CN.md` 第 18、89 行的 Apache-2.0 当时仍是**建议，未作授权声明**。

2026-11-05 更新：`public-runtime/` 已带 `LICENSE`（Apache-2.0，见第 6 节），`pyproject.toml` 声明 `license = "Apache-2.0"`。**仓库根目录依旧没有 LICENSE**，`runners/` 文件头依旧无版权声明——本包的许可声明只覆盖 `public-runtime/` 内的运行时代码，不自动延伸到归档实验脚本。

| 参考文件（仓库相对路径） | sha256 | git 状态 | M1 处理方式 |
|---|---|---|---|
| `runners/decision_d1_runtime_boundary.py` | `163a75205b1a6e530243618ca3505e69354eb9d9562bbd2479725ff542837861` | **UNTRACKED** | 语义参照，重写 |
| `runners/decision_d1_judgment_adapter.py` | `e3fdb95d048ca95edbfeb1e985cac53a3b653b8cb49e7657c763a9c8e20e9b81` | **UNTRACKED** | 语义参照，重写 |
| `runners/decision_d1_rule_selector.py` | `b3c1577bb63d90456412b00d462c137a55eaacfe9a388d2bf8c6025a93f1a2a8` | TRACKED | 可适配 |
| `runners/isolated_store.py` | `c7b629bc9e332817bc28587d5f9aa1053c2f6f859a66428795541f51011fae62` | TRACKED | 可适配 |
| `runners/decision_d1_r119_store_worker.py` | `6d34412e867c288beb1c44921fb94e3657635184759b2a23eccff89c3297b83f` | **UNTRACKED** | 语义参照，重写 |
| `runners/lsg_open_source_adapter.py` | `7460cdd8d86796ea8e7ab7c597e50ccae5ee50b2afdbc8580b65b71606f3e93a` | TRACKED（有他人未提交修改） | 语义参照，重写（不复用他人未提交内容） |
| `gates/memory_quality_gate.py` | `8114e1a7cb123f37c84effe9702b72ae938695e0cb485693b9c7708af83118e0` | **UNTRACKED** | 语义参照，重写 |
| `gates/lsg_sg4_r3_d69_proof_gate.py` | `cae6bd7161785a3762c31c5e990886dde9d376786ca1a8d43aa882bf8f8927d5` | **UNTRACKED** | **不复用**（见第 5 节第 4 条） |
| `selectors/lsg_k_selector.py` | `4c4c2c17d96497fdfadead8a5696f1ee35d990eb9430ba6b8afa43f675383dba` | **UNTRACKED** | 语义参照，重写 |
| `schemas/phase2d-decision-input.schema.json` | `d23f7b1a0a70f7818eec46eb8a5734cf05efcb5c1a0bb90d2933ca8953b2ffae` | **UNTRACKED** | 按公开包语义重新定义 |
| `schemas/phase2d-decision-output.schema.json` | `22ae39d2f6a3c3d0b2b6afc3ba974c74699eb5229e1e2d7ba2b5c896810bbb74` | **UNTRACKED** | 按公开包语义重新定义 |
| `schemas/decision-d1-judgment-output.schema.json` | `3d7c24eba72e0d4b03f452a760e77680095661bd46b98c76c95817c3e0d19ec5` | **UNTRACKED** | 按公开包语义重新定义 |

schema `$id` 自述为 `DRAFT; R0/R1 static planning artifact, never scientific evidence`——公开包不得沿用该自我定位，需在 M1-3 重新定义稳定 schema 版本。

## 5. 审计发现的缺口（M1 必须处理，不接受规划表述覆盖实测）

1. **规划第 15 行「本仓库已有 runner、gate、schema、selector」在版本控制层面部分不成立**：`gates/` 4 个文件 **0 tracked**、`selectors/` 3 个 **0 tracked**、`schemas/` 13 个中 **3 tracked**、`runners/` 1908 个 `.py` 中 **356 tracked**。「已验证跑通」的证据链大半不在版本控制里。处理方式：公开包不依赖这些未提交文件；上表逐条登记 sha256 与跟踪状态，作为行为参照。
2. **没有独立的检索模块**：`"retriever": "entity-token-v1"` 只是 runner 内的行内字符串，实体 token 匹配逻辑写在实验脚本里，无 import 入口。规划第 29 行「接入查询相关检索」在 M1 属**新写**，不是抽取。（M1-4 已新建 `retrieval.py`，`RETRIEVER_VERSION="entity-token-v1"`，先精确实体再 token 重叠、以 memory_id 决定同分次序；`tests/test_chain.py` 覆盖命中与复用。）
3. **记忆记录缺验证状态字段**：SQLite 表 `memories(write_id, sequence_id, repeat_no, record_json, content_sha256)` 无 verification 列，`verification_status` 只出现在 verifier 与报告 JSON 中。不满足 `ARTIFACT-SPEC` 第 46 行「验证类型/版本、晋升状态随记忆存储」，公开包 store 需重新设计。（M1-4 已重设计：`memory/store.py` 表含 `verification_type/version/status/detail`、`promotion_state`、`related_ids`、`schema_version`、`namespace`、`content_sha256`、`captured_at`、`retriever_version`；写入恒为 `candidate/unverified`，`promote()` 在无 pass 或 hash 不符时抛 `PromotionUnauthorized`。）
4. **证明门使用测试夹具密钥**：`gates/lsg_sg4_r3_d69_proof_gate.py` 的 Ed25519 私钥派生自字面量 `"D69-R1 TEST FIXTURE KEY ONLY - NOT A PRODUCTION TRUST ROOT"`。公开包**禁止**把它当信任根——那等于出厂自带一把假签名密钥。M1 的校验语义改为「内容 hash + 来源 + 规则版本 + 授权标志」的可核对记录，不假装密码学信任根；如将来引入真实密钥，另行设计密钥管理并单独验收。（M1-4 已按此实现：`sources.py` 的 `source-consistency-v1` 与 `lineage-consistency-v1`，无签名、无密钥、无「可信根」措辞；`verify_record()` 拒绝缺 ref/未知 ref/hash 不符/内容与实体不符。）
5. **本机 HF 缓存非标准布局**：`blobs/` 为空，快照内文件是普通文件而非 LFS 符号链接。因此**不能**用缓存文件名或「缓存命中」推断完整性，必须按 sha256 显式校验——本清单第 1 节已用该方法完成一次核对。（M1-3 已实现为门禁：`model/laya.py::verify_integrity()` 对 `model.safetensors` 比对固定 digest，不符即 `ModelIntegrityError`，不调用模型。）
6. **无 DLLM-0 调用代码**：`PROJECT_BOUNDARY.zh-CN.md` 将其权重列为只读外部资产，规划第 17 行默认不纳入本包。M1 不含 DLLM-0 路径。
7. **`MODEL_CARD.md` 五项曾为 TBD**：M1-5 已用本清单实测值回填（模型名/来源 revision/SHA-256/许可/运行时包版本），并把「已评估行为」限定在 mock 链路，真实模型行为标注为未测。

## 6. 待人工决定（只阻断相关发布动作，不阻断开发）

2026-11-05 由属主决定的三项（决定即证据，记 `D`，不推断）：

- ~~自有运行时代码许可证选择~~ → **已决定 `Apache-2.0`**。新增 `LICENSE`（Apache-2.0 全文 + 本包版权声明，11,978 B，sha256 `d55f3052cc51ef8bb0fb0161b55f98d93cb7542c1c6b19e1ebf5655a8c1408a1` `H`），`pyproject.toml` 改为 `license = "Apache-2.0"` + `license-files = ["LICENSE"]`，并移除 `Private :: Do Not Upload` classifier。该许可**只覆盖本包代码**，不对上游权重重新授权。
  构建事实：setuptools 80.10.2 对「SPDX 表达式 + `License ::` classifier」并存报 `InvalidConfigError`（PEP 639），已删除 classifier 并把 `build-system.requires` 提到 `setuptools>=77`。
- ~~是否在发布包中附带 842 MB 权重~~ → **已决定薄包**：wheel + sdist 不含权重，权重与编码器按固定 revision + sha256 现取或指本地目录，hash 不符即拒跑（`model/laya.py::verify_integrity()`）。
- ~~发布目标渠道~~ → **已决定 Hugging Face**，账号由属主提供。

仍未定，且继续阻断上传动作：

- ~~发布目标**账号与 repo ID**~~ → **已决定（2026-11-05）**：Hugging Face 账号 `WayneRR`（write token 经只读 `whoami` 实测有效；对 HF 的认证请求必须直连，走本机代理会被 401 拒绝——两次 401 的根因即此），目标 repo **`WayneRR/cognitive-learning-lab`**（model repo）。
- ~~`55cf4c4…` 是否被批准为**发布** revision~~ → **已批准（2026-11-05，属主明确批准）**：`55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851` 为发布 revision。
- ~~编码器权重获取~~ → **已解决并实测修正**（2026-11-05）：属主自行下载后提供本地路径，五件文件按 §1 基准校验一致（`model.safetensors` sha256 精确等于 `44510fec…`）。真实 smoke 随即跑通且发现编码器权重在 `laya 0.3.20` 推理中**不参与计算**（见 §1 实测修正行）——第 2 项验收由 `NOT_RUN` 转 **Pass**。

上述决定齐备后进入发布执行。当前状态：**本地验收 7/7 全 Pass**（含真实模型 smoke），`READY_TO_UPLOAD` 条件已满足；实际发布状态以 `RELEASE-CHECKLIST.md` 与 `RELEASE-MANIFEST.json` 的 `publication` 块为准（上传后须记录远端 URL/revision 与下载/hash/smoke 复核）。

## 7. M1 实施后的登记更新（第 2–5 步）

| 变更 | 影响 | 证据 |
|---|---|---|
| 默认配置与示例移入包内 `src/cognitive_runtime/defaults/`（原 `ARTIFACT-SPEC` 顶层 `configs/`、`examples/`） | 分离布局下构建出的 wheel 缺 `SourceRegistry`，安装后静默 abstain；入口与字段不变，`ARTIFACT-SPEC` 目录段已同步 | R（`acceptance/PR-M1.md` 第 1 项） |
| 不引入任何签名/密钥 | 校验语义为 hash + 来源 + 谱系，第 4 节第 4 条缺口按此关闭，包内无测试夹具密钥 | R+D |
| provider 无可用提议（`schema_failure`/`timeout`/`runtime_error`）→ 顶层 `provider_error` + 退出码 3，不产出 `answered` | 模型未运行时不能凭记忆答题冒充链路通过；模型 `abstain` 仍是可用提议，照常走 gate | R |
| `proposal_agrees_with_judgment` 改为两侧都比候选文本 | 原实现比较 `candidate_id` 与文本，该信号恒为 `false`（出厂即失效的指标）；现正负两向都能触发 | R |
| 新增合成示例 `defaults/examples/seed-records.jsonl`（含一条无 receipt 的记录） | 演示第二条入记忆路径：`memory seed` 只写 candidate，`memory verify` 才可能晋升；无 receipt 者 `unknown_source_ref` 拒绝 | R |
| 包内不复制外部仓库源码，也不声明其为依赖 | `grep -ri "anchorjudge" src/` 0 命中；行为契约（revision 门禁、`provider_class` 区分、失败降级不冒充成功）在本包内重写 | R |
| 记忆命中会短路 acquisition | 冲突负例必须在空 store 上演示；已用测试固定该语义并在 README「已知限制」写明 | R |
| 验收改在真实 venv 复跑（`uv venv` 由该 embedded 解释器建出 `isolated=0` 的环境） | 第 1 项与第 7 项的「console script 靠 bootstrap」条件项关闭：`cognitive-runtime.exe`、`python -m`、wheel 与 sdist 两条安装路径、以及在 site-packages 上跑 27 测试全部原生通过；embedded 解释器的限制属环境，不属包 | R |
| `requirements-lock.txt` 补齐为 44 包闭包并做 dry-run 求解核对 | 原文件只有 23 条，干净环境实际会装 44 个包——即「锁」名不副实；现闭包完整且可共同解出（exit 0），但未下载 wheel、未固定 hash，逐字节复现仍列未做 | R |
| `SHA256SUMS` 由 50 条改为 44 条，剔除 6 个 `src/cognitive_runtime.egg-info/*` | 旧清单把不随包发布、重新构建也无法逐字节复现的构建残留计入 hash，换台机器必然失配；源码树 digest 同步改为 33 文件 `d6aaa4aa…`（旧 `209a1f16…` 含 egg-info）。成因是 `"egg-info" not in p.parts` 永不命中（目录名是 `cognitive_runtime.egg-info`），故改为按 wheel 成员逐名比对 | R |
| 44 包许可改由包自身元数据登记 | `torch` 原记为「BSD-3-Clause（未复核）」，实测 `License-Expression` 为 Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT；`certifi`/`tqdm` 含 MPL-2.0、`typing-extensions` PSF-2.0、`regex` 含 CNRI-Python，6 个包元数据未声明许可（标 `<not declared>`，不计入已验证） | M |
