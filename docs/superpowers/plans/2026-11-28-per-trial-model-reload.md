# Per-trial model reload implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this task with tests first.

**Goal:** Reload the LM Studio model for every independent repetition in the batch.

**Architecture:** The batch owns one runtime per `(model, project, pipeline, iteration)`.
It invokes the generator for one selected iteration, then unloads that exact instance
in `finally`. The generator retains the original iteration index and seed schedule.

**Tech Stack:** Python, LM Studio SDK helper, pytest, tmux.

**Spec:** User request on 2026-11-28: check repetition-level initialization; implement it,
update README, push the current branch, and restart in tmux. The follow-up request
selects `./run_lmstudio.sh --feedback-level 1` for the new experiment.

## Global constraints

- Default models/projects/pipelines/iterations, sampling, context, seeds, feedback, and repair budget stay unchanged.
- Each independent trial gets a fresh identifier and loaded instance; modeling and repairs within that trial share it.
- Trained weights are reloaded; no training, server restart, or OS cache purge is introduced.
- Preserve old results and stop the previous batch gracefully before restarting.
- Manual `generate.py` remains usable against a caller-managed model.

## Review focus

- Selected iteration must preserve both its output directory index and seed `base + index`.
- Both pipelines must load separately, even for the same project/seed.
- Failure or cancellation during any trial must unload the owned instance and stop later work.
- Runtime and command logs must not overwrite earlier trials' records.
- Same-trial domain generation, repair and transport retry must keep the same instance and seed.

## Task 1: Isolate each independent batch trial

**Files:** `generate/run_batch.py`, `generate/generate.py`, `tests/test_batch.py`,
`tests/test_repetition.py`, `README_LMSTUDIO.md`, `README.md`.

**Interfaces:** `generate.py --iteration-index N` selects one zero-based index from
the positional iteration count without renumbering it. Batch runtime snapshots and logs
include project, pipeline and iteration. Manifest policy is `per_trial`.

- [x] Extend batch lifecycle/seed tests; add selected-iteration validation and same-trial repair checks.
- [x] Run the new expectations against the old code and confirm they fail for the missing reload/index behavior.
- [x] Implement the selector and move runtime ownership inside the pipeline/iteration loops.
- [x] Update README scope, execution flow, metadata examples and manual-run caveat.
- [x] Run focused tests, full pytest, Node helper tests and dry-run; expect all to pass with unchanged 36-trial plan.
- [ ] Review the diff, resolve findings, commit, fast-forward the current branch and push.
- [ ] Start the requested command in tmux and verify its manifest/runtime/first request.
