# Third-party notices

## Upstream model

`convaiinnovations/laya`, revision `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`.
License recorded by the Hugging Face model card metadata: `apache-2.0`.
`model.safetensors` is 842,609,210 bytes with SHA-256
`891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c`, verified
byte-identical against the upstream LFS object in PR-M1.

The runtime does not redistribute these weights. It downloads the pinned
revision on demand, or accepts a `model.local_dir` path, and refuses to run if
the hash does not match.

## Encoder dependency pulled in by the model

`rl_agent_config.json` names `answerdotai/ModernBERT-large` (revision
`45bb4654a4d5aaff24dd11d4781fa46d39bf8c13`, license `apache-2.0`). The Laya
snapshot ships only `encoder/config.json`. Measured 2026-11-05: at inference
`laya 0.3.20` loads every parameter, encoder included, from the Laya
checkpoint itself (`pretrained=False`), so the ~1.58 GB ModernBERT weights are
**not required to run** this package; they were nonetheless downloaded and
hash-verified independently during PR-M1 (`model.safetensors` sha256
`44510fec…` = upstream LFS oid). If a future `laya` version returns to
`pretrained=True`, that second download becomes a real installation cost
again.

## Python packages

The table covers the **full 44-package closure** of `requirements-lock.txt`.
Every row was read from the installed distribution on the acceptance machine
(`importlib.metadata`, 2026-11-05): the version is what was actually used, and
the license column is the package's own `License-Expression`, falling back to
its `License` field. `<not declared>` means the metadata carries neither, so the
upstream `LICENSE` file still has to be checked before redistribution — those
rows are listed for completeness and are **not** counted as verified.

| Package | Version | License recorded by the package |
|---|---|---|
| `laya` | 0.3.20 | Apache-2.0 |
| `huggingface_hub` | 1.33.0 | Apache-2.0 |
| `torch` | 2.14.0 | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT |
| `transformers` | 5.17.0 | Apache 2.0 License |
| `safetensors` | 0.8.0 | `<not declared>` |
| `numpy` | 2.4.1 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| `tokenizers` | 0.23.2 | `<not declared>` |
| `regex` | 2026.9.10 | Apache-2.0 AND CNRI-Python |
| `click` | 8.5.0 | BSD-3-Clause |
| `filelock` | 4.0.3 | MIT |
| `fsspec` | 2026.9.0 | BSD-3-Clause |
| `hf-xet` | 1.6.0 | Apache-2.0 |
| `httpx` | 0.28.1 | BSD-3-Clause |
| `httpcore` | 1.0.9 | BSD-3-Clause |
| `h11` | 0.16.0 | MIT |
| `anyio` | 4.12.1 | MIT |
| `idna` | 3.20 | BSD-3-Clause |
| `certifi` | 2026.1.4 | MPL-2.0 |
| `packaging` | 26.0 | Apache-2.0 OR BSD-2-Clause |
| `pyyaml` | 6.0.3 | MIT |
| `tqdm` | 4.67.1 | MPL-2.0 AND MIT |
| `typing-extensions` | 4.15.0 | PSF-2.0 |
| `mpmath` | 1.3.0 | BSD |
| `sympy` | 1.14.0 | BSD |
| `networkx` | 3.6.1 | BSD-3-Clause |
| `jinja2` | 3.1.6 | `<not declared>` |
| `markupsafe` | 3.0.3 | BSD-3-Clause |
| `setuptools` | 80.10.2 | MIT |
| `rich` | 14.3.1 | MIT |
| `markdown-it-py` | 4.0.0 | `<not declared>` |
| `mdurl` | 0.1.2 | `<not declared>` |
| `pygments` | 2.19.2 | BSD-2-Clause |
| `shellingham` | 1.5.4 | ISC License |
| `typer` | 0.21.1 | MIT |
| `annotated-doc` | 0.0.4 | MIT |
| `colorama` | 0.4.6 | `<not declared>` |
| `jsonschema` | 4.26.0 | MIT |
| `attrs` | 25.4.0 | MIT |
| `referencing` | 0.36.2 | MIT |
| `rpds-py` | 0.30.0 | MIT |
| `jsonschema-specifications` | 2025.9.1 | MIT |
| `pytest` | 9.1.1 | MIT |
| `iniconfig` | 2.3.0 | MIT |
| `pluggy` | 1.6.0 | MIT |

Earlier revisions of this file recorded `torch` as "BSD-3-Clause (not
re-verified)"; that was wrong in a way that matters — the shipped wheel declares
a six-term expression, so any redistribution notice has to cover all of it, not
one clause.

The published artifact is a **thin** wheel and sdist: it declares no hard
runtime dependency and vendors none of the above. `pip install .` therefore
copies no third-party code, and these rows only matter if the `model` /
`validate` extras are installed, or if weights plus a full environment are ever
bundled. Copyleft-ish terms worth watching in that case: `certifi` and `tqdm`
carry MPL-2.0, `typing-extensions` PSF-2.0, `regex` adds CNRI-Python, and
`torch` mixes Apache-2.0 with several BSD clauses and BSL-1.0.

## Code deliberately not reused

An external working copy of the `AnchorJudge` project (kept outside this
repository; its path is deliberately not recorded in this public file) declares
`license = { text = "Apache-2.0" }` in its
`pyproject.toml` but ships no LICENSE, COPYING or NOTICE file, and four of its
source files were uncommitted at audit time. There is no auditable,
redistributable baseline, so this package reimplements the behaviour it
describes rather than importing or copying it.

The archived experiment runners in this repository are referenced for semantics
only. Their file paths, SHA-256 values and git tracking state are recorded in
`SOURCE-INVENTORY.md`.
