import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {prepare, snapshot, unloadOwned} from '../generate/lmstudio_runtime.mjs';

const data = JSON.parse(readFileSync(new URL('../generate/lmstudio_profiles.json', import.meta.url)));
const profile = {model_key: 'qwen/qwen3-coder-30b', ...data.models['qwen/qwen3-coder-30b'], runtime: data.runtime};
const request = {identifier: profile.identifier, profile};
// Exercise generic fallback behavior with an explicit alternative profile;
// the experiment's actual default now requires exactly 32K.
const fallbackRequest = {...request, profile: {...profile, runtime: {
  ...profile.runtime, context_candidates: [65536, 32768]}}};

function model(context = 32768, changes = {}) {
  return {identifier: profile.identifier,
    getModelInfo: async () => ({identifier: profile.identifier, modelKey: profile.model_key,
      instanceReference: 'original-instance',
      quantization: {name: 'Q4_K_M'}, contextLength: context}),
    getLoadConfig: async () => ({...profile.runtime.load_config, contextLength: context, ...changes}),
    getBasePredictionConfig: async () => ({cpuThreads: 7}),
    unloads: 0,
    async unload() {this.unloads++;},
  };
}

test('preparation refuses to touch an unrelated loaded model', async () => {
  const other = {identifier: 'active-experiment'};
  let loads = 0;
  const client = {llm: {listLoaded: async () => [other], load: async () => {loads++;}}};
  await assert.rejects(prepare(client, request, () => 8000), /Another model is loaded/);
  assert.equal(loads, 0);
});

test('an existing matching model is reused without loading or unloading', async () => {
  const existing = model();
  const client = {llm: {listLoaded: async () => [existing], load: async () => assert.fail('must not load')}};
  const state = await prepare(client, request, () => assert.fail('must not reload'));
  assert.equal(state.reused, true);
  assert.equal(existing.unloads, 0);
});

test('a different CPU thread count is observed without rejecting preparation', async () => {
  const existing = model();
  existing.getBasePredictionConfig = async () => ({cpuThreads: 12});
  const client = {llm: {listLoaded: async () => [existing], load: async () => assert.fail('must not reload')}};
  const state = await prepare(client, request, () => assert.fail('must not reload'));
  assert.equal(state.prediction_config.cpuThreads, 12);
  assert.equal(existing.unloads, 0);
});

test('GPU ratio validation compares the configured value, including fractional placement', async () => {
  const cases = [[.9, .9, true], [.9, 1, false], [.9, .8, false],
    ['max', 1, true], [1, 'max', true], ['off', 0, true], [0, 'off', true],
    [1, true, false], [0, false, false], [.9, '0.9', false], [.9, undefined, false]];
  for (const [expected, actual, accepted] of cases) {
    const configured = structuredClone(request);
    configured.profile.runtime.load_config.gpu.numCpuExpertLayersRatio = expected;
    const existing = model(32768, {gpu: {ratio: 'max', numCpuExpertLayersRatio: actual}});
    const client = {llm: {listLoaded: async () => [existing]}};
    if (accepted) await prepare(client, configured, () => 2000);
    else await assert.rejects(prepare(client, configured, () => 2000), /gpu.numCpuExpertLayersRatio/);
    assert.equal(existing.unloads, 0);
  }
});

test('preparation applies CPU threads to the backend startup and records the override', async () => {
  const configured = structuredClone(request);
  configured.profile.runtime.cpu_threads = 12;
  let passed;
  const client = {llm: {listLoaded: async () => [], load: async (key, options) => {
    passed = options.config;
    return model(options.config.contextLength, options.config);
  }}};
  const state = await prepare(client, configured, () => 2000);
  const expected = {enabled: true, disabledParameters: ['--threads'], excludeAllConfig: false,
    overrideParameters: [{key: '--threads', value: '12'}]};
  assert.deepEqual(passed.llamaCppArgumentsOverride, expected);
  assert.deepEqual(state.load_config.llamaCppArgumentsOverride, expected);
  assert.equal(passed.useFp16ForKVCache, true);
  assert.equal(passed.contextLength, 32768);
  assert.equal('llamaCppArgumentsOverride' in configured.profile.runtime.load_config, false);
});

