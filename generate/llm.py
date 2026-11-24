import os
from abc import ABC, abstractmethod
import anthropic
from config import *


class LLM(ABC):
    @abstractmethod
    def chat(self, user_prompt):
        """Single-turn request. Returns (text, usage dict)."""


class Claude(LLM):
    # No refusal fallbacks: the model must not change during the experiment.
    def __init__(self, model_id):
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("Error: ANTHROPIC_API_KEY doesn't exist.")
            exit(1)
        self.client = anthropic.Anthropic()
        self.model_id = model_id

    def chat(self, user_prompt):
        with self.client.messages.stream(
            model=self.model_id,
            max_tokens=MAX_TOKENS,
            output_config={"effort": EFFORT},
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            message = stream.get_final_message()
            req_id = getattr(message, "_request_id", None) or \
                getattr(getattr(stream, "response", None), "headers", {}).get("request-id")
        text = "".join(b.text for b in message.content if b.type == "text")
        u = message.usage
        usage = {
            "model": message.model,
            "stop_reason": message.stop_reason,
            "request_id": req_id,
            "input_tokens": u.input_tokens,
            "output_tokens": u.output_tokens,
            "cache_read_tokens": u.cache_read_input_tokens or 0,
            "cache_write_tokens": u.cache_creation_input_tokens or 0,
        }
        print("  [LLM] stop_reason=%s in=%d out=%d"
              % (usage["stop_reason"], usage["input_tokens"], usage["output_tokens"]))
        if message.stop_reason in ("max_tokens", "refusal"):
            print("  [LLM Warning] stop_reason=%s (incomplete answer)" % message.stop_reason)
        return text, usage


PROVIDERS = {"anthropic": Claude}


def make_llm(model):
    provider, model_id = MODELS[model]
    if provider not in PROVIDERS:
        print("Unsupported provider: %s" % provider)
        exit(1)
    return PROVIDERS[provider](model_id)
