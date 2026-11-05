# Changelog

## v0.1.0 — PR-M1 (2026-11-05, local only)

First implementation of the public runtime candidate. Nothing in this
release is uploaded, and every accepted result below was produced with
`provider_class="mock"`.

### Added

- `cognitive_runtime` package (src layout, Python 3.10+, no hard runtime
  dependencies) with a `cognitive-runtime` console script and `python -m`
  entry point; stable schema ids `cognitive-runtime/decision-input/v1` and
  `cognitive-runtime/decision-output/v1`.
- Fail-closed chain: input sanitizer → store integrity check → retrieval →
  optional receipt acquisition → verification/promotion → model proposal →
  rule judgment → three-layer boundary → controlled writeback.
- SQLite memory store with per-record schema version, namespace, content
  hash, source, capture time, verification type/version/status, promotion
  state and related ids. Writes always land as `candidate/unverified`;
  `promote()` refuses unless verification passed and the hash still matches.
  Tampering found by `integrity_check()` quarantines the record before
  anything can be authorised from it.
- Two verification types, `source-consistency-v1` (record vs. the receipt it
  cites) and `lineage-consistency-v1` (a written-back conclusion vs. its
  promoted parents). Both report provenance consistency only.
- Deterministic `entity-token-v1` retriever — new code; the audit found no
  importable retriever in the private repository.
- Providers: `MockProvider` (offline, always labelled `mock`) and
  `LayaProvider` (pinned `convaiinnovations/laya@55cf4c4e…`, SHA-256
  integrity gate on `model.safetensors`, subprocess inference with a
  wall-clock timeout, `local_dir` supported for offline copies).
- CLI: `doctor`, `infer`, `memory seed|verify|inspect|show|clear`. Store
  paths are never guessed; `clear` refuses without `--yes` naming the same
  store. Exit codes 0 / 2 / 3.
- Synthetic examples (`defaults/examples/`) and 28 tests covering the
  positive chain, the negatives required by PR-M1, subprocess reuse and
  out-of-the-box behaviour of the shipped examples.
- Release documents: `SOURCE-INVENTORY.md`, `MODEL_CARD.md`,
  `THIRD_PARTY_NOTICES.md`, `requirements-lock.txt`,
  `RELEASE-MANIFEST.json`, `SHA256SUMS`, `acceptance/PR-M1.md`,
  `PAPER-ARTIFACT-NOTE.md`.

### Changed relative to the planning documents

- Default config and examples moved inside the package
  (`src/cognitive_runtime/defaults/`), because the acceptance run of the
  separated `configs/` + `examples/` layout produced a wheel whose
  `SourceRegistry` was empty and which silently abstained. `ARTIFACT-SPEC`
  updated to match.
- No cryptographic trust root ships. The archived Ed25519 gate in the
  private repository derives its private key from a string that says it is a
  test fixture, so verification here is hash + provenance + lineage.
- A provider that produces no usable proposal (`schema_failure`, `timeout`,
  `runtime_error`) is reported as **not-run** with exit code 3 instead of an
  `answered` envelope; a model that declines (`abstain`) still flows through
  the chain normally.
- `proposal_agrees_with_judgment` compares candidate *text* on both sides;
  it previously compared the provider's `candidate_id` against the
  judgment's text, which kept the flag permanently `false`.

### Verification hardening (same day, no code change)

- Acceptance was re-run in **real venvs** (`uv venv` from the audit
  interpreter), which replaced the `pip install --target` + bootstrap
  workaround. The console script, `python -m`, the wheel install, the sdist
  install and the 27-test suite against the *installed* package were all
  exercised outside the repository with normal interpreter flags.
- `requirements-lock.txt` grew from 23 measured pins to the full 44-package
  transitive closure of the acceptance environment, and was checked to resolve
  satisfiable as a set in a fresh venv. Resolving from `pyproject.toml` alone
  drifts upward (`torch 2.15.0`, `transformers 5.22.1`), which is now written
  down instead of being silently assumed.
