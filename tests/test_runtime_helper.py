from pathlib import Path
import subprocess
import json
import os

from conftest import snapshot


def test_node_preparation_contract():
    result = subprocess.run(['node', '--test', str(Path(__file__).with_name('lmstudio_runtime.test.mjs'))],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_sdk_authentication_and_preflight_use_specific_loaded_instance(tmp_path):
    from lmstudio_runtime import load_profile
    state = snapshot()
    state['load_config']['contextLength'] = state['context_length']
    # External SDK test double enforces authentication and prohibits dynamic handles.
    sdk = tmp_path / 'sdk.mjs'
    sdk.write_text('''
export class LMStudioClient {
  constructor(options) {
    if (options.apiToken !== process.env.LMSTUDIO_API_KEY) throw Error('SDK authentication missing');
    const state = JSON.parse(process.env.FIXTURE_STATE);
    const model = {
      identifier: state.identifier,
      getModelInfo: async () => ({identifier: state.identifier, modelKey: state.model_key,
        quantization: {name: state.quantization}, contextLength: state.context_length}),
      getLoadConfig: async () => state.load_config,
      getBasePredictionConfig: async () => state.prediction_config,
      applyPromptTemplate: async (chat) => chat.messages[0].content[0].text,
      countTokens: async (text) => text === 'preserve input' ? 123 : -1
    };
    this.llm = {listLoaded: async () => [model], createDynamicHandle: () => {throw Error('use specific handle');}};
  }
}
''')
    request = {'action': 'count', 'base_url': 'ws://127.0.0.1:1234',
               'identifier': state['identifier'], 'profile': load_profile(state['model_key']),
               'prompt': 'preserve input'}
    env = {**os.environ, 'LMSTUDIO_API_KEY': 'fixture-only-secret',
           'LMSTUDIO_SDK_PATH': str(sdk), 'FIXTURE_STATE': json.dumps(state)}
    helper = Path(__file__).parents[1] / 'generate/lmstudio_runtime.mjs'
    result = subprocess.run(['node', str(helper)], input=json.dumps(request), env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'fixture-only-secret' not in result.stdout + result.stderr
    value = json.loads(result.stdout)
    assert value['tokens'] == 123
    assert value['runtime']['context_length'] == 32768
    assert value['runtime']['identifier'] == state['identifier']
