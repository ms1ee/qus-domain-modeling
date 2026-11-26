import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {prepare, unloadOwned} from '../generate/lmstudio_runtime.mjs';

const data = JSON.parse(readFileSync(new URL('../generate/lmstudio_profiles.json', import.meta.url)));
const profile = {model_key: 'qwen/qwen3-coder-30b', ...data.models['qwen/qwen3-coder-30b'], runtime: data.runtime};
const request = {identifier: profile.identifier, profile};

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

test('low VRAM unloads only the new model and falls back from 64K to 32K', async () => {
  const owned = [];
  const client = {llm: {listLoaded: async () => [], load: async (key, options) => {
    assert.equal(key, profile.model_key);
    assert.equal(options.config.gpu.numCpuExpertLayersRatio, 1);
    const item = model(options.config.contextLength); owned.push(item); return item;
  }}};
  const state = await prepare(client, request, () => owned.length === 1 ? 400 : 2000);
  assert.equal(state.context_length, 32768);
  assert.equal(owned.length, 2);
  assert.equal(owned[0].unloads, 1);
  assert.equal(owned[1].unloads, 0);
});

test('model load OOM also falls back, but unrelated load errors do not', async () => {
  for (const [message, expectedCalls] of [['out of memory', 2], ['model file not found', 1]]) {
    let calls = 0;
    const client = {llm: {listLoaded: async () => [], load: async () => {calls++; throw Error(message);}}};
    await assert.rejects(prepare(client, request, () => 2000));
    assert.equal(calls, expectedCalls);
  }
});

test('wrong runtime is cleaned up and aborts without a smaller-context retry', async () => {
  let loads = 0;
  const wrong = model(65536, {flashAttention: false});
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
  await assert.rejects(prepare(client, request, () => 200), /cleanup failed/);
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