test('runtime snapshots retain numeric thread settings without unrelated argument values', async () => {
  for (const value of ['12', '12 --api-key fixture-only-secret']) {
    const existing = model(32768, {llamaCppArgumentsOverride: {
      enabled: true, excludeAllConfig: false,
      disabledParameters: ['--threads', '--api-key'],
      overrideParameters: [{key: '--threads', value},
        {key: '--api-key', value: 'fixture-only-secret'}],
    }});
    const state = await snapshot(existing);
    assert.doesNotMatch(JSON.stringify(state), /api-key|fixture-only-secret/);
    assert.deepEqual(state.load_config.llamaCppArgumentsOverride, {
      enabled: true, excludeAllConfig: false, disabledParameters: ['--threads'],
      overrideParameters: value === '12' ? [{key: '--threads', value: '12'}] : [],
    });
  }
});

test('low VRAM unloads only the new model and falls back from 64K to 32K', async () => {
  const owned = [];
  const client = {llm: {listLoaded: async () => [], load: async (key, options) => {
    assert.equal(key, profile.model_key);
    assert.equal(options.config.gpu.numCpuExpertLayersRatio, 1);
    const item = model(options.config.contextLength); owned.push(item); return item;
  }}};
  const state = await prepare(client, fallbackRequest, () => owned.length === 1 ? 400 : 2000);
  assert.equal(state.context_length, 32768);
  assert.equal(owned.length, 2);
  assert.equal(owned[0].unloads, 1);
  assert.equal(owned[1].unloads, 0);
});

test('model load OOM also falls back, but unrelated load errors do not', async () => {
  for (const [message, expectedCalls] of [['out of memory', 2], ['model file not found', 1]]) {
    let calls = 0;
    const client = {llm: {listLoaded: async () => [], load: async () => {calls++; throw Error(message);}}};
    await assert.rejects(prepare(client, fallbackRequest, () => 2000));
    assert.equal(calls, expectedCalls);
  }
});

test('wrong runtime is cleaned up and aborts without a smaller-context retry', async () => {
  let loads = 0;
  const wrong = model(32768, {flashAttention: false});
  const client = {llm: {listLoaded: async () => [], load: async () => {loads++; return wrong;}}};
  await assert.rejects(prepare(client, request, () => 2000), /flashAttention/);
  assert.equal(loads, 1);
  assert.equal(wrong.unloads, 1);
});

test('cleanup failure stops fallback', async () => {
  let loads = 0;
  const owned = model(65536);
  owned.unload = async () => {throw Error('cleanup failed');};
  const client = {llm: {listLoaded: async () => [], load: async () => {loads++; return owned;}}};
  await assert.rejects(prepare(client, fallbackRequest, () => 200), /cleanup failed/);
  assert.equal(loads, 1);
});

test('batch preparation refuses even a matching model owned by another run', async () => {
  const existing = model();
  const client = {llm: {listLoaded: async () => [existing]}};
  await assert.rejects(prepare(client, {...request, exclusive: true}, () => 2000), /already loaded/);
  assert.equal(existing.unloads, 0);
});

test('cleanup only unloads the exact instance originally loaded', async () => {
  const existing = model();
  const client = {llm: {listLoaded: async () => [existing]}};
  await assert.rejects(unloadOwned(client, {...request, instance_reference: 'other-instance'}), /instance/);
  assert.equal(existing.unloads, 0);
  await unloadOwned(client, {...request, instance_reference: 'original-instance'});
  assert.equal(existing.unloads, 1);
});

test('interrupted preparation cleans the newly loaded model', async () => {
  const abort = new AbortController();
  const created = model(65536);
  const client = {llm: {listLoaded: async () => [], load: async () => {abort.abort(); return created;}}};
  await assert.rejects(prepare(client, {...request, signal: abort.signal}, () => 2000));
  assert.equal(created.unloads, 1);
});
