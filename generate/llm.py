import os
import time
from abc import ABC, abstractmethod
from config import *
from context import ContextBudgetError
from model_output import (OUTPUT_FEEDBACK, api_error_details, capture_server_logs,
                          classify_parser_error, completion_status)


class LLM(ABC):
    @abstractmethod
    def chat(self, user_prompt):
        """Single-turn request. Returns (text, usage dict)."""


class Claude(LLM):
    # No refusal fallbacks: the model must not change during the experiment.
    def __init__(self, model_id):
        import anthropic

        if not os.getenv("ANTHROPIC_API_KEY"):
            print("Error: ANTHROPIC_API_KEY doesn't exist.")
            exit(1)
        self.client = anthropic.Anthropic()
        self.model_id = model_id

    def chat(self, user_prompt, cache=True):
        # cache: prompt repeats across iterations (1h TTL: an iteration can take over 5 min)
        block = {"type": "text", "text": user_prompt}
        if cache:
            block["cache_control"] = {"type": "ephemeral", "ttl": "1h"}
        with self.client.messages.stream(
            model=self.model_id,
            max_tokens=MAX_TOKENS,
            output_config={"effort": EFFORT},
            messages=[{"role": "user", "content": [block]}],
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
        print("  [LLM] stop_reason=%s in=%d cache_w=%d cache_r=%d out=%d"
              % (usage["stop_reason"], usage["input_tokens"], usage["cache_write_tokens"],
                 usage["cache_read_tokens"], usage["output_tokens"]))
        if message.stop_reason in ("max_tokens", "refusal"):
            print("  [LLM Warning] stop_reason=%s (incomplete answer)" % message.stop_reason)
        return text, usage


class LMStudio(LLM):
    def __init__(self, model_id):
        import httpx
        import openai
        import lmstudio_runtime

        self.profile = lmstudio_runtime.load_profile(model_id)
        base_url, self.model_id = lmstudio_runtime.connection(self.profile)
        self.base_url = base_url
        self.runtime = lmstudio_runtime.Runtime(self.profile, base_url, self.model_id)
        self._refresh_runtime()
        api = self.profile['api']
        self.client = openai.OpenAI(
            base_url=base_url, api_key=os.getenv('LMSTUDIO_API_KEY', 'lm-studio'),
            max_retries=0, timeout=httpx.Timeout(api['response_timeout_seconds'],
                                               connect=api['connect_timeout_seconds']))

    def _refresh_runtime(self):
        self._record_runtime(self.runtime.inspect())

    def _record_runtime(self, state):
        from lmstudio_runtime import validate_runtime

        validate_runtime(self.profile, state)
        if state['identifier'] != self.model_id:
            raise ValueError('LM Studio runtime mismatch: identifier')
        self.settings = {'sampling': self.profile['sampling'], 'api': self.profile['api'], 'runtime': state}

    def chat(self, user_prompt):
        import openai

        api = self.profile['api']
        sampling = dict(self.profile['sampling'])
        request = dict(model=self.model_id, messages=[{'role': 'user', 'content': user_prompt}],
                       max_tokens=api['max_tokens'], temperature=sampling.pop('temperature'),
                       top_p=sampling.pop('top_p'), seed=sampling.pop('seed'), extra_body=sampling)
        http_attempts = 0
        input_tokens = budget = None
        def failed_usage():
            return {
                'model': self.model_id, 'http_attempts': http_attempts,
                'retries': max(0, http_attempts - 1), 'response_complete': False,
                'input_tokens': None, 'output_tokens': None, 'reasoning_tokens': None,
                'cache_read_tokens': None, 'rendered_input_tokens': input_tokens,
                'input_budget_tokens': budget, 'settings': self.settings,
            }
        try:
            for attempt in range(api['max_retries'] + 1):
                # Revalidate before every HTTP attempt, including after retry backoff.
                preflight = self.runtime.preflight(user_prompt)
                self._record_runtime(preflight['runtime'])
                input_tokens = preflight['tokens']
                context = self.settings['runtime']['context_length']
                budget = context - api['output_reserve_tokens'] - api['template_margin_tokens']
                if input_tokens > budget:
                    raise ContextBudgetError(f'Input needs {input_tokens} tokens; context input budget is {budget}/{context}. '
                                     'PRD/domain model was not truncated. Prepare a larger context before retrying.')
                try:
                    log_cursor = capture_server_logs(self.base_url)
                    http_attempts += 1
                    message = self.client.chat.completions.create(**request)
                    break
                except (openai.APIConnectionError, openai.APIStatusError) as error:
                    details = classify_parser_error(error, log_cursor, self.model_id)
                    if details is not None:
                        usage = failed_usage()
                        usage.update(response_status='protocol_error', stop_reason='protocol_error',
                                     api_error=details,
                                     response_feedback='LM Studio could not parse the last model output. ' + OUTPUT_FEEDBACK)
                        print('  [LLM Warning] Model output protocol error; next request uses the repair budget', flush=True)
                        return '', usage
                    status = getattr(error, 'status_code', None)
                    retryable = status is None or status in (408, 409, 429) or status >= 500
                    if not retryable or attempt == api['max_retries']:
                        raise
                    print(f'  [LLM] Transient API failure; retry {attempt + 1}/{api["max_retries"]}')
                    time.sleep(2 ** attempt)
            if not message.choices:
                raise RuntimeError('LM Studio returned no completion choices')
        except BaseException as error:
            # Known transport counts survive failures; server token usage is unknown.
            error.request_usage = failed_usage()
            if isinstance(error, (openai.APIConnectionError, openai.APIStatusError)):
                error.request_usage['api_error'] = api_error_details(error)
            raise
        choice = message.choices[0]
        # Reasoning is not program output. Never concatenate reasoning_content.
        text = choice.message.content or ''
        u = message.usage
        usage = {
            'model': message.model, 'request_id': getattr(message, '_request_id', None),
            'stop_reason': 'max_tokens' if choice.finish_reason == 'length' else choice.finish_reason,
            'finish_reason': choice.finish_reason,
            **completion_status(choice, text),
            'input_tokens': getattr(u, 'prompt_tokens', None),
            'output_tokens': getattr(u, 'completion_tokens', None),
            'cache_read_tokens': getattr(getattr(u, 'prompt_tokens_details', None), 'cached_tokens', None),
            'cache_write_tokens': None,  # Not supplied by the OpenAI-compatible response.
            'reasoning_tokens': getattr(getattr(u, 'completion_tokens_details', None), 'reasoning_tokens', None),
            'retries': attempt, 'http_attempts': http_attempts, 'rendered_input_tokens': input_tokens,
            'input_budget_tokens': budget, 'settings': self.settings,
        }
        print('  [LLM] stop_reason=%s in=%s out=%s' %
              (usage['stop_reason'], usage['input_tokens'], usage['output_tokens']))
        if not usage['response_complete']:
            print(f'  [LLM Warning] {usage["response_status"]}; no code applied from this response')
        return text, usage


PROVIDERS = {"anthropic": Claude, "lmstudio": LMStudio}


def request_completion(llm, prompt, *, cache=True):
    """Keep Anthropic cache directives out of local/OpenAI-compatible requests."""
    if isinstance(llm, Claude):
        return llm.chat(prompt, cache=cache)
    return llm.chat(prompt)


def make_llm(model):
    provider, model_id = MODELS[model]
    if provider not in PROVIDERS:
        print("Unsupported provider: %s" % provider)
        exit(1)
    instance = PROVIDERS[provider](model_id)
    instance.model_name = model
    return instance
