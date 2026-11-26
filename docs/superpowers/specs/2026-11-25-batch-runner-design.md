# One-command LM Studio experiment

User requests one script to run this repository after the current experiment.
Use the already approved sequence, Qwen3-Coder-30B then gpt-oss-20b; projects
37, 44, 29; vanilla PRD; one iteration. Default direct; optional modeling/both.
Do not start a real experiment during implementation or change model settings.

Approach: a small shell entry point and Python orchestration of the existing
generator/evaluator, sharing the existing SDK preparation helper. A shell-only
runner makes structured status and reliable interruption handling harder. An
agent loop would change this experiment and is outside scope.

Each invocation has a fresh result name. Preserve existing per-model outputs;
add output/batches/<name>/ with console/stage logs, manifest/status and combined
summary. Errors stop the batch; test failures remain evaluation results.
Use unique loaded identifiers, exclusive preparation and exact-instance cleanup.
Only prevent duplicate invocations of this script with a repository-local lock.
User explicitly checks completion of the other experiment and starts this one
manually: no polling, waiting, automatic launch or other-experiment lock access.
Dry-run prints the plan without model calls or filesystem changes.
Scope decisions are routine continuation of the preceding approved manual flow;
no additional design permission is needed. Work on feat/lmstudio-prdbench in place.
