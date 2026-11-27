# LM Studio hardware tuning implementation plan

> Execute inline with superpowers:executing-plans. User explicitly authorized measurement, applying faster stable settings, README update and push; no further approval gate.

Goal: compare F16-cache CPU expert placement and 8/10/12/20 CPU threads for the two installed models; apply only measured stable improvements.

Constraints: preserve 32768 context, sampling, gpt-oss medium, fixed seed, quantization, flash attention, experiment defaults and all old results. Do not start the full PRDBench batch. Own and clean up only measurement model instances. Serialize GPU use and refuse an already loaded model. Keep a VRAM safety margin. Preserve native model configuration backups and restore it after screening.

- [ ] Task 1: Measure baseline and CPU expert ratios 1.0/0.9/0.8 at 10 threads with the same prompt and bounded output length. Record actual load settings, prompt/generation timing and sampled peak VRAM. On viable placements compare 8/10/12/20 threads. Repeat baseline and best candidates on a second, longer representative input. Rejected memory configurations are failures, not speed results.
- [ ] Task 2: Add tests for explicit fractional GPU validation and independent per-model runtime configuration; implement minimal profile merging and exact validation. Apply selected runtime profiles and native CPU settings only after confirming them.
- [ ] Task 3: Run regression checks and real production-API smoke checks, publish measurement scope/limits and selected settings in README; one independent final code review, then integrate into feat/lmstudio-prdbench and push.

Review focus: configured versus effective CPU/GPU settings; no sampling or precision changes; fresh-context timings and short-run bias; headroom during generation rather than load alone; safe model/config cleanup after interruption.
