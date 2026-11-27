# PRDBench updates and LM Studio integration

User-approved scope (2026-11-27): incorporate the complete current `origin/prdbench`, implement automatic cleanup of the documented output tags, add PRD selection to the local batch, and verify without starting experiments. Preserve existing results and local recovery fixes. No further feature choice is required.

## Approach

Preserve the pre-update benchmark/runner and current fixes, then integrate in a separate worktree and fast-forward `feat/lmstudio-prdbench` after verification. Replacing the local runner with upstream's one-shot generator would lose repairs and provenance; selectively dropping upstream tests/interfaces would not satisfy the requested full integration. Combine the upstream data/contracts and Claude changes with the existing state-based runner.

## Required behavior

- Integrate upstream `df23b1c` (or a newer head fetched before implementation), including all defect data, corrected project 29 tests, reduced interfaces, Claude Sonnet registration, and Claude prompt caching.
- Preserve LM Studio model profiles, resource settings, provider identity, bounded API retries, native-output-error recovery, per-project reload and 0–30 repair budget. No inference requests or experiments during this work.
- Original response and token statistics remain unchanged. Normalize complete code responses before atomic publication and evaluation; never normalize incomplete/native protocol-error responses.
- Only documented syntax cleanup: remove standalone `</parameter>` / `</invoke>` lines from Python code outside strings; recover an unclosed file block only when the same path is reopened and the replacement is complete. Do not repair algorithms, arbitrary tags, different nested paths, closed duplicate file blocks, protected input updates or unsafe paths. Ambiguous/literal cases remain unchanged and follow existing feedback handling.
- Save changed normalized responses and per-file cleanup counts/replacement details in each round's `tag_cleanup.json` / `tag_cleanup.txt`. Keep raw `response.txt` / `codegen_response.txt`. A cleaned response still consumes its original request round; no hidden model calls. Existing source hashes and validation must refer to the actually published cleaned code.
- Add `--prd` selecting exactly one of `vanilla`, `unambiguous_defect`, `complete_defect`, `consistent_defect`; default `vanilla`. Persist selection in manifest, generation identity and output names. Missing selected PRDs fail before loading any model or starting a batch. No automatic all-variants expansion.
- Claude caching is provider-specific: one-hour ephemeral text-block caching for modeling input and direct code requests; disabled for code generated through the modeling pipeline. Never send Anthropic cache fields to LM Studio or break its single-prompt API.
- Document new benchmark/version comparability and the distinction between automatic managed-run cleanup and legacy manual cleanup. Old outputs stay byte-identical; use the archived prior benchmark/runner to inspect or reproduce old evaluations.

## Verification

Tests cover repaired syntax actually passing the evaluator, intact raw responses and usage, safe non-normalization of literals/unsafe markers, finite repair budgets, real batch selection through HTTP/SDK fixtures, and Claude payload differences. Run the full repository suite, review the integrated branch, and verify preserved output hashes. Do not launch a model experiment or push remotely.
