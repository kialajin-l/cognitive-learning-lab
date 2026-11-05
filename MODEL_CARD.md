# Model Card

Status: PR-M1 runtime implemented and locally accepted; the real-model smoke
**ran** on 2026-11-05 (offline, CPU, pinned local snapshot). Planned versions:
PR-M1/v0.1.0 (complete bounded runtime), PR-M2/v0.2.0 (deployment),
PR-M3/v0.3.0 (experimental conversation and bounded web learning). See
`PROJECT-PLAN.zh-CN.md`; future features are not evaluated capabilities.

## Model identity

- Model name: `convaiinnovations/laya` (upstream frozen checkpoint; not trained,
  renamed or re-branded by this project)
- Source/revision: Hugging Face `convaiinnovations/laya` @
  `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851` (upstream `lastModified`
  2026-09-24T05:39:22Z)
- SHA-256 of `model.safetensors`:
  `891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c`
  (842,609,210 bytes; local copy verified equal to the upstream LFS digest)
- Runtime package revision: `cognitive-runtime 0.1.0`
- License: upstream model card declares `apache-2.0`. This project's own
  runtime code is `Apache-2.0` (`LICENSE`), decided by the owner on
  2026-11-05; that licence covers the code only, not the checkpoint, and does
  not re-license it. The published package is thin — no weights are bundled.
- Encoder dependency: `answerdotai/ModernBERT-large` @
  `45bb4654a4d5aaff24dd11d4781fa46d39bf8c13`, `apache-2.0`. Its
  `model.safetensors` is 1,583,544,840 bytes, upstream LFS digest
  `44510fec5d3a81a1877f225637b869495f18e55f6f23a09abb9be0acc030295f`; the
  owner downloaded it separately and the download was hash-verified.
  Measured 2026-11-05: at inference `laya 0.3.20` does **not** read these
  weights — it builds the network untrained and loads every parameter,
  encoder included, from the Laya checkpoint; only the snapshot's
  `encoder/config.json` is read as configuration. The smoke run in
  `acceptance/PR-M1.md` item 2 executed with the hub in offline mode, which
  also proves no hidden fetch.

## What the model actually does

`laya.load(...).predict(state, questions)` over **one typed `choice` question**
with one option per candidate. It returns a candidate id, per-option
probabilities and an answer confidence. It is a bounded selector over options
the runtime hands it — not a free-text generator, and not able to cite its own
sources.

`rl_agent_config.json` records `max_len=512`, `head_max_len=192`,
`max_prefixes=6`, `amp_dtype=bf16`, and `fine_tuned_from_checkpoint=true`
(7313 updates, 1 epoch). The option budget enforced by this package is 20.

## Calibration

`calibration_status` is reported per run. Laya emits a temperature warning at
load time, which this package maps to `uncalibrated`. Confidence values are
therefore **not** probabilities of correctness and must not be read as such.
The runtime never uses confidence to authorise an answer or a memory promotion.

## Evaluated behavior

Verified in PR-M1, in a clean install outside this repository, using the mock
provider:

- retrieval → verification → promotion → typed judgment → answer, persisted in
  SQLite and reused by a second, independent process;
- abstention with no evidence, with conflicting receipts, with a tampered
  record, with a duplicate candidate set, and with an unknown source ref;
- refusal of caller-supplied `verified`, `gold` or `expected` fields;
- a disagreeing model proposal does not change the authorized answer, and
  `proposal_agrees_with_judgment` compares candidate text on both sides;
- a provider that returns no usable proposal (`schema_failure`, `timeout`,
  `runtime_error`) exits `3` as `provider_error` instead of letting memory
  answer in the model's place — a model that declines (`abstain`) still flows
  through the judgment unchanged.

One end-to-end run then used the **real frozen checkpoint** (`provider_class=
"real"`, offline, CPU): `answered`/`team-north` with
`proposal_agrees_with_judgment=true`, real token usage recorded
(`prompt_tokens=117`), `calibration_status=uncalibrated` (the temperature
warning actually fired), and the writeback promoted with
`verification_status=pass`; a second independent process reused the memory
with `acquisition_calls=0`. That is **one smoke receipt on one synthetic
example on one machine** — it establishes that the pinned checkpoint loads and
the chain runs end-to-end with the real model; it is not an accuracy
evaluation, and nothing above the mock-provider list is claimed beyond it.

Not verified in PR-M1: any accuracy or quality evaluation of the real model,
cross-platform installation, and every capability belonging to PR-M2/PR-M3.

The sealed experiments in this repository carry task- and protocol-bound
evidence for bounded memory retrieval/replay, conflict and tamper rejection,
persistence across controlled restarts, and writeback boundaries. That evidence
was produced by the archived runners, not by this package, and is not
re-attributed here.

## Limitations

Long-horizon memory growth, open-domain autonomous search, universal transfer,
stable positive long-term marginal gain, and model-parameter growth are not
established. Verification in this package proves **provenance consistency** —
that a record still matches the receipt or lineage it cites. It does not prove
the cited claim is true in the world.

## Reproduction

```bash
pip install ./dist/cognitive_runtime-0.1.0-py3-none-any.whl
python -m cognitive_runtime doctor
python -m cognitive_runtime infer \
  --input "$(python -c 'import cognitive_runtime.config as c;print(c.EXAMPLES_DIR/"request.json")')" \
  --store ./memory.sqlite
```

The real-model path additionally needs the `model` extra, network or a local
copy of both upstream files, and `provider: laya` in the config. Until the
real-model smoke is recorded, no claim in this card depends on it.
