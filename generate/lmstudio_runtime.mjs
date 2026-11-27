// Use only public SDK configuration. Never serialize a handle (it contains credentials).
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {homedir} from 'node:os';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';

function threadArgumentsSnapshot(config) {
  // A manually loaded model may have unrelated arguments containing credentials.
  // Persist only numeric --threads values, never arbitrary custom argument text.
  const parameters = Array.isArray(config.overrideParameters) ? config.overrideParameters : [];
  const threads = parameters.filter(item => item?.key === '--threads' &&
    typeof item.value === 'string' && /^\d+$/.test(item.value) &&
    Number.isSafeInteger(Number(item.value)) && Number(item.value) > 0);
  return {enabled: config.enabled === true, excludeAllConfig: config.excludeAllConfig === true,
    disabledParameters: Array.isArray(config.disabledParameters) &&
      config.disabledParameters.includes('--threads') ? ['--threads'] : [],
    overrideParameters: threads.map(item => ({key: '--threads', value: String(Number(item.value))}))};
}

export async function snapshot(model) {
  const info = await model.getModelInfo();
  const load = await model.getLoadConfig();
  const prediction = await model.getBasePredictionConfig();
  const fields = ['contextLength', 'gpu', 'maxParallelPredictions', 'flashAttention',
    'offloadKVCacheToGpu', 'useFp16ForKVCache', 'llamaKCacheQuantizationType',
    'llamaVCacheQuantizationType', 'evalBatchSize', 'physicalBatchSize',
    'keepModelInMemory', 'tryMmap', 'gpuStrictVramCap'];
  const loadConfig = Object.fromEntries(fields.filter(k => k in load).map(k => [k, load[k]]));
  if (load.llamaCppArgumentsOverride) {
    loadConfig.llamaCppArgumentsOverride = threadArgumentsSnapshot(load.llamaCppArgumentsOverride);
  }
  return {identifier: info.identifier, instance_reference: info.instanceReference, model_key: info.modelKey,
    quantization: info.quantization?.name, context_length: info.contextLength,
    load_config: loadConfig,
    prediction_config: {cpuThreads: prediction.cpuThreads}};
}

function gpuSettingMatches(field, expected, actual) {
  if (['ratio', 'numCpuExpertLayersRatio'].includes(field)) {
    const ratio = value => value === 'max' ? 1 : value === 'off' ? 0 : value;
    expected = ratio(expected); actual = ratio(actual);
    return typeof expected === 'number' && typeof actual === 'number' &&
      expected >= 0 && expected <= 1 && expected === actual;
  }
  return JSON.stringify(expected) === JSON.stringify(actual);
}

function validate(profile, state, identifier) {
  const expected = profile.runtime;
  const require = (ok, field) => {if (!ok) throw new Error(`LM Studio runtime mismatch: ${field}`);};
  require(state.identifier === identifier, 'identifier');
  require(state.model_key === profile.model_key, 'model_key');
  require(state.quantization === profile.quantization, 'quantization');
  require(expected.context_candidates.includes(state.context_length), 'context_length');
  for (const [key, value] of Object.entries(expected.load_config)) {
    if (key === 'gpu') {
      for (const [field, configured] of Object.entries(value)) {
        require(gpuSettingMatches(field, configured, state.load_config.gpu?.[field]), `gpu.${field}`);
      }
    } else require(state.load_config[key] === value, key);
  }
  // Native prediction cpuThreads and the startup thread pool are recorded separately.
  // Do not reject a different native prediction count.
}

