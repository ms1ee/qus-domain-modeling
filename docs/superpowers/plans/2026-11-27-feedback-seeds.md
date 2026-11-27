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

- [ ] Add RED tests for literal level projections, no history/detail leakage, preserved common format feedback, overflow behavior, real repair logs and unchanged scoring.
- [ ] Implement filtering before prompt assembly, shared validation and repair-loop propagation. Keep default level 3 behavior.
- [ ] Run affected tests and full pytest, inspect outcomes, commit.

### Task 2: Repetition seeds, model settings and CLI integration

**Files:** `generate/experiment.py`, `generate/llm.py`, `generate/lmstudio_profiles.json`, `generate/generate.py`, `generate/run_batch.py`, `eval/evaluate.py`, tests and README files.
**Interfaces:** iteration_seed(base, index), seed_schedule(base,count); LMStudio.set_seed(seed); run_once(..., seed=None). --seed-base, --feedback-level propagated by batch; identity includes actual seed; SUMMARY_FIELDS includes seed/feedback_level.

- [ ] Add RED real HTTP/batch tests for both models, repeated direct/modeling trials, repair/retry stability, settings snapshots, summary grouping and mismatched reuse rejection. Update fixture runtime expectations to the new requested settings.
- [ ] Implement validated scheduling, provider-specific seed setup, fresh sampling snapshots and model profile changes. Add CLI flags, early validation, manifest and summary fields, skip guards.
- [ ] Update usage docs with three feedback conditions, 3/5 repetitions, explicit seed base, 32K context and medium reasoning. Explain same seed within repairs and actual feedback truncation.
- [ ] Run full pytest and no-model dry runs; commit.

### Task 3: Review and delivery

- [ ] One fresh read-only reviewer checks the entire branch; reproduce and fix material findings, then full verification.
- [ ] Verify benchmark/old outputs unchanged; fast-forward the requested branch to the verified commits; remove the clean temporary worktree. Do not push or start an experiment.
