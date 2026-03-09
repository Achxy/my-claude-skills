# Hypersaint CI Integrity Verification

## Table of Contents

1. [Overview](#overview)
2. [What CI Checks](#what-ci-checks)
3. [Failure Modes](#failure-modes)
4. [Integration with GitHub Actions](#integration-with-github-actions)
5. [Local Verification](#local-verification)

---

## Overview

The Hypersaint CI integrity pipeline ensures that the manifest system (README.md + index.toml) is
always in sync with the actual files. It runs on every push and pull request. Any mismatch is a
hard failure — the change cannot be merged until manifests are updated.

This is the enforcement mechanism for the rule: "Updating manifests is part of every change."

---

## What CI Checks

The integrity check walks the entire repository tree and performs these verifications at every
directory that contains an `index.toml`:

### 1. index.toml Hash Accuracy

For every entry in `[integrity]`:
- Recompute the SHA-256 hash of the referenced file or directory.
- Compare against the declared hash.
- **FAIL** if any hash mismatches.

### 2. index.toml Completeness

- List all files and directories in the same directory as `index.toml` (excluding `index.toml`
  itself, `.git`, `__pycache__`, `node_modules`, and other standard ignores).
- **FAIL** if any file/directory exists but has no entry in `[integrity]`.
- **FAIL** if any entry in `[integrity]` references a nonexistent file/directory.

### 3. README.md Hash Accuracy

- Parse the `<!-- @hs:integrity -->` block from README.md.
- Recompute the SHA-256 hash of every referenced file (excluding README.md itself).
- Compare against the declared hashes.
- **FAIL** if any hash mismatches.

### 4. README.md Completeness

- Same completeness check as index.toml but for the README integrity block.
- **FAIL** on missing or extra entries.

### 5. Cross-Validation

- The hash of `index.toml` as declared in README.md's integrity block must match the actual
  `index.toml` file.
- The hash of `README.md` as declared in index.toml's `[integrity]` table must match the actual
  `README.md` file.
- **FAIL** if either cross-reference is stale.

### 6. Circular Dependency Symmetry

- For every `[circular]` entry in every `index.toml`, verify that the referenced atom also
  declares the reverse circular dependency.
- **FAIL** on asymmetric circular declarations.

### 7. Structural Completeness

- Every directory in the repository (except root-level config dirs like `.git`, `.github`,
  `node_modules`, `__pycache__`, `.mypy_cache`, `.ruff_cache`) must contain both `README.md`
  and `index.toml`.
- **FAIL** if any directory is missing either file.

---

## Failure Modes

Each failure produces a machine-readable error message that the LLM agent can parse and act on.

| Error Code | Message Format | Agent Action |
|------------|---------------|--------------|
| `HASH_MISMATCH` | `HASH_MISMATCH: {path} declared={declared} actual={actual}` | Recompute and update the manifest |
| `MISSING_ENTRY` | `MISSING_ENTRY: {path} not in {manifest_file}` | Add the missing entry to the manifest |
| `EXTRA_ENTRY` | `EXTRA_ENTRY: {path} in {manifest_file} but file does not exist` | Remove the stale entry |
| `CROSS_VALIDATION` | `CROSS_VALIDATION: {file_a} hash of {file_b} is stale` | Update both manifests |
| `CIRCULAR_ASYMMETRIC` | `CIRCULAR_ASYMMETRIC: {atom_a} declares circular with {atom_b} but not vice versa` | Add declaration to the other atom |
| `MISSING_MANIFEST` | `MISSING_MANIFEST: {dir} missing {README.md|index.toml}` | Create the missing manifest |

The error output is one error per line, parseable by the agent. The agent can loop: read errors →
fix → re-run check → repeat until clean.

---

## Integration with GitHub Actions

Use `assets/ci.yml` as the workflow template. The workflow:

1. Checks out the repository.
2. Sets up Python (the integrity check scripts are Python).
3. Runs `scripts/verify_integrity.py` on the entire repo.
4. Fails the job if any errors are reported.

The workflow runs on:
- Every push to any branch.
- Every pull request targeting any branch.

It is a **required status check** for merge — PRs cannot merge without passing integrity.

---

## Local Verification

Developers (human or LLM) can run the integrity check locally before pushing:

```bash
python scripts/verify_integrity.py .
```

This produces the same error output as CI. The agent should run this after every change as part
of its feedback loop (step 5 in the Agent Navigation Model described in the Modularity reference).

For updating manifests automatically after changes:

```bash
# Update index.toml for a specific directory
python scripts/index_toml_generator.py path/to/atom/

# Update READMEs for all directories affected by a set of changed files
python scripts/readme_hooks.py . --changed path/to/changed_file.py path/to/other_file.py
```
