# PRDBench integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Bring upstream PRDBench updates into the LM Studio branch, with auditable automatic tag cleanup and PRD selection, without starting experiments.

**Architecture:** Preserve existing experiments and recovery fixes, merge upstream in an isolated worktree, and keep the current repair/evaluation architecture. Add one pure response-normalization module and provider-specific cache dispatch; use the existing batch identity for PRD selection.

**Tech Stack:** Python, pytest, Git worktrees, existing LM Studio SDK fixture and local HTTP test server.

**Spec:** `docs/superpowers/specs/2026-11-27-prdbench-sync-design.md`

## Global Constraints

- Model profiles, per-project reload and 0–30 repairs stay unchanged; no live inference, model loads, experiment start, or remote push.
- Default `--prd vanilla`; selectable `unambiguous_defect`, `complete_defect`, `consistent_defect`.
- Raw responses and old experiment outputs are immutable. Cleanup is limited to documented tags/reopened same-path blocks and records its changes before evaluation.
- Benchmark updates are versioned separately from existing results; preserve a pre-merge benchmark and runner archive.

## Review Focus

- Literal tags in Python strings or non-Python data must not be changed (Task 2).
- Malformed nested blocks must not hide unsafe paths, deletes or protected input writes (Task 2).
- A cleaned but rejected response must not inherit a new score or overwrite current code (Task 2).
- Anthropic cache directives must not reach LM Studio, including modeling (Task 1).
- Missing/invalid defect PRDs must fail before model work and must never silently use vanilla (Task 3).

### Task 1: Integrate upstream and preserve provider behavior

**Files:** `generate/config.py`, `generate/generate.py`, `generate/llm.py`, `generate/repair.py`, upstream benchmark/docs; `tests/test_claude_cache.py`.

**Interfaces:** Add `request_completion(llm, prompt, *, cache=True)` routing cache controls only to Claude; retain the `(text, usage)` contract. Existing caller identities choose direct/modeling cache behavior.

- [x] Preserve output hashes, previous benchmark/runner and current recovery edits; verify the baseline suite and create an isolated worktree.
- [x] Write failing tests for real Claude payload caching on direct/modeling stages; retain real generator/evaluator with only SDK boundary doubled. Run targeted pytest and observe failures.
- [x] Merge all upstream commits, keeping the managed generation loop. Resolve README and generator conflicts; apply cache controls through the provider-aware helper.
- [x] Run provider/generation tests and full pytest; commit the integrated upstream merge.

### Task 2: Automatically normalize documented tags with provenance

**Files:** create `generate/tag_cleanup.py`, `tests/test_tag_cleanup.py`; modify `generate/repair.py`, `generate/session.py`, and related docs.

**Interfaces:** `normalize_response(response: str) -> tuple[str, dict]` returns normalized text and deterministic per-file audit metadata. The repair loop saves raw/cleaned artifacts and applies its existing parsing/protected-path/atomic-publication checks.

- [x] Write RED tests: literal expectations for standalone tag removal, same-path reopening, string/data preservation and rejected mixed/unsafe operations. Add real repair/evaluation tests for retained raw response, passing cleaned code, unchanged usage and budget, rejected cleanup preserving prior code.
- [x] Run targeted pytest and inspect expected failures.
- [x] Implement conservative normalization, per-round cleanup artifacts, and record policy metadata. Never execute response-suggested tools or alter logical program statements.
- [x] Run affected tests and full pytest; commit automatic cleanup.

### Task 3: Select PRD variants through the local batch

**Files:** `generate/run_batch.py`, `tests/test_batch.py`, `README.md`, `README_LMSTUDIO.md`, `eval/README.md`.

**Interfaces:** `--prd NAME` populates `plan['prd']`, child generation argv, manifest and existing trial identity/output directory. Default and model/project ordering remain unchanged.

- [x] Write RED real-entry tests selecting each defect variant with distinct PRD contents, checking saved identity and correct input; invalid/missing input must produce no SDK events or output batch. Existing default tests continue covering vanilla.
- [x] Run tests, then implement selection/preflight and document examples, cleanup evidence and old-result versioning.
- [x] Run full pytest and selected dry runs; commit.

### Task 4: Review and deliver on the requested branch

**Files:** final documentation and verification record; no experiment artifacts are edited.

- [x] Review the entire change with a fresh read-only reviewer per requesting-code-review. Fix material findings with reproducing tests.
- [x] Verify upstream is an ancestor, sampling/runtime profiles unchanged, all regression tests pass, no experiment running and all pre-existing output hashes match the archive manifest.
- [x] Fast-forward `feat/lmstudio-prdbench` to the verified integration branch and remove the clean temporary worktree. Leave original results and archive available; do not push or start experiments.

## Completion record (2026-11-27)

- Integrated upstream `df23b1c` and delivered verified implementation `810c576` to local `feat/lmstudio-prdbench` by fast-forward. Temporary worktree/branch removed.
- Regression progression: baseline 144; merge 148; cleanup 177; PRD selection 187; final fixes **194 passed in 102.31s**. The suite includes Node runtime contract checks and local HTTP/SDK fixtures; no real model inference.
- Fresh read-only review found two important edge cases. Reproducing tests failed before fixes, then passed: unreadable/empty PRDs are rejected before model loading; reopened file tags must occupy an entire physical line. No deferred minor findings.
- All four PRD variants passed real-checkout dry runs. Existing model profiles/runtime helpers remained byte-identical. Benchmark contents match upstream.
- All 4,212 pre-existing output files match their archived SHA256 values. Prior benchmark/runner: `output/archives/pre_prdbench_sync_20261127-180026/`.
- Detailed local evidence: `.superpowers/prdbench-sync-20261127/integration-evidence/`. No experiments started and no remote push.

### Decisions and practical limits

1. Use an isolated worktree and one independent final review before local integration. This was within the selected scope; changes were not delivered to the requested branch until verified.
2. Keep cleanup conservative for strings, data and ambiguous wrappers. Unrecognized formatting still needs a model repair and can consume the normal repair budget.
3. Retain each completed full-suite run as evidence instead of repeating identical tests through the task bookkeeping helper. Re-run after functional changes; final delivery uses the exact tested code, with a main-checkout dry run after integration.
4. Preserve upstream defect annotations as supplied. This integration does not independently establish their scientific validity; any annotation issue would carry into subsequent experiments.
5. Defer live provider availability and model scoring to the separately requested experiment. Local tests cannot establish real-model success or performance.
6. After review, retain the conservative handling of ambiguous string/tag responses: preserve content and return ordinary feedback, accepting that these cases can require additional repair rounds.
