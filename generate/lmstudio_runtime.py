"""LM Studio inspection/preparation; generation never implicitly loads a model."""
import json
import os
from copy import deepcopy
from pathlib import Path
import subprocess
import signal
from urllib.parse import urlsplit, urlunsplit
from lmstudio_contract import SYSTEM_PROMPT


HERE = Path(__file__).resolve().parent


def _merge_settings(base, overrides):
    """Keep common runtime settings when a model overrides only a nested field."""
    merged = deepcopy(base)
    for key, value in overrides.items():
        merged[key] = (_merge_settings(merged[key], value)
                       if isinstance(merged.get(key), dict) and isinstance(value, dict)
                       else deepcopy(value))
    return merged


def load_profile(model_key):
    data = json.loads((HERE / "lmstudio_profiles.json").read_text())
    model = data["models"][model_key]
    return {**model, "model_key": model_key, "api": data["api"],
            "runtime": _merge_settings(data["runtime"], model.get("runtime", {}))}


def _gpu_setting_matches(field, expected, actual):
    if field in ("ratio", "numCpuExpertLayersRatio"):
        def ratio(value):
            return 1 if value == "max" else 0 if value == "off" else value
        expected, actual = ratio(expected), ratio(actual)
        return (type(expected) in (int, float) and type(actual) in (int, float)
                and 0 <= expected <= 1 and expected == actual)
    return expected == actual


def validate_runtime(profile, state):
    """Fail rather than silently compare models running with different settings."""
    def require(ok, field):
        if not ok:
            raise ValueError(f"LM Studio runtime mismatch: {field}; run prepare_lmstudio.py --check")

    require(state.get("model_key") == profile["model_key"], "model_key")
    require(state.get("quantization") == profile["quantization"], "quantization")
    require(state.get("context_length") in profile["runtime"]["context_candidates"], "context_length")
    actual = state.get("load_config", {})
    for key, value in profile["runtime"]["load_config"].items():
        if key == "gpu":
            gpu = actual.get("gpu", {})
            for field, expected in value.items():
                require(_gpu_setting_matches(field, expected, gpu.get(field)), f"gpu.{field}")
        else:
            require(key in actual and actual[key] == value, key)
    # Native prediction cpuThreads can differ from the startup thread pool.
    # Record both settings without rejecting a different native prediction count.


class Runtime:
    def __init__(self, profile, base_url, identifier):
        self.profile, self.identifier = profile, identifier
        parts = urlsplit(base_url)
        if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
            raise ValueError("LMSTUDIO_API_BASE must be an http(s) URL without embedded credentials")
        self.ws_url = urlunsplit(("wss" if parts.scheme == "https" else "ws", parts.netloc, "", "", ""))

    def _call(self, action, **kwargs):
        request = {"action": action, "identifier": self.identifier,
                   "base_url": self.ws_url, "profile": self.profile, **kwargs}
        # No shell, command-line prompts or credentials. A load can take several minutes.
        with subprocess.Popen(["node", str(HERE / "lmstudio_runtime.mjs")], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                              # Inspect/tokenize belong to the generator's process
                              # group so batch cancellation also stops these helpers.
                              start_new_session=action in ('prepare', 'unload')) as child:
            try:
                stdout, _ = child.communicate(json.dumps(request))
            except BaseException:
                # Give the SDK loader a chance to abort/clean up instead of orphaning a load.
                child.send_signal(signal.SIGTERM)
                try:
                    child.communicate(timeout=20)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.communicate()
                raise
        try:
            response = json.loads(stdout)
        except ValueError as error:
            raise RuntimeError("LM Studio SDK helper failed; check Node.js, LMSTUDIO_SDK_PATH and the server") from error
        if child.returncode or "error" in response:
            raise RuntimeError(response.get("error", "LM Studio SDK helper failed"))
        return response

    def inspect(self):
        return self._call("inspect")

    def count_tokens(self, prompt):
        return self.preflight(prompt)["tokens"]

    def preflight(self, prompt):
        return self._call("count", prompt=prompt, system_prompt=SYSTEM_PROMPT)

    def prepare(self, exclusive=False):
        return self._call("prepare", exclusive=exclusive)

    def unload(self, instance_reference):
        return self._call("unload", instance_reference=instance_reference)


def connection(profile):
    return (os.getenv("LMSTUDIO_API_BASE", "http://127.0.0.1:1234/v1").rstrip("/"),
            os.getenv(profile["identifier_env"], profile["identifier"]))