export async function prepare(client, request, freeVram) {
  const {profile, identifier} = request;
  const loaded = await client.llm.listLoaded();
  if (loaded.length) {
    if (request.exclusive) throw new Error('A model is already loaded; refusing to use or unload another experiment\'s model');
    const same = loaded.find(m => m.identifier === identifier);
    if (!same) throw new Error('Another model is loaded; refusing to unload or replace it. Use --check or wait for the existing experiment.');
    const state = await snapshot(same);
    validate(profile, state, identifier);
    return {...state, reused: true};
  }
  const attempts = [];
  for (const contextLength of profile.runtime.context_candidates) {
    let owned;
    try {
      request.signal?.throwIfAborted();
      // Recheck at each attempt; never unload a model this helper did not load.
      if ((await client.llm.listLoaded()).length) throw new Error('Another model was loaded during preparation');
      // llama-server fixes its thread pool at startup. Prediction cpuThreads alone
      // did not change that pool on the tested backend; replace only --threads.
      const config = {...profile.runtime.load_config, contextLength,
        llamaCppArgumentsOverride: {enabled: true, disabledParameters: ['--threads'],
          excludeAllConfig: false,
          overrideParameters: [{key: '--threads', value: String(profile.runtime.cpu_threads)}]}};
      owned = await client.llm.load(profile.model_key, {identifier, deviceIdentifier: null,
        config, signal: request.signal, verbose: false});
      request.signal?.throwIfAborted();
      const state = await snapshot(owned);
      validate(profile, state, identifier);
      if (state.context_length !== contextLength) throw new Error('Requested context was not applied');
      const free = freeVram();
      if (!Number.isFinite(free)) throw new Error('Cannot inspect free GPU memory');
      if (free < profile.runtime.min_free_vram_mib) {
        const error = new Error(`Only ${free} MiB free GPU memory after loading`);
        error.memoryFailure = true;
        throw error;
      }
      request.signal?.throwIfAborted();
      return {...state, free_vram_mib: free, attempts, reused: false};
    } catch (error) {
      if (owned) await owned.unload(); // Cleanup failure aborts; do not try another load.
      const memoryFailure = error.memoryFailure || /out of memory|failed to allocate|insufficient memory|memory resources/i.test(error.message);
      attempts.push({context_length: contextLength, error: error.message});
      if (!memoryFailure) throw error;
    }
  }
  throw new Error(`No context fits the memory budget: ${JSON.stringify(attempts)}`);
}

export async function unloadOwned(client, request) {
  const model = (await client.llm.listLoaded()).find(m => m.identifier === request.identifier);
  if (!model) return {status: 'already_unloaded'};
  const info = await model.getModelInfo();
  if (!request.instance_reference || info.instanceReference !== request.instance_reference ||
      info.modelKey !== request.profile.model_key) {
    throw new Error('Refusing to unload a different model instance');
  }
  await model.unload();
  // Public SDK unload is identifier-based, not an atomic instance-reference RPC.
  // Batch identifiers therefore include a fresh nonce and must not be manually reused.
  return {status: 'unloaded', identifier: request.identifier};
}

async function main() {
  const request = JSON.parse(readFileSync(0, 'utf8'));
  const sdk = process.env.LMSTUDIO_SDK_PATH || resolve(homedir(),
    '.lmstudio/extensions/plugins/lmstudio/rag-v1/node_modules/@lmstudio/sdk/dist/index.mjs');
  const {LMStudioClient} = await import(pathToFileURL(sdk).href);
  const client = new LMStudioClient({baseUrl: request.base_url,
    ...(process.env.LMSTUDIO_API_KEY ? {apiToken: process.env.LMSTUDIO_API_KEY} : {})});
  if (request.action === 'prepare') {
    const abort = new AbortController();
    const interrupted = () => abort.abort(new Error('Interrupted during model preparation'));
    process.once('SIGINT', interrupted);
    process.once('SIGTERM', interrupted);
    try {
      return await prepare(client, {...request, signal: abort.signal}, () => Number(execFileSync('nvidia-smi',
        ['--query-gpu=memory.free', '--format=csv,noheader,nounits', '--id=0'], {encoding: 'utf8'}).trim()));
    } finally {
      process.removeListener('SIGINT', interrupted);
      process.removeListener('SIGTERM', interrupted);
    }
  }
  if (request.action === 'unload') return unloadOwned(client, request);
  // A specific instance keeps inspection and tokenization on the same loaded model.
  // A dynamic identifier could resolve a replacement instance between SDK calls.
  const model = (await client.llm.listLoaded()).find(m => m.identifier === request.identifier);
  if (!model) throw new Error(`Model ${request.identifier} is not loaded; run prepare_lmstudio.py first`);
  const state = await snapshot(model);
  validate(request.profile, state, request.identifier);
  if (request.action === 'inspect') return state;
  if (request.action === 'count') {
    const rendered = await model.applyPromptTemplate({messages: [
      {role: 'user', content: [{type: 'text', text: request.prompt}]}]});
    return {tokens: await model.countTokens(rendered), runtime: state};
  }
  throw new Error(`Unknown action: ${request.action}`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().then(value => {process.stdout.write(JSON.stringify(value)); process.exit(0);})
    .catch(error => {process.stdout.write(JSON.stringify({error: error.message})); process.exit(1);});
}
