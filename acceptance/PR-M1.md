# PR-M1 / v0.1.0 acceptance report

Date: 2026-11-05. Branch `public-runtime-m1`, package `cognitive-runtime 0.1.0`.
Status: `LOCAL_ACCEPTED_REAL_MODEL_SMOKE` — all seven items measured **Pass**;
the only remaining gap to upload is procedural (destination account/repo id and
publication-revision approval, `RELEASE-CHECKLIST.md`), not evidence.

Evidence tags follow `SOURCE-INVENTORY.md`: `R` measured local run (command +
exit code) · `H` measured file SHA-256 · `M` package/upstream metadata ·
`F` measured filesystem size · `G` git · `D` document.

Harness note: the acceptance runs happen in a directory **outside** the
repository, against the installed artifact only. The audit interpreter is an
embedded build (it ships `python311._pth`, so it runs isolated —
`sys.flags.isolated=1`, `ignore_environment=1`, `safe_path=True`, `PYTHONPATH`
ignored — and has no `venv` or `virtualenv` module). Two isolation mechanisms
were used, and the second one is the stronger:

- earlier rounds: `pip install --target <dir>` plus a one-line bootstrap,
  because no venv module existed;
- this round: `uv venv <dir> --python <audit interpreter> --seed`, which
  produces a **normal** environment (`isolated=0`, own `sys.prefix`, pip 26.3,
  working console scripts). Every command below was re-run through the real
  `cognitive-runtime.exe` console script in that venv, so the bootstrap
  workaround is no longer load-bearing.

This is an environment property, not a package property: `pip install .` from
the source tree and the built wheel both produce a working package here.

## Acceptance items

### 1. Install outside the repo from the build artifact, no private reads — Pass `R` `H`

```bash
python -m pip wheel --no-build-isolation --no-deps --wheel-dir dist .   # rc=0
python -c "from setuptools import setup; setup()" sdist --dist-dir dist # rc=0
python -m pip install --no-deps --no-index --target <isolated>/site \
    cognitive_runtime-0.1.0-py3-none-any.whl                            # rc=0
python -m pip install --no-deps --no-index --no-build-isolation \
    --target <isolated2>/site cognitive_runtime-0.1.0.tar.gz             # rc=0
```

Artifacts as of that round (this build was later superseded — see the
re-verification sections at the end of this report for the current identity):

- `cognitive_runtime-0.1.0-py3-none-any.whl`, 42,118 B `F`, SHA-256
  `0c700b2ff66d3541b020df327bfe7a6abc8cfa62f73c828054aa67f26f005bcf` `H`
- `cognitive_runtime-0.1.0.tar.gz`, 41,209 B `F`, SHA-256
  `f46de08c03e0dbb7def1b520e42ad5bd424e0d646c9d97fc2c07bf57b99faf71` `H`

Each is an instance fingerprint of this build, not a reproducible-build claim
(the tar carries timestamps). The wheel contains 29 package files, and that set
is exactly `src/cognitive_runtime/**` on disk — verified by name, so nothing in
the wheel is absent from the reviewed tree and nothing reviewed is missing from
the wheel. The sdist contains `defaults/` and `schemas/`, and installing from it
ran the full chain: `infer` rc=0, `answered`, `authorization=verified_judgment`,
`proposal_agrees_with_judgment=true` `R`.

The earlier round recorded `94b9ab38…` (wheel, 35,487 B) and `735532f6…` (sdist,
36,524 B). Those hashes were superseded, not corrected: editing `README.md` and
`requirements-lock.txt` changes the sdist payload and the wheel `METADATA`
(which embeds the README), so keeping the old hashes would have described
artifacts that no longer exist. This round superseded them twice more — first
for the lock/README edits (`aa1c122a…` / `0449fe36…`), then for the licence
work (`02a8de59…` / `a91d2229…`, built before the README licence rows were
rewritten). Only the final pair above was recorded as current; the wheel now
carries `License-Expression: Apache-2.0` and
`License-File: LICENSE` in its `METADATA`, and `LICENSE` ships at
`…dist-info/licenses/LICENSE` (verified present after install) and at the sdist
root. Both final artifacts were re-installed and re-verified before their
hashes were written down.

