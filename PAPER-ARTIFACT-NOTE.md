# Paper artifact note — PR-M1 / v0.1.0

Date: 2026-11-05. Written because `ARTIFACT-SPEC.zh-CN.md` requires this note
from M1 onward, and because a reader must not be able to mistake this package
for the experiments behind the sealed research report.

## Identity and availability

| Field | Value |
|---|---|
| Artifact | `cognitive-runtime` 0.1.0 (PR-M1) |
| Wheel | `dist/cognitive_runtime-0.1.0-py3-none-any.whl`, 46,448 B, SHA-256 `64e02c1ab36023f4ae66c6da0d0ba6fba959bd88664d6b37590b3905c71f28e1` |
| Source package | `dist/cognitive_runtime-0.1.0.tar.gz`, 51,237 B, SHA-256 `d69ad3ce98d3a63fdf2519724675f599920b4173cf3a4a381bee00b6fc9b0213` |
| Public URL | `https://huggingface.co/WayneRR/cognitive-learning-lab` (model repo, published 2026-11-05; latest content commit `5ccf3666`; initial publication commit `4225068d`). Artifacts are also attached to GitHub Release v0.1.0 of the source repository |
| Source-of-truth repository | the private working repository, branch `public-runtime-m1`; this bundle is the public-safe subset. The public source copy lives at `https://github.com/kialajin-l/cognitive-learning-lab` |
| Code license | `Apache-2.0` (`LICENSE`), owner decision 2026-11-05; covers the package's code only, not the upstream checkpoint. Package is thin — no weights bundled |

## How to obtain and run it

```bash
python -m pip install ./dist/cognitive_runtime-0.1.0-py3-none-any.whl   # or: pip install .
python -m cognitive_runtime doctor --store ./memory.sqlite
python -m cognitive_runtime infer --input "$(python -c \
  'import cognitive_runtime.config as c;print(c.EXAMPLES_DIR/"request.json")')" \
  --store ./memory.sqlite --namespace demo
python -m pytest tests -q --basetemp=<tmp> -p no:cacheprovider   # 28 tests, from the source tree
```

The `--basetemp` and `-p no:cacheprovider` flags were needed on this audit
machine (`PermissionError [WinError 5]` on a `pytest-of-<user>` temp directory
it cannot write). They are harness workarounds, not part of the package;
whether a plain `python -m pytest tests -q` works elsewhere is not verified
here.

The default provider is `mock`. The real provider needs the `model` extra and
one upstream download (`convaiinnovations/laya@55cf4c4e…`) — or a local
directory, which is what the smoke in `acceptance/PR-M1.md` used. Measured
correction to earlier text: the `answerdotai/ModernBERT-large` weights are not
read at inference on `laya 0.3.20`; see `MODEL_CARD.md`.

## What this package is a contribution of

An engineering artifact: the runtime boundary the research line kept needing —
input sanitising before the gate, integrity-checked memory, retrieval, a
fail-closed typed rule judgment, a three-layer boundary that separates a model
proposal from an authorised answer, receipt/lineage verification, controlled
writeback, and cross-process replay — packaged so it installs and runs without
the private repository, and without any answer keys or task sets.

## Correspondence with the sealed experiments

The frozen research record for this mechanism is
`docs/LSG-SG4-R3-D708-FINAL-VERDICT-v1.zh-CN.md` (2026-10-29) inside
`docs/LSG-SG4-R3-PROJECT-BOUNDARY-CLOSEOUT-SCOPE-v1.zh-CN.md`, status
`PROJECT_SCOPE_CLOSED`. Mapping of ideas, not of numbers:

| Sealed experiment line | What it studied | What this package does with that |
|---|---|---|
| R23–R25, R27, R35–R37 memory participating in decisions | retrieval + evidence into the decision | reimplemented as `retrieval.py` + `judgment.py`, on a new synthetic task domain |
| R16–R19, R29–R30 correct writeback and reuse | verified writeback surviving replay | reimplemented as `pipeline._writeback` + `lineage-consistency-v1` |
| R26/R28, R40 rejecting contaminated memory and conservative abstention | pollution rejection, refuse when undecidable | reimplemented as fail-closed `select_rule` reasons and `sanitize.py` refusal of caller trust fields |
| R39/R44/R46/R47 conflict handling | multi-source conflict, partially unresolved | only the narrow single-assignment conflict is implemented: two promoted rules that disagree → `conflicting_verified_rules`, no answer, no writeback |
| R31–R34, R37, R48 open-web acquisition | autonomous search, `3/8` admission on open web | **not implemented** — that is PR-M3 scope, and the sealed evidence does not support it being reliable |
| long-horizon positive gain | explicitly unverified | explicitly not claimed; nothing here measures learning over time |

## Differences a reader must not overlook

1. **Different code path.** The sealed numbers were produced by archived
   `runners/` scripts against sealed task sets and local-state model assets.
   This package re-implements the boundary in `cognitive_runtime` and has never
   been run on those task sets. Equal semantics are not assumed, and no
   R-number result is re-stated as a property of this package.
2. **Different evidence class.** The acceptance evidence in
   `acceptance/PR-M1.md` comes from the mock provider plus synthetic
   `Directory record: X is assigned to Y` fixtures. The single real-model
   receipt (2026-11-05, offline CPU, `provider_class="real"`) is a load-and-run
   smoke on one of those same synthetic examples — it proves the pinned
   checkpoint drives the chain end-to-end; it is **not** an accuracy result and
   adds no evidence toward any paper claim. This package has never been run on
   the sealed task sets.
3. **No answer keys, no trust root.** The paper experiments used held-out
   answer keys in a separate evaluation path. This package refuses fields that
   look like answer keys or trust assertions (`gold`, `expected`, `verified`,
   `trusted`, `ground truth`) at the input boundary, and ships no signing key —
   verification means hash + cited receipt + lineage, which is provenance
   consistency, not truth.
4. **Scope of "memory growth".** The closed project's question was whether
   memory can participate in decisions and show observable gain, plateau or
   degradation under a controlled loop. This package answers the narrower
   engineering question of whether that boundary can be installed and
   reproduced at all. Gain is not measured here.

## Reading order for a reviewer

`README.md` → `acceptance/PR-M1.md` (what actually passed, what did not) →
`SOURCE-INVENTORY.md` (licenses, revisions, hashes, audit gaps) →
`MODEL_CARD.md` (model identity and limitations) → the sealed verdict document
above for the research claims, which this note neither repeats nor extends.

M2 and M3 will update this note with their own version, run method and
correspondence changes. This note does not modify any sealed experiment,
figure, or research conclusion, and adds no new D/R numbering.