- `SHA256SUMS` corrected from 50 entries to 44: six of the old entries were
  `src/cognitive_runtime.egg-info/*`, generated build residue that is not
  shipped and that a rebuild cannot reproduce, so the checksum file was
  unverifiable on any other machine. The source-tree digest changed with it.
- Wheel and sdist were **rebuilt** after the README and lock edits (the wheel
  `METADATA` embeds the README), giving `aa1c122a…` / `0449fe36…`; both were
  re-installed into fresh venvs and re-run before their hashes were recorded.
  Those two hashes were in turn superseded by the licence rebuild below.
- `THIRD_PARTY_NOTICES.md` now lists all 44 packages with the license each one
  declares in its own metadata. This corrected an earlier line that called
  `torch` "BSD-3-Clause": its metadata declares a six-term expression
  (Apache-2.0 + LLVM-exception + BSD-2 + BSD-3 + BSL-1.0 + MIT).

### Publication decisions recorded (same day)

- The owner decided the runtime code licence: `Apache-2.0`. `LICENSE` is the
  verbatim Apache-2.0 text with an applied copyright notice for this package,
  and `pyproject.toml` now carries `license = "Apache-2.0"` plus
  `license-files = ["LICENSE"]`. The `Private :: Do Not Upload` classifier is
  gone, so an accidental publish is no longer blocked by build metadata —
  `README.md` states the two gates that remain.
- The published package form is **thin**: wheel + sdist, no bundled weights.
  The model checkpoint and its encoder stay separate, hash-pinned downloads.
  The Apache-2.0 licence covers the code only and does not re-license them.
- Destination is Hugging Face, with an account the owner supplies; the account
  and repository id are still unknown, so nothing was uploaded.
- Build defect found and fixed: setuptools 80.10.2 refuses a config that has
  both the SPDX `license = "Apache-2.0"` expression and a `License ::`
  classifier (`InvalidConfigError`, PEP 639). The classifier was removed and
  `build-system.requires` raised to `setuptools>=77`, which is the first
  version that accepts a bare SPDX string.
- Wheel and sdist were rebuilt again for the licence and README edits, giving
  `0c700b2f…` (wheel, 42,118 B) / `f46de08c…` (sdist, 41,209 B); both were
  re-installed into fresh venvs (wheel and sdist separately) and re-run — the
  8-step transcript and the 27-test suite against the installed package —
  before any hash was written down.

### Real-model smoke (same day, item 2 closed)

- The owner downloaded the five `answerdotai/ModernBERT-large@45bb4654…` files
  independently; all sizes match the recorded baselines and `model.safetensors`
  hashes to the pinned `44510fec…` exactly.
- Measured correction found on the first real run: `laya 0.3.20` builds the
  network untrained and loads **every parameter — encoder included — from the
  Laya checkpoint**; only the snapshot's `encoder/config.json` is read. The
  1.58 GB encoder weights are **not needed at inference**, so the earlier
  "blocked on a second ~1.47 GiB download" record was a documented assumption,
  now corrected everywhere it appeared.
- The real `infer` ran fully offline (`HF_HUB_OFFLINE=1`,
  `TRANSFORMERS_OFFLINE=1`, CPU) against a copy of the pinned local snapshot
  (`model.local_dir`, `allow_download:false`; the copy was re-hashed first
  because `laya.load` may rewrite `tokenizer/tokenizer_config.json` in place,
  and the shared hub cache must stay untouched): rc=0, `answered`/`team-north`,
  `provider_class=real`, `prompt_tokens=117`,
  `calibration_status=uncalibrated` (the temperature warning really fired),
  `authorization=verified_judgment`, writeback promoted; a second independent
  process reused the memory with `acquisition_calls=0`. Acceptance status is
  now `LOCAL_ACCEPTED_REAL_MODEL_SMOKE` — 7 of 7 items Pass.
