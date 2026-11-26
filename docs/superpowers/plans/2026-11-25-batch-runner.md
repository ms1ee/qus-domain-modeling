# LM Studio Batch Runner Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline; one final fresh review.

**Goal:** One command executes and evaluates both local models on the three projects.
**Architecture:** Shell entry, Python subprocess orchestration, existing SDK lifecycle.
**Tech Stack:** Python stdlib, Bash, existing LM Studio SDK and installed dependencies.
**Spec:** ../specs/2026-11-25-batch-runner-design.md

## Global Constraints
- Preserve profiles, PRDs, prompts, code generation and scoring semantics.
- Remain on the user's current branch/path; preserve existing uncommitted changes.
- Do not run inference, unload models, or alter the active Minimal-CodeAgent job.
- Defaults: Qwen then gpt-oss; 37,44,29; direct; vanilla; one iteration.

## Review Focus
- Another instance of this script or unrelated model must never be unloaded/reused.
- Failure and interruption must stop child processes and only clean up owned models.
- Results/logs must describe partial failure accurately and never overwrite a prior batch.
- Shell entry must work from other directories and preserve failing exit status.
- Dry-run must have no side effects, both pipelines must be distinguishable in outputs.

### Task 1: lifecycle and batch execution
- [x] Write failing tests for exclusive preparation/owned cleanup, execution order,
  modeling flags, lock contention, failure/interruption and dry-run.
- [x] Add run_lmstudio.sh and generate/run_batch.py; extend runtime helper with
  exclusive preparation and owned-instance unloading only.
- [x] Verify targeted tests and whole suite.

### Task 2: documentation and review
- [x] Document one-command use, tmux, options, logs and failure behavior.
- [x] Review changes once; fix material findings with regression tests.
- [x] Verify shell syntax, dry-run, full tests; no interaction with the existing experiment.

## Progress / rulings
- Baseline: 26 existing harness tests passed during previous connection work.
- User clarification: remove other-experiment lock integration. User decides when
  to launch; keep only .lmstudio-batch.lock for duplicate invocations of this script.
- No source/evaluator changes beyond batch orchestration/lifecycle are planned.
- Final: 39 pytest tests passed in 38.80s, including real generator/evaluator
  subprocesses through HTTP/SDK doubles and cancellation regression cases.
- CLI --help/--dry-run work from another directory; shell/Node syntax and diff
  whitespace checks pass. No real model inference/load/unload was performed.