Then, from that install and with the working directory outside the repository:
`doctor` rc=0, `infer` ×2 rc=0, `memory inspect` rc=0, conflict `infer` rc=0,
`seed`/`verify`/`show` rc=0, `clear` rc=2 then rc=0, offline-Laya `doctor` rc=0,
offline-Laya `infer` rc=3. Nothing read `runners/`, `gates/`, tasksets, answer
keys or any private store — the package has no import path to them (no
`PYTHONPATH` injection, and this interpreter would ignore it anyway).
The default sources registry and examples resolve inside
`cognitive_runtime/defaults/`. `python -m pip install --no-deps --target … .`
from the source tree was separately verified to produce the same working
install (rc=0).

**Re-run in real venvs (this round, `R`).** Two fresh venvs, one per artifact,
against the rebuilt wheel and sdist above:

```bash
uv venv <v1> --python <audit python> --seed                       # rc=0
<v1>/Scripts/python.exe -m pip install --no-deps --no-index \
    ./dist/cognitive_runtime-0.1.0-py3-none-any.whl               # rc=0
uv venv <v2> --python <audit python>
uv pip install --python <v2>/Scripts/python.exe \
    dist/cognitive_runtime-0.1.0.tar.gz                           # rc=0, built from sdist
```

From `<v1>` and `<v2>`, with the working directory outside the repository and
only the console script on PATH (`cognitive-runtime.exe` exists in
`<v1>/Scripts`):

| Step | Command | Result |
|---|---|---|
| 1 | `infer` on a fresh store | rc=0, `answered`, `team-north`, `verification.type=source-consistency-v1`, `authorization=verified_judgment`, `memory_hit=true`, `proposal_agrees_with_judgment=true`, `cost={model_calls:1, acquisition_calls:1, monetary_cost:null}` |
| 2 | `infer` again, **separate process** | rc=0, `memory_hit=true`, `acquisition_calls=0`, identical `evidence_refs` |
| 3 | `memory inspect` | rc=0, one record, `promotion_state=promoted`, `content_sha256=4c9c99523a63eb9e…` |
| 4 | `infer request-conflict.json`, fresh store | rc=0, `abstained`, `conflicting_verified_rules`, `authorization=none`, `writeback.allowed=false` |
| 5 | input with `"gold"` injected | rc=2, `forbidden keys in input: $.gold` |
| 6 | `memory clear` / `… --yes` | rc=2 `refused`, then rc=0 `records_removed=1` |
| 7 | `--config <defaults>/laya-offline.json doctor` / `infer` | rc=0 with `blockers=["model_unavailable_or_unverified"]`; **rc=3** `provider_error`, `detail: provider real returned status='runtime_error'` |
| 8 | `<v2>` sdist install, `infer` | rc=0, `answered`, `team-north`, `proposal_agrees_with_judgment=true`, module resolved from `<v2>/Lib/site-packages` |

`python -m cognitive_runtime doctor` also runs rc=0 inside the venv, which it
cannot do on the isolated audit interpreter — confirming that limitation was
the interpreter, not the package. The 27-test suite was run **against the
installed wheel** (`cognitive_runtime.__file__` =
`<v1>/Lib/site-packages/cognitive_runtime/__init__.py`) from outside the repo:
`27 passed`, rc=0 (28 after the worker-invocation regression test added below).

The entire sequence above was **re-run after the licence rebuild** against the
then-current `0c700b2f…` wheel and `f46de08c…` sdist in two new venvs: the same rc
sequence 0 / 0 / 0 / 0 / 2 / (2 then 0) / 0 / 3, `27 passed` (28 after the worker fix) with the module
resolved from site-packages, the sdist `infer` rc=0
(`answered` / `team-north` / `verified_judgment` /
`proposal_agrees_with_judgment=true`), and `LICENSE` present under
`…dist-info/licenses/` in both installs.

### 2. At least one real model call — **Pass** `R` `M` `H`

The offline negative from earlier in this milestone still holds: with
`laya-offline.json` (`allow_download:false`, no `local_dir`), `doctor` rc=0
reports `blockers: ["model_unavailable_or_unverified"]` and `infer` exits **3**
with `provider_error` — the chain reports not-run instead of letting memory
answer in the model's place. No mock result is presented as model evidence.

