# PRDBench integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

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

- [ ] Preserve output hashes, previous benchmark/runner and current recovery edits; verify the baseline suite and create an isolated worktree.
- [ ] Write failing tests for real Claude payload caching on direct/modeling stages; retain real generator/evaluator with only SDK boundary doubled. Run targeted pytest and observe failures.
- [ ] Merge all upstream commits, keeping the managed generation loop. Resolve README and generator conflicts; apply cache controls through the provider-aware helper.
- [ ] Run provider/generation tests and full pytest; commit the integrated upstream merge.

### Task 2: Automatically normalize documented tags with provenance

**Files:** create `generate/tag_cleanup.py`, `tests/test_tag_cleanup.py`; modify `generate/repair.py`, `generate/session.py`, and related docs.

**Interfaces:** `normalize_response(response: str) -> tuple[str, dict]` returns normalized text and deterministic per-file audit metadata. The repair loop saves raw/cleaned artifacts and applies its existing parsing/protected-path/atomic-publication checks.

- [ ] Write RED tests: literal expectations for standalone tag removal, same-path reopening, string/data preservation and rejected mixed/unsafe operations. Add real repair/evaluation tests for retained raw response, passing cleaned code, unchanged usage and budget, rejected cleanup preserving prior code.
- [ ] Run targeted pytest and inspect expected failures.
- [ ] Implement conservative normalization, per-round cleanup artifacts, and record policy metadata. Never execute response-suggested tools or alter logical program statements.
- [ ] Run affected tests and full pytest; commit automatic cleanup.

### Task 3: Select PRD variants through the local batch

**Files:** `generate/run_batch.py`, `tests/test_batch.py`, `README.md`, `README_LMSTUDIO.md`, `eval/README.md`.

**Interfaces:** `--prd NAME` populates `plan['prd']`, child generation argv, manifest and existing trial identity/output directory. Default and model/project ordering remain unchanged.

- [ ] Write RED real-entry tests selecting each defect variant with distinct PRD contents, checking saved identity and correct input; invalid/missing input must produce no SDK events or output batch. Existing default tests continue covering vanilla.
- [ ] Run tests, then implement selection/preflight and document examples, cleanup evidence and old-result versioning.
- [ ] Run full pytest and selected dry runs; commit.

### Task 4: Review and deliver on the requested branch

**Files:** final documentation and verification record; no experiment artifacts are edited.

- [ ] Review the entire change with a fresh read-only reviewer per requesting-code-review. Fix material findings with reproducing tests.
- [ ] Verify upstream is an ancestor, sampling/runtime profiles unchanged, all regression tests pass, no experiment running and all pre-existing output hashes match the archive manifest.
- [ ] Fast-forward `feat/lmstudio-prdbench` to the verified integration branch and remove the clean temporary worktree. Leave original results and archive available; do not push or start experiments.
