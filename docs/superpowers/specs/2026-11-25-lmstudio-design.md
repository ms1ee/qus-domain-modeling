# LM Studio connection

User-approved scope: create a new branch from prdbench and connect Qwen3-Coder-30B
and gpt-oss-20b, preserving the settings of the existing local experiment.

Use the existing `chat(prompt) -> (text, usage)` boundary. Keep direct/modeling,
PRDs, interface prompts, benchmark tests and evaluation behavior unchanged.
The OpenAI-compatible provider sends the same sampling parameters and separates
final content from reasoning. Claude remains available through a lazy import.

Profiles copied from the running experiment's manifest:
- Qwen: Q4_K_M; temperature .7, top_p .8, top_k 20, repeat_penalty 1.05,
  min_p 0, seed 42, no reasoning_effort.
- GPT-OSS: MXFP4; temperature 1, top_p 1, top_k 0, repeat_penalty 1,
  min_p 0, seed 42, reasoning_effort high.
- Runtime: CPU experts/GPU attention, GPU KV cache, F16 KV, flash attention,
  parallelism 1, context auto 65536 then 32768 on memory/headroom failure;
  keep 768 MiB VRAM headroom. Preserve current native CPU threads=7.
- API: explicit unbounded response timeout with connect=10s; 5 transient
  retries at 1/2/4/8/16s; no SDK double retries. Local max_tokens=-1,
  preflight rendered input against actual loaded context with 8192 output
  reserve and 1024 template margin. Never truncate the PRD or domain model.

Approach: add a provider plus a small explicit model-preparation command. This
avoids implicit JIT loading with different defaults and preserves the existing
single-response experiment. Importing the other repository's agent loop would
change the experiment and is outside the approved connection work.

Model preparation refuses to unload/replace any existing model. Default aliases
belong to this repository; explicit identifier environment variables allow reuse.
The active Minimal-CodeAgent experiment must remain running and unchanged.

Evidence: record actual runtime, sampling, token usage, finish reason and retry
count. No API keys in logs. Verify with local HTTP fixtures and read-only live
SDK inspection; do not send inference to the busy model or load GPT-OSS during
the existing experiment.