The real call then ran on 2026-11-05, fully offline:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  <audit python> -m-style bootstrap --config <acc>/laya-local.json doctor   # rc=0
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  <audit python> -m-style bootstrap --config <acc>/laya-local.json \
  infer --input <defaults>/examples/request.json \
  --store <acc>/real2.sqlite --namespace demo                               # rc=0
```

Harness notes, in order of relevance to trust:

- **Measured fact that supersedes the earlier "encoder weights required"
  record:** `laya 0.3.20` builds the network with `pretrained=False` and loads
  every parameter — encoder included — from the Laya checkpoint itself
  (`load_state_dict(strict=True)`); the snapshot's `encoder/config.json` is
  read as configuration only. The 1.58 GiB
  `answerdotai/ModernBERT-large` weights were **not needed** for this smoke.
  The run succeeded with both offline flags set, which also proves no hidden
  hub fetch. The upstream model card's "second download" warning described a
  possible path, not the one this version takes.
- The owner downloaded the five encoder files independently (mirror/Xunlei) to
  a local directory before the run. All five sizes match the recorded
  baselines and `model.safetensors` hashes to
  `44510fec5d3a81a1877f225637b869495f18e55f6f23a09abb9be0acc030295f` exactly
  (`H`, measured this round). They are recorded in `SOURCE-INVENTORY.md` §1 as
  available-but-unused at inference.
- The Laya snapshot was **copied** to an acceptance directory and the copy's
  `model.safetensors` re-hashed to `891102d3…` before loading, because
  `laya.load` may rewrite `tokenizer/tokenizer_config.json` in place — the
  shared Hugging Face cache stays untouched. The provider's own
  `verify_integrity()` then hashed the same file again inside the chain.
- `laya-local.json` pins `model.local_dir` to that copy with
  `allow_download:false`; `doctor` reports `model_digest =
  laya:convaiinnovations/laya@55cf4c4e…`, `identity_warning: null`,
  `blockers: []`.

Measured cold call (fresh store, rc=0):

| Field | Value |
|---|---|
| `status` / `final_answer` | `answered` / `team-north` |
| `model.provider_class` | `real` |
| `model.model_digest` | `laya:convaiinnovations/laya@55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851` |
| `model.calibration_status` | `uncalibrated` (temperature warning detected by the worker) |
| `cost` | `model_calls:1`, `acquisition_calls:1`, `prompt_tokens:117`, `latency_ms:10264` (includes child-process weight load), `monetary_cost:null` |
| `authorization` | `verified_judgment` |
| `proposal_agrees_with_judgment` | `true` |
| `writeback` | `allowed:true`, reason `verified_judgment_allow` |

Second independent process on the same store (rc=0): `answered`,
`acquisition_calls=0` (memory reused, no re-acquisition), `model_calls=1`,
`prompt_tokens=117`, identical `evidence_refs`; `memory inspect` shows the
promoted record `demo:widget-alpha:4c9c9952…` with
`promotion_state=promoted`, `verification_status=pass`, `source_ref=dir-001`.

Both runs used the *installed-from-source-tree* package on the audit
interpreter (the packaged code is byte-identical — `src/` has zero diff with
the wheel members verified in item 1). Item 2 is closed with a real frozen
model, not a mock.

**Defect the real smoke exposed, and its fix (`R`).** Re-running the same
smoke from a *normally installed* wheel (fresh venv, console script) failed
with `runtime_error: laya package unavailable: attempted relative import with
no known parent package`. Cause: the worker was launched as a script file
(`python …/cognitive_runtime/model/laya_worker.py`), which puts that directory
at the child's `sys.path[0]` — where this package's own `model/laya.py`
**shadows the third-party `laya` package**, and the child imports the parent's
module and dies on its relative imports. The earlier successful runs passed
only because the audit interpreter is an embedded build whose `._pth` makes it
ignore the script directory. In other words, the packaged wheel could not run
the real provider on any normal environment — exactly the class of bug that
only a second environment exposes. Fix: the worker is now launched as a
package submodule through a `-c` bootstrap that inserts the package root
(`laya.py::_worker_command`), so `import laya` resolves to the real
third-party package in both layouts; a regression test
(`test_worker_is_imported_as_a_module_not_run_as_a_script`) pins the
invocation shape, and the suite grew 27 → 28, all passing. After the fix the
real smoke passes from both layouts: the installed wheel in a fresh venv and
the source tree on the audit interpreter, identical
`answered`/`team-north`/`verified_judgment` envelopes. Measured on the
installed wheel (fresh store, offline): rc=0, cold
`latency_ms=10283` / `prompt_tokens=117`, replay `acquisition_calls=0` /
`prompt_tokens=117`, writeback `demo:widget-alpha:4c9c9952…`
`promoted`/`pass`; the source tree on the audit interpreter reproduces the
same envelope (`latency_ms=8745`).

Environment note kept honest: the venv used for the installed-wheel real run
needed the model extra (`laya`, `torch`, `transformers`) visible; a venv
created from this embedded interpreter cannot inherit its site-packages
(`._pth` defeats `--system-site-packages`), so the acceptance venv exposes the
base site-packages through a `.pth` file — the standard-layout equivalent of
"model extra installed in the venv". The run stayed fully offline.

### 3. First acquire → verify → write back, second independent process reuses it — Pass `R` `H`

Process 1 (`infer`, rc=0): `status=answered`, `final_answer=team-north`,
`authorization=verified_judgment`, `memory_hit=true`,
`writeback_receipt.written=["demo:widget-alpha:4c9c99523a63eb9e"]`,
`promoted=[same]`, `cost={model_calls:1, acquisition_calls:1, latency_ms:47,
monetary_cost:null}`, `provider_class=mock`.

Process 2, a separate OS process reading the same SQLite file (rc=0):
`status=answered`, `memory_hit=true`, `acquisition_calls=0`,
`evidence_refs=["demo:widget-alpha:4c9c99523a63eb9e"]`,
`content_sha256=4c9c99523a63eb9e82a1a9f1af0ffab469f161d959906cd058f714dd551fa84e`
(= the first 16 hex chars of the memory id, i.e. the id is content-derived and
checkable) `H`.

`memory inspect` on that store returns one record,
`promotion_state=promoted`, `verification_status=pass`,
`source_ref=dir-001`.

A second entry route is covered too: `memory seed` wrote 2 candidates
(`note: seeded records are candidates and unverified`), `memory verify`
promoted the one citing `dir-002` and refused `dir-999` with
`unknown_source_ref:dir-999`, then a `widget-beta` request answered
`team-south` with `acquisition_calls=0` from that promoted record.

### 4. Missing evidence, conflict, tampering, forged `verified` → no unauthorised writeback — Pass `R` `H`

| Case | Result |
|---|---|
| no evidence, no acquire | `abstained`, `abstain_reason=no_verified_matching_rule`, `authorization=none`, `writeback.allowed=false` (test) |
| two receipts disagree (`request-conflict.json`, fresh store) | rc=0, `abstained`, `conflicting_verified_rules`, `authorization=none`, `writeback.allowed=false`, `reason=judgment_conflicting_verified_rules`; both receipts are stored and promoted, yet neither authorises |
| row edited on disk, replay without re-acquire | rc=0, `store_integrity={checked:1, quarantined:1, tampered:[demo:widget-alpha:4c9c99523a63eb9e]}`, `abstained`, `authorization=none`, `final_answer=null`, `memory_hit=false` — the injected `team-south` never authorises anything |
| row edited on disk, replay **with** re-acquire | rc=0, tampered row quarantined first, then rewritten and re-verified from the receipt; answer is `team-north` from the receipt, `acquisition_calls=1`. Recovery is by re-verification, not by trusting the edited content |
| caller sends `"gold": "team-north"` | rc=2, `{"status":"input_error","detail":"forbidden keys in input: $.gold"}` — refused before the gate |
| caller sends `memory_evidence[].verified=true` | rc=2 `ForbiddenInput` (test) |
| provider returns `runtime_error` / `timeout` / `schema_failure` | rc=3 not-run, no answer authorised (test + item 2 above) |
| duplicate candidate ids / texts | `abstain`, `invalid_candidate_set` (test) |

`verification.scope` is always the literal
`"provenance consistency, not external truth"`.

### 5. Raw proposal vs final decision vs verification kept distinct; honest abstains — Pass `R` `D`

Every output envelope carries `raw_proposal`, `judgment`, `verification`,
`writeback`, `writeback_receipt`, `authorization`, `cost` and `model` as
separate objects; `decision-output.schema.json` requires them. In the
conflict case the envelope still shows the two promoted records and the
provider's proposal while refusing to answer. In the disagreeing-mock test the
model proposes `c2`, memory rules say `team-north`, and the answer is
`team-north` with `proposal_agrees_with_judgment=false`.
`abstain_reason` is populated whenever `selected` is null. No test or example
requires all unknown questions to be answered correctly.

Defect found and fixed while writing this report: the flag previously
compared a `candidate_id` against a text, so it could never be true. After the
fix it reports `true` when the provider and the rule agree (re-run steps 3–4,
cold and replay both `proposal_agrees_with_judgment=true`) and `false` in the
disagreeing test — i.e. the signal now actually fires in both directions.

### 6. User-specified store; clearing limited to that store; no background work — Pass `R` `H`

Every store-touching command requires `--store` (or
`COGNITIVE_RUNTIME_STORE`); `resolve_store_path()` raises instead of guessing
a shared location. `memory clear --store X` without `--yes` → rc=2
`{"status":"refused","detail":"clear requires --yes naming the same store you
passed to --store"}`; with `--yes` → rc=0
`{"records_removed":1,"store":"…\\demo.sqlite"}`. `clear()` additionally
compares the confirmed path to the opened path and raises `StoreNotSpecified`
on mismatch, so one call cannot clear a different store.
Inference runs in a child process only for the duration of the call, with a
`timeout_seconds` wall-clock budget; no service, scheduler, telemetry, or
network call is started by the package (`laya-offline.json` keeps
`allow_download:false`, and step 14/15 prove it names the blocker rather than
downloading).

### 7. README install commands real; model card, notices, inventory, SHA256SUMS, acceptance report present — Pass `R` `D`

`README.md` install and use commands are the ones actually run above. The
`cognitive-runtime` console script was exercised natively in a real venv (every
row of the item-1 table), and `--config` is a top-level flag that must precede
the subcommand — the README shows that order. `MODEL_CARD.md`,
`THIRD_PARTY_NOTICES.md`, `SOURCE-INVENTORY.md`, `requirements-lock.txt`,
`RELEASE-MANIFEST.json`, `SHA256SUMS`, `CHANGELOG.md` and this report exist.
`LICENSE` now exists — the owner decided `Apache-2.0` on 2026-11-05; the file
is the verbatim Apache-2.0 text plus an applied copyright notice for this
package (11,978 B, SHA-256
`d55f3052cc51ef8bb0fb0161b55f98d93cb7542c1c6b19e1ebf5655a8c1408a1` `H`). It
covers this package's runtime code only and does not re-license the upstream
checkpoint. The `Private :: Do Not Upload` classifier that previously made an
accidental publish impossible has been removed (owner decision: publish thin
wheel + sdist to Hugging Face once the remaining gates close), so the remaining
prevention is procedural — see the release-gate section of `README.md`. Build
fact worth keeping: setuptools 80.10.2 rejects a configuration that pairs the
PEP 639 SPDX string `license = "Apache-2.0"` with a `License ::` classifier
(`InvalidConfigError`); the classifier was removed and
`build-system.requires` raised to `setuptools>=77`, and the build then
succeeded with `License-Expression` and `License-File` metadata as verified
above.

Defect found in the release file itself: `SHA256SUMS` carried 50 entries of
which 6 were `src/cognitive_runtime.egg-info/*` — generated build residue that
is not shipped and that nobody reproduces byte-for-byte, so anyone rebuilding
would see mismatches on files that never leave their machine. The set first
became 44 entries: 9 release documents + 33 `src`/`tests` files + 2 build
artifacts, and
the source-tree digest in `RELEASE-MANIFEST.json` excludes the same residue
(`d6aaa4aad1bf98bf80a19bb52adca2a7114803c395541c51c8bb678fb9c6e75e`, 33 files;
the earlier `209a1f16…` covered 39 including egg-info). The filter bug was
`"egg-info" not in p.parts`, which never matched because the path component is
`cognitive_runtime.egg-info` — a check that silently passes is worse than one
that fails, which is why the file set is now compared by name against the wheel
members rather than trusted to a glob. After `LICENSE` was added the set grew
to 45 entries: 10 release documents + 33 `src`/`tests` files + 2 build
artifacts, re-verified with zero mismatches.

## Test suite

28 tests, rc=0:

```bash
python -m pytest tests -q --basetemp=<tmp> -p no:cacheprovider   # 28 passed in ~3.0s, rc=0
```

Those two flags are an audit-machine workaround (`PermissionError [WinError 5]`
writing `pytest-of-<user>`); a plain `python -m pytest tests -q` was not
verified on another interpreter and is not claimed. What was verified this
round is weaker in a different direction and stronger in another: inside the
clean venv the same command with the same two flags gave `27 passed`, rc=0 (see the worker-fix section for the 28th test),
while importing `cognitive_runtime` from `site-packages` — i.e. the shipped
wheel, not the source tree, passes the suite.

Coverage: positive chain 7 (`test_chain.py`), negatives 13
(`test_negatives.py`, table above), process/CLI/out-of-the-box examples 7
(`test_process_and_cli.py`).

## Dependency lock reproduction

`requirements-lock.txt` is now the **full 44-package closure** of the
acceptance environment: the 23 names it carried before plus 21 transitive
packages that a fresh install also pulls (torch's `sympy`/`networkx`/`mpmath`/
`jinja2`, httpx's `anyio`/`h11`/`httpcore`/`certifi`/`idna`, huggingface_hub's
`rich`/`typer`/`shellingham`, pytest's `pluggy`/`iniconfig`, etc.), each read
from the installed distribution (`importlib.metadata.version`, rc=0, none
missing). Duplicate names: none.

- `uv pip install --python <fresh venv> --dry-run -r requirements-lock.txt`
  against a mirror index → `Resolved 44 packages`, `Would install 44 packages`,
  rc=0. The set is satisfiable together in a clean environment.
- `uv pip compile pyproject.toml --extra model --extra validate --extra dev`
  → resolves, but drifts upward because pyproject pins only
  laya/huggingface_hub/jsonschema: `torch 2.15.0`, `transformers 5.22.1`,
  `numpy 2.4.6`, `pytest 9.2.0`, `typing-extensions 4.16.0`. Recorded so nobody
  mistakes a pyproject-only install for the accepted environment.
- **Not claimed**: `--dry-run` fetches metadata, not wheels, so this is not a
  byte-level reproduction of the environment, and no package hashes are pinned.
  A full `pip install -r requirements-lock.txt` (~30 wheels to download, torch
  alone is large) was deliberately not run inside the session.

## Regressions and open items

1. ~~Real model call (item 2)~~ — **closed 2026-11-05**: ran offline on CPU
   against the pinned local snapshot; see item 2. The ~1.47 GiB encoder
   weights the owner downloaded turned out to be unused at inference
   (`laya 0.3.20` loads all parameters from the checkpoint); they stay
   recorded in `SOURCE-INVENTORY.md` §1 with measured hashes. The dependency
   lock must still be re-measured on a machine that installs the model extra
   from scratch — this environment already had `laya`/`torch`/`transformers`.
2. Owner decisions carried from `SOURCE-INVENTORY.md`: the code license
   (`Apache-2.0`), the package form (thin, no weights) and the channel
   (Hugging Face) are **decided** (2026-11-05). Still open: the destination
   account/repo id and whether `55cf4c4e…` is the approved publication
   revision.
3. ~~Console-script and `python -m` paths were verified through a bootstrap
   wrapper~~ — closed this round: both run natively in a real venv created with
   `uv venv` (item 1 table, `python -m cognitive_runtime doctor` rc=0). Still
   unverified on a *standard* system Python outside this machine.
4. Known semantic limit recorded in `README.md`: a memory hit short-circuits
   acquisition, so a newly conflicting receipt is not consulted until the
   store changes — conflict detection is proven on a fresh store, not on a
   cache hit.
5. `requirements-lock.txt` is the measured 44-package closure and resolves
   satisfiable in a clean venv (metadata-level, rc=0), but wheels were not
   re-downloaded and no per-package hashes are pinned. A byte-level clean
   install is still open, and the lock must be re-measured when the real-model
   smoke runs.

## Re-verification after the bilingual README (2026-11-05, same day)

The owner asked for a bilingual README (Hugging Face has no language tabs; the
card carries the English text followed by a full Chinese translation, which
ships in both artifacts because `README.md` feeds the wheel METADATA and the
sdist). Because README bytes are inside both artifacts, the build identity
changed and the whole acceptance chain was re-run against the new build
(harness script `reverify_bilingual_r7.sh`, log kept outside the repo):

- new artifact hashes (supersede `d2958445…` / `268fdb67…`, which are recorded
  only in the harness log, never in a release document):
  wheel `ed9940feab46…` 46,337 B · sdist `64f4f2c603…` 50,990 B;
- venv11 reinstalled from the new wheel: 28 tests pass (rc=0); 15-step
  transcript re-run clean; real-model smoke re-run **offline from the
  installed wheel** (`answered`, `provider_class=real`,
  `authorization=verified_judgment`; replay `answered`; inspect rc=0) and once
  from the source tree on the audit interpreter (`answered/real`, rc=0);
  venv12 (sdist install) mock infer rc=0;
- `SHA256SUMS` regenerated (45 entries: 10 documents, 33 src/tests, 2
  artifacts) and `check_release_integrity.py` reports zero mismatches;
- `source_tree_sha256` in `RELEASE-MANIFEST.json` is unchanged (`452b2c23…`)
  because its scope is the 33 src/tests files; README is a release document.

No code file changed in this round; all seven acceptance items above were
re-measured, not assumed.

## Pre-upload rebuild for the publication wording (2026-11-05)

The owner approved the publication revision `55cf4c4e…` and named the
destination (`WayneRR/cognitive-learning-lab`). README status rows were
re-worded so they remain true across the upload boundary (the publication
record is delegated to `RELEASE-CHECKLIST.md` / `RELEASE-MANIFEST.json`,
because README bytes are frozen into the wheel METADATA). Artifacts were
rebuilt a third time and the chain re-run: 28 tests pass, transcript clean,
real-model smoke `answered/real/verified_judgment` from the installed wheel
and the source tree, sdist mock infer rc=0, SHA256SUMS regenerated with zero
integrity mismatches. Build identity for the upload: wheel `803ee8248669…`
46,414 B · sdist `37375e949ab8…` 51,157 B (the two earlier same-day
identities are superseded and live only in the harness logs).

## Upload and post-download verification (2026-11-05)

Published to `https://huggingface.co/WayneRR/cognitive-learning-lab` as a
public model repo, single `upload_folder` commit `4225068d5f589f1bea…`
(14 files: the 10 hash-surface documents, `RELEASE-MANIFEST.json`,
`SHA256SUMS`, wheel, sdist). Upload ran directly against huggingface.co with
the owner's write token; no token is stored in any file.

Post-download verification (the checklist's final item):

- the wheel and sdist were re-downloaded **from the published repo** —
  via hf-mirror, because the file CDN behind huggingface.co times out on
  this network (the API does not); hashes are endpoint-independent. Both
  match the uploaded build exactly: wheel `803ee8248669…`,
  sdist `37375e949ab8…`.
- a fresh `uv venv` (cr-m1-venv13) installed the **downloaded-back** wheel:
  `doctor` rc=0, `infer` rc=0 `answered`/`provider_class=mock`/
  `authorization=verified_judgment`, and a second process replayed the store
  rc=0 with memory reuse.

This closes the publication loop; package state is recorded as
`LOCAL_ACCEPTED_REAL_MODEL_SMOKE / PUBLISHED` in `RELEASE-CHECKLIST.md` and
`RELEASE-MANIFEST.json`. The documents recording the upload were re-uploaded
to the repo afterwards, so the remote carries the same receipts.

## Model-card fix-up rebuild (2026-11-05, post-publication review)

An external review of the published card found the status badge still said
`_NOT_UPLOADED` and the card lacked YAML frontmatter. Both fixed in
`README.md` (badge de-updated in EN and zh; frontmatter declares
`license: apache-2.0`, `language: [en, zh]`, truthful tags). README bytes
are inside both artifacts, so they were rebuilt — fourth same-day identity:
wheel `64e02c1ab360…` 46,448 B, sdist `d69ad3ce98d3…` 51,237 B — and the
chain re-run: 28 tests pass, transcript clean, real-model smoke
`answered/real/verified_judgment` from the installed wheel and the source
tree, sdist mock infer rc=0, SHA256SUMS regenerated with zero integrity
mismatches. The rebuilt artifacts replace `803ee824…` / `37375e94…` in the
published repo; the download-back verification was repeated against the new
build (receipt in `RELEASE-CHECKLIST.md` / `RELEASE-MANIFEST.json`).

### Download-back receipt for the fix-up build

The rebuilt artifacts (wheel `64e02c1a…`, sdist `d69ad3ce…`, upload commit
`5ccf3666…`) were re-downloaded from the published repo via hf-mirror and
hash-match byte-for-byte; a fresh uv venv (cr-m1-venv14) installed the
downloaded-back wheel: `doctor` rc=0, `infer` rc=0
`answered`/`provider_class=mock`/`verified_judgment`, second-process replay
rc=0 with memory reuse. The first uploaded build's receipt (commit
`4225068d`, wheel `803ee824…`) remains valid as history; the remote now
serves the fix-up build.

### GitHub source-repository export (owner-confirmed, 2026-11-05)

A clean public source repository was published with entirely fresh git
history — the workspace branch was **not** pushed anywhere. Destination
`https://github.com/kialajin-l/cognitive-learning-lab` (org `kialajin-l`,
created via `gh` and pushed through the local proxy, which GitHub writes
require).

Pre-upload gates: a secret/credential scan and a machine-path scan over the
whole export set gave **zero real hits** (the only pattern matches were the
`s:/` substring inside `https://` URLs). The 13-item confirmed export
(`src/`, `tests/`, `pyproject.toml`, `LICENSE`, `README.md`, `MODEL_CARD.md`,
`THIRD_PARTY_NOTICES.md`, `requirements-lock.txt`, `acceptance/PR-M1.md`,
`PAPER-ARTIFACT-NOTE.md`, `CHANGELOG.md`, `RELEASE-MANIFEST.json`,
`SHA256SUMS`) was byte-diffed against the source tree before committing —
all identical; no `__pycache__`/`egg-info` copied. Wheel, sdist and
`SHA256SUMS` are **Release v0.1.0 attachments, not git blobs**.

One gap was found in post-clone verification and closed by owner decision:
`SOURCE-INVENTORY.md` was absent from the confirmed list while being hashed
by `SHA256SUMS` and referenced by six shipped documents (13 references) —
and already public on the Hugging Face repo. It was added as commit
`d6dc1b4…`.

Post-upload verification, all measured:

- fresh clone (`core.autocrlf=input`): **43/43** non-`dist` `SHA256SUMS`
  entries match; the two `dist/` entries are the Release attachments;
- Release assets re-downloaded: wheel `64e02c1a…` 46,448 B and sdist
  `d69ad3ce…` 51,237 B hash-match the built `dist/` byte-for-byte, and the
  `SHA256SUMS` asset is identical to the repository copy;
- fresh uv venv installed the **Release-downloaded** wheel: `doctor` rc=0
  `blockers:[]`, `infer` rc=0 `answered`/`mock`/`verified_judgment`, a second
  independent process rc=0 with `acquisition_calls=0` (memory replayed),
  and the 28-test suite run from the cloned `tests/` against the installed
  wheel: **28 passed**.

### ModelScope mirror (owner-approved, same day)

Channel matrix note: ModelScope is domestic and runs **direct, no proxy**; the
token (`ms-…`, short-lived, write role) validated via the SDK's `whoami`
(account `kialajin`).

- Repo created public: `https://modelscope.cn/models/kialajin/cognitive-learning-lab`.
- Upload: 14 files **byte-identical** to the HF repo at HEAD `d0756e93…`
  (10 hash-surface docs incl. `acceptance/PR-M1.md`, manifest, SHA256SUMS,
  `pyproject.toml`, `requirements-lock.txt`, wheel, sdist) — upload commit
  `d0aaacbffe…`, 14 committed / 0 failed, wheel stored via LFS.
- Download-back (`snapshot_download@master`): every `SHA256SUMS` entry whose
  path exists in the flat remote layout matches byte-for-byte (10/10);
  wheel/sdist hashes match the current build directly
  (`64e02c1a…` / `d69ad3ce…`). The 35 "missing" entries are the flat-`src/` /
  `dist/` layout difference of `SHA256SUMS`, the same structural note as on
  HF, not a defect — artifact integrity is verified through the artifacts
  themselves.
- README's YAML frontmatter (HF card format) is shipped unchanged to keep the
  two channels byte-identical; ModelScope tolerates it. Model channel
  status: HF primary, ModelScope mirror; no weights on either.
