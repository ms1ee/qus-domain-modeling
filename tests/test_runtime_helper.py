from pathlib import Path
import subprocess
import json

from conftest import snapshot


def test_node_preparation_contract():
    result = subprocess.run(['node', '--test', str(Path(__file__).with_name('lmstudio_runtime.test.mjs'))],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_sdk_authentication_and_preflight_use_specific_loaded_instance(tmp_path, monkeypatch, capsys):
    from lmstudio_runtime import Runtime, load_profile
    from lmstudio_contract import messages
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
      applyPromptTemplate: async (chat) => {
        if (chat.messages.length !== 2 || chat.messages[0].role !== 'system' ||
            chat.messages[0].content[0].text !== process.env.EXPECTED_CONTRACT ||
            chat.messages[1].role !== 'user') throw Error('System contract missing from token count');
        return chat.messages[1].content[0].text;
      },
      countTokens: async (text) => text === 'preserve input' ? 123 : -1
    };
    this.llm = {listLoaded: async () => [model], createDynamicHandle: () => {throw Error('use specific handle');}};
  }
}
''')
    for key, value in {'LMSTUDIO_API_KEY': 'fixture-only-secret', 'LMSTUDIO_SDK_PATH': str(sdk),
                       'FIXTURE_STATE': json.dumps(state),
                       'EXPECTED_CONTRACT': messages('preserve input')[0]['content']}.items():
        monkeypatch.setenv(key, value)
    runtime = Runtime(load_profile(state['model_key']), 'http://127.0.0.1:1234/v1', state['identifier'])
    value = runtime.preflight('preserve input')
    captured = capsys.readouterr()
    assert 'fixture-only-secret' not in captured.out + captured.err + json.dumps(value)
    assert value['tokens'] == 123
    assert value['runtime']['context_length'] == 32768
    assert value['runtime']['identifier'] == state['identifier']
