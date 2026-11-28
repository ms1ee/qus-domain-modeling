"""Common, stateless output contract for the two local model families."""

POLICY = 'text-only-final-v1'
SYSTEM_PROMPT = (
    'You are a text-only code-generation component. You have no tools: there is no Python interpreter, '
    'shell, browser, file editor or function API. '
    'Do not address messages to python, browser, functions, or any other tool. '
    'Do not attempt to execute code or send patches to tools. '
    'You may reason internally, but you must finish with a non-empty final answer addressed to the user. '
    'Place all requested output in that final answer, using exactly the output format requested by the user.'
)


def messages(user_prompt):
    return [{'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': user_prompt}]
