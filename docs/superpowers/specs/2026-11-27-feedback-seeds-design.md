# Feedback levels and repeated local-model trials

Approved by the user: implement the preceding three-level feedback proposal; set both models to 32,768 context tokens (explicit follow-up answer); gpt-oss reasoning medium; use a different seed for each independent repetition. Do not start experiments or push.

## Behavior

- `--feedback-level {1,2,3}`, default 3, in batch and generator. Level 1 shows only passed/total scored metrics; level 2 additionally shows every metric's pass/fail (all non-pass outcomes become fail); level 3 retains existing detailed feedback and repair history. Levels 1/2 never show detailed history. Unknown validation is explicitly unmeasured.
- PRD/interface/frozen domain/current code and output-format/protocol feedback follow common rules. Full raw evaluation evidence is still saved at every level. Only the prompt projection changes; tests and scoring do not.
- Keep existing context fitting at level 3, record selected level, effective history mode, error excerpt budget and omissions. At levels 1/2, intentional hiding is distinct from budget-driven omission. Test-code exposure remains pytest log excerpts, not extra file extraction.
- `--seed-base N`, local-model default 42, yields seed N+i for zero-based independent repetition i. Modeling, initial code, repairs and transient retries within that trial use the same seed. Model/project/pipeline/feedback choices do not shift the schedule. `--iters 5` yields 42,43,44,45,46 by default. Nonnegative 32-bit seeds; reject a schedule that overflows before model loading.
- Seed control applies to LM Studio. Do not send unsupported seed parameters to Claude; explicitly requesting a seed there is an error. Existing Claude usage remains supported.
- Both context candidate lists become [32768], gpt-oss reasoning_effort becomes medium. Preserve other sampling/runtime/API settings. Do not change the live LM Studio server or model files.
- Record feedback level and effective seed in trial identity, usage settings, batch manifest and summary. Reject reuse of a trial with different feedback/seed conditions; distinguish summary groups by feedback level. Historical records without these fields remain readable as unknown, not relabeled.

## Approach

Extend the existing context projection rather than redact raw logs. Put shared option validation and deterministic seed scheduling in a small `experiment.py` module. Configure LMStudio's seed before each independent trial with per-request copies of effective settings; never mutate previous usage records. Keep one feedback level per batch and use new run names for separate conditions.

## Validation

Use current context/real repair evaluator and local HTTP/SDK fixture tests. Assert no detail leakage at levels 1/2 including history; full saved evidence; consistent seeds across repairs/modeling and both models; no seed leakage into later trial metadata; early argument rejection; correct 32K runtime checks; separate summary grouping and resume guards. Existing result files and benchmark stay unchanged. Final independent read-only review and full regression suite before delivery to feat/lmstudio-prdbench.