- The smoke is one receipt on one synthetic example on one machine; no
  accuracy claim is derived from it.
- **Defect found and fixed while re-running the smoke from a normally
  installed wheel:** the worker was launched as a script file, putting
  `cognitive_runtime/model/` at the child's `sys.path[0]` where the package's
  own `laya.py` shadowed the third-party `laya` package — the packaged wheel
  could not run the real provider in any normal environment. Earlier runs
  passed only because the embedded audit interpreter ignores the script
  directory. The worker is now imported as a package submodule via a `-c`
  bootstrap (`laya.py::_worker_command`), a regression test pins the
  invocation shape (suite 27 → 28), and the real smoke passes from both the
  installed wheel and the source tree.

### Bilingual README (same day, no code change)

- The owner chose the destination repository id (`cognitive-learning-lab`)
  and asked for a bilingual README. Hugging Face model cards are a single
  Markdown file with no language tabs, so `README.md` now carries the English
  text followed by a full Chinese translation of every section, with a
  language navigation at the top.
- Because `README.md` is embedded in the wheel METADATA (CRLF-normalised) and
  shipped in the sdist, both artifacts were rebuilt and the whole acceptance
  chain re-run against the new build: venv11 reinstall + 28 tests (rc=0),
  15-step transcript clean, real-model smoke re-run offline from the installed
  wheel (`answered`, `provider_class=real`, `authorization=verified_judgment`;
  replay `answered`; inspect rc=0) and from the source tree (rc=0), venv12
  sdist mock infer rc=0. Receipts in `acceptance/PR-M1.md` §"Re-verification
  after the bilingual README".
- New build identity: wheel `ed9940feab46…` 46,337 B, sdist `64f4f2c603…`
  50,990 B (superseding `d2958445…` / `268fdb67…`, which stay recorded only in
  the harness log). `SHA256SUMS` regenerated, integrity check zero mismatches.
  The release documents' claim set is unchanged.

### Publication approved (same day)

- The owner approved revision `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851` as
  the publication revision and named the destination: Hugging Face account
  `WayneRR`, model repo **`WayneRR/cognitive-learning-lab`**. The write-role
  token was validated by a read-only `whoami`; root cause of the two earlier
  token rejections was the local proxy mangling HF authentication — HF API
  calls run with no proxy.
- README now words its status rows so they stay true across the upload
  boundary and defers the publication record to `RELEASE-CHECKLIST.md` /
  `RELEASE-MANIFEST.json` (`publication.status`), because README bytes are
  frozen into the wheel METADATA. Artifacts were rebuilt for this wording
  change and the acceptance chain re-run; `READY_TO_UPLOAD` conditions are
  all satisfied.

### Model-card fix-up (same day, post-publication review)

- A post-publication review found two model-card issues, both fixed: the
  status badge still carried `_NOT_UPLOADED` (an inconsistency with the
  `PUBLISHED` manifest — the release-gate paragraphs were already
  upload-safe, the badge was not), and the card had no YAML frontmatter
  (HF "empty or missing yaml metadata" warning). The badge now reads
  `PR_M1_IMPLEMENTED_LOCALLY_ACCEPTED_REAL_MODEL_SMOKE` (EN + zh), and the
  card frontmatter declares `license: apache-2.0`, `language: [en, zh]` and
  truthful tags. Note: the frontmatter bytes are part of the wheel METADATA
  description like the rest of the README — cosmetic, and standard for
  packages whose README is a HF card.
- Because README bytes live in both artifacts, they were rebuilt (fourth
  build identity: wheel `64e02c1a…` 46,448 B, sdist `d69ad3ce…` 51,237 B,
  superseding `803ee824…` / `37375e94…` and the two earlier same-day
  identities, which stay only in the harness logs) and the full chain
  re-run: 28 tests, transcript, offline real-model smoke from the installed
  wheel and the source tree, sdist mock infer — all pass; SHA256SUMS
  regenerated, integrity zero mismatches. The rebuilt artifacts were
  uploaded to the published repo and the download-back verification repeated
  (see `RELEASE-CHECKLIST.md`).

