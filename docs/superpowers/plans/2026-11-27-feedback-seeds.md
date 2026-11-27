# Feedback levels and repeated trials Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox syntax to track completion.

**Goal:** Add three feedback conditions, paired varying repetition seeds, 32K contexts and medium gpt-oss reasoning.

**Architecture:** Project full validation into a level-specific prompt, retain full evidence, and propagate selected conditions through generator/batch/summary. Configure the request seed once per independent trial. No new agent framework.

**Tech Stack:** Python, pytest, existing Node/HTTP/SDK fixtures.

**Spec:** `docs/superpowers/specs/2026-11-27-feedback-seeds-design.md`

## Global Constraints

- No experiments, model loads, native LM Studio changes, remote push, benchmark edits, or old-result edits.
- Default feedback 3, seed base 42, default iters 1. Use --iters 3 or 5 to repeat.
- Both contexts 32768, gpt-oss medium; retain every other runtime/sampling rule and 30-repair budget.

## Review Focus

- Level 1/2 must not leak hidden test details via repair history, metadata or overflow fallback.
- Same trial's domain/code/repair/retry requests must share a seed; later seeds must not mutate earlier usage records.
- Invalid options/seed overflow fail before model preparation, including dry runs and direct generator use.
- Existing trials cannot be reused under different feedback/seed conditions; legacy records are not falsely relabeled.
- All actual requests and summaries must carry the intended conditions, not just the displayed plan.

### Task 1: Feedback projection and complete evidence

**Files:** `generate/context.py`, `generate/repair.py`, `generate/generate.py`, new `generate/experiment.py`, `tests/test_context.py`, `tests/test_feedback.py`.
**Interfaces:** validate_feedback_level(level); build_prompt/fit_prompt(..., feedback_level=3); run_once(..., feedback_level=3). Trial identity carries feedback_level. Context records history_mode/error_chars/feedback_level.

- [x] Add RED tests for literal level projections, no history/detail leakage, preserved common format feedback, overflow behavior, real repair logs and unchanged scoring.
- [x] Implement filtering before prompt assembly, shared validation and repair-loop propagation. Keep default level 3 behavior.
- [x] Run affected tests and full pytest, inspect outcomes, commit.

### Task 2: Repetition seeds, model settings and CLI integration

**Files:** `generate/experiment.py`, `generate/llm.py`, `generate/lmstudio_profiles.json`, `generate/generate.py`, `generate/run_batch.py`, `eval/evaluate.py`, tests and README files.
**Interfaces:** iteration_seed(base, index), seed_schedule(base,count); LMStudio.set_trial_options(seed=..., feedback_level=...); run_once(..., seed=None). --seed-base, --feedback-level propagated by batch; identity includes actual seed; SUMMARY_FIELDS includes seed/feedback_level.

- [x] Add RED real HTTP/batch tests for both models, repeated direct/modeling trials, repair/retry stability, settings snapshots, summary grouping and mismatched reuse rejection. Update fixture runtime expectations to the new requested settings.
- [x] Implement validated scheduling, provider-specific seed setup, fresh sampling snapshots and model profile changes. Add CLI flags, early validation, manifest and summary fields, skip guards.
- [x] Update usage docs with three feedback conditions, 3/5 repetitions, explicit seed base, 32K context and medium reasoning. Explain same seed within repairs and actual feedback truncation.
- [x] Run full pytest and no-model dry runs; commit.

### Task 3: Review and delivery

- [x] One fresh read-only reviewer checks the entire branch; reproduce and fix material findings, then full verification.
- [x] Verify benchmark/old outputs unchanged; fast-forward the requested branch to the verified commits; remove the clean temporary worktree. Do not push or start an experiment.


## Verification record

- Task 1: 15 feature tests failed before implementation; 209 regression tests passed afterward.
- Task 2: 9 feature tests failed before implementation; 226 regression tests passed afterward.
- Final review: accepted all 3 Important findings and 1 Minor finding. Ten failing regression cases reproduced them; targeted verification then passed 57 tests. Fixed reserved random seed rejection, complete request-condition metadata, read-only conflict/skip preflight, and context-budget guidance.
- Final full suite: **231 passed in 127.93s**, including local HTTP/SDK fixtures and the Node runtime contract tests. No real model inference was used.
- Dry runs confirmed default five-repeat seeds 42,43,44,45,46 and custom-base repetition schedules. Benchmark is unchanged from 238134e; all 4,212 archived output hashes still match.
- Real model output quality and strict output reproducibility were not measured in this implementation task.

Delivered by fast-forward to `feat/lmstudio-prdbench` through e31c217. The temporary worktree/branch was removed after preserving local verification logs in `.superpowers/feedback-seeds-20261127/`. Main-checkout dry run passed; no experiment or push was performed.