### Published (same day)

- v0.1.0 was uploaded to
  [`WayneRR/cognitive-learning-lab`](https://huggingface.co/WayneRR/cognitive-learning-lab)
  as a single commit `4225068d…` (14 files: 10 hash-surface documents,
  manifest, SHA256SUMS, wheel, sdist). Nothing but the thin package went up —
  no weights, no private paths, no experiment data.
- Post-download verification passed: wheel and sdist re-downloaded from the
  published repo hash-match the uploaded build byte-for-byte, and a fresh
  venv smoke of the downloaded-back wheel runs the full chain
  (`answered`/`verified_judgment`, replay reuse).
- Package state: `LOCAL_ACCEPTED_REAL_MODEL_SMOKE / PUBLISHED`.
  PR-M2/v0.2.0 is next and has not been started.

### Not done

- (2026-11-05, superseded the same day) the two items that used to be listed
  here — an un-uploaded build and an unapproved revision — were both closed:
  the owner approved the revision and the package was published; see
  "Published" above. Still genuinely open: the byte-level clean install of
  `requirements-lock.txt` (conditional, unchanged) and all of PR-M2/PR-M3.

### GitHub source repository published (same day, owner-confirmed)

- A clean public source repo was created at
  [`kialajin-l/cognitive-learning-lab`](https://github.com/kialajin-l/cognitive-learning-lab)
  with **entirely fresh git history** — initial commit `34231b87…` (44 files,
  the confirmed export set); the workspace branch was never pushed.
- Before the first public commit: secret/machine-path scans over the export
  set (zero real hits), staging byte-diffed against the source tree, and
  `PAPER-ARTIFACT-NOTE.md` corrected (`Public URL: pending` → the published
  HF URL; superseded hashes `0c700b2f…`/`f46de08c…` → current
  `64e02c1a…`/`d69ad3ce…`; the same relabelling applied in
  `acceptance/PR-M1.md`).
- **Release v0.1.0** carries the wheel (`64e02c1a…`), the sdist
  (`d69ad3ce…`) and `SHA256SUMS` as attachments — artifacts are not in the
  git history.
- Post-clone verification found `SOURCE-INVENTORY.md` absent from the
  confirmed list while hashed by `SHA256SUMS` and referenced by six shipped
  documents; owner decision: add it (already public on HF) — commit
  `d6dc1b4…`.
- Post-upload verification, measured: fresh clone verifies 43/43 non-`dist`
  SHA256SUMS entries; Release assets re-downloaded hash-match the built
  `dist/` byte-for-byte; a fresh venv installed the Release-downloaded wheel
  (`doctor` rc=0, `infer` rc=0 `answered`/`verified_judgment`, second process
  `acquisition_calls=0`) and the 28-test suite from the cloned `tests/`
  passes against that install.
- The model-package channel remains Hugging Face; no weights on GitHub.

### ModelScope mirror (same day, owner-approved)

- Public mirror repo created at
  [`kialajin/cognitive-learning-lab`](https://modelscope.cn/models/kialajin/cognitive-learning-lab)
  (token validated via SDK `whoami`, account `kialajin`).
- 14 files uploaded **byte-identical** to the HF repo (thin package, no
  weights, wheel via LFS) — commit `d0aaacbffe…`.
- Download-back verification: 10/10 flat-layout doc entries match
  byte-for-byte; wheel/sdist hashes match the current build
  (`64e02c1a…`/`d69ad3ce…`). The unmatched `SHA256SUMS` lines are the flat
  working-tree layout, not missing content.
- Channels: Hugging Face primary, ModelScope mirror, GitHub source copy;
  all three carry the same artifact identity.
