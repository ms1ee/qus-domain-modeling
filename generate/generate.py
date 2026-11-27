#!/usr/bin/env python3
import os, re, sys, json, time, shutil, argparse, subprocess
from pathlib import Path
import signal
from dotenv import load_dotenv
from config import *
from prompt import *
from llm import LMStudio, make_llm, request_completion
from artifacts import snapshot_hashes, write_json, ArtifactIntegrityError, source_digest
from session import create_state
from repair import run_trial, response_complete, finish_trial, evaluation
from context import ContextBudgetError
from experiment import DEFAULT_FEEDBACK_LEVEL, DEFAULT_SEED_BASE, iteration_seed, seed_schedule, validate_feedback_level

load_dotenv(os.path.join(ROOT_DIR, ".env"))

FILE_BLOCK = re.compile(r'<file path="([^"]+)">\n?(.*?)</file>', re.DOTALL)
FENCE = re.compile(r"^```[\w-]*\n(.*?)\n?```\s*$", re.DOTALL)


def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def parse_json(text):
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def extract_files(response):
    files, rejected = {}, []
    for path, content in FILE_BLOCK.findall(response):
        norm = os.path.normpath(path.strip())
        if os.path.isabs(norm) or norm.startswith("..") or not norm.startswith("src" + os.sep):
            rejected.append(path)
            continue
        m = FENCE.match(content.strip())
        files[norm] = m.group(1) + "\n" if m else content
    return files, rejected


def run_once(llm, task, prd, use_modeling, run_dir, *, max_repairs=20, prd_name='vanilla', nth=0,
             feedback_level=DEFAULT_FEEDBACK_LEVEL, seed=None):
    validate_feedback_level(feedback_level)
    if not 0 <= max_repairs <= 30:
        raise ValueError('max_repairs must be between 0 and 30')
    run_dir = Path(run_dir)
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError(f'Trial directory is not empty; use a new run name: {run_dir}')
    if isinstance(llm, LMStudio):
        seed = iteration_seed(DEFAULT_SEED_BASE, nth) if seed is None else iteration_seed(seed, 0)
        llm.set_trial_options(seed=seed, feedback_level=feedback_level)
    elif seed is not None:
        raise ValueError('Explicit seed control is supported only for LM Studio models')
    benchmark = Path(BENCHMARK_DIR) / task
    inputs = snapshot_hashes(benchmark)
    identity = {'task': task, 'prd': prd_name, 'pipeline': 'modeling' if use_modeling else 'direct',
                'iter': nth, 'feedback_level': feedback_level, 'seed': seed,
                'model': getattr(llm, 'model_name', getattr(llm, 'model_id', type(llm).__name__))}
    state = create_state(run_dir, identity, max_repairs=max_repairs, inputs={'benchmark': inputs},
                         settings=getattr(llm, 'settings', {}))
    try:
        evaluation.ensure_test_runner()
        provided = benchmark / 'src'
        if provided.is_dir():
            shutil.copytree(provided, run_dir / 'src')
        else:
            (run_dir / 'src').mkdir()
        domain = ''
        if use_modeling:
            state['phase'] = 'modeling'
            write_json(run_dir / 'run.json', state)
            modeling_prompt = MODELING_PROMPT % prd
            (run_dir / 'modeling-prompt.txt').write_text(modeling_prompt, encoding='utf-8')
            print('  [*] Modeling (once; frozen for all repairs)', flush=True)
            started = time.monotonic()
            try:
                modeling, usage = request_completion(llm, modeling_prompt)
            except BaseException as error:
                if getattr(error, 'request_usage', None) is not None:
                    state['modeling_usage'] = error.request_usage
                    write_json(run_dir / 'modeling-usage.json', error.request_usage)
                raise
            finally:
                state['modeling_seconds'] = time.monotonic() - started
            state['modeling_usage'] = usage
            write_json(run_dir / 'modeling-usage.json', usage)
            (run_dir / 'modeling.txt').write_text(modeling, encoding='utf-8')
            if not response_complete(modeling, usage):
                return finish_trial(run_dir, state, 'modeling_error', error='Empty or incomplete domain model')
            model = parse_json(modeling)
            usage['json_ok'] = model is not None
            domain = json.dumps(model, indent=2) if model is not None else modeling.strip()
            if model is not None:
                write_json(run_dir / 'modeling.json', model)
        if snapshot_hashes(benchmark) != inputs:
            raise ArtifactIntegrityError('Benchmark inputs changed during preparation/modeling')
        api = getattr(llm, 'profile', {}).get('api', {})
        fixed = {'prd': prd, 'interface': BENCHMARKS[task]['interface'], 'domain_model': domain,
                 'provided_files': {'src/' + name: digest for name, digest in snapshot_hashes(provided).items()},
                 'output_reserve_tokens': api.get('output_reserve_tokens', 8192),
                 'template_margin_tokens': api.get('template_margin_tokens', 1024)}
    except BaseException as error:
        status = ('interrupted' if isinstance(error, KeyboardInterrupt) else
                  'integrity_error' if isinstance(error, ArtifactIntegrityError) else
                  'context_limit' if isinstance(error, ContextBudgetError) else
                  'api_error' if state['phase'] == 'modeling' else 'validation_error')
        finish_trial(run_dir, state, status, error=error)
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        return state
    return run_trial(llm, identity=identity, fixed=fixed, run_dir=run_dir, max_repairs=max_repairs, state=state)


def log_gen_info(outdir, args, llm):
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, check=True,
                                capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError:
        commit = "none"
    with open(os.path.join(outdir, "gen.config"), "a") as f:
        f.write("Model: %s %s\n" % (args.model, MODELS[args.model][1]))
        if MODELS[args.model][0] == "lmstudio":
            f.write("LM Studio settings: %s\n" % json.dumps(llm.settings, sort_keys=True))
        else:
            f.write("Effort: %s, Max tokens: %d\n" % (EFFORT, MAX_TOKENS))
        f.write("Task: %s, PRD: %s, Pipeline: %s, Iterations: %d\n"
                % (args.task, args.prd, "modeling" if args.modeling else "direct", args.iters))
        f.write("Start Time: %d\n" % int(time.time()))
        f.write("Max repairs after initial generation: %d\n" % getattr(args, 'max_repairs', 20))
        f.write("Feedback level: %d\n" % getattr(args, 'feedback_level', DEFAULT_FEEDBACK_LEVEL))
        if isinstance(llm, LMStudio):
            base = getattr(args, 'seed_base', None)
            f.write("Seed schedule by independent iteration: %s\n" %
                    seed_schedule(DEFAULT_SEED_BASE if base is None else base, args.iters))
        f.write("Commit Hash: %s\n\n" % commit)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model", choices=list(MODELS))
    parser.add_argument("task", choices=list(BENCHMARKS))
    parser.add_argument("prd", help="vanilla or <type>_defect (benchmark/<task>/<prd>_PRD.md)")
    parser.add_argument("iters", type=int)
    parser.add_argument("outdir", help="output/<model>/<outdir>")
    parser.add_argument("--modeling", action="store_true", help="PRD -> Modeling -> Code")
    parser.add_argument('--max-repairs', type=int, default=20, help='Repair requests after initial generation (default: 20)')
    parser.add_argument('--feedback-level', type=int, choices=(1, 2, 3), default=DEFAULT_FEEDBACK_LEVEL,
                        help='1: score (default); 2: score and item outcomes; 3: detailed failures; all include level-filtered repair history')
    parser.add_argument('--seed-base', type=int,
                        help='LM Studio only: repetition i uses base+i (default: 42)')
    args = parser.parse_args()
    if not 0 <= args.max_repairs <= 30 or args.iters < 1:
        parser.error('--max-repairs must be between 0 and 30 and iters must be positive')
    local = MODELS[args.model][0] == 'lmstudio'
    if not local and args.seed_base is not None:
        parser.error('--seed-base is supported only for LM Studio models')
    try:
        seeds = seed_schedule(DEFAULT_SEED_BASE if args.seed_base is None else args.seed_base, args.iters) if local else [None] * args.iters
    except ValueError as error:
        parser.error(str(error))
    def interrupt(signum, frame):
        raise KeyboardInterrupt
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, interrupt)

    prd_path = os.path.join(BENCHMARK_DIR, args.task, "%s_PRD.md" % args.prd)
    if not os.path.isfile(prd_path):
        print("PRD not found: %s" % prd_path)
        exit(1)
    with open(prd_path, encoding="utf-8") as f:
        prd = f.read()

    outdir = os.path.join(OUTDIR_BASE, args.model, args.outdir)
    pipeline = "modeling" if args.modeling else "direct"
    pending = []
    # Check every existing trial before starting any missing trial or appending
    # settings. A rejected condition must leave the recorded experiment intact.
    for i in range(args.iters):
        run_dir = os.path.join(outdir, "%s-%s-%s-iter-%d" % (args.task, args.prd, pipeline, i))
        state_path = Path(run_dir) / 'run.json'
        if state_path.exists():
            previous = json.loads(state_path.read_text())
            if (previous['status'] in ('passed', 'repair_limit')
                    and previous['max_repairs'] == args.max_repairs
                    and previous['identity'].get('feedback_level') == args.feedback_level
                    and previous['identity'].get('seed') == seeds[i]
                    and evaluation.managed_result(run_dir)['status'] == previous['status']):
                print('[*] Skip %s (%s)' % (run_dir, previous['status']))
                continue
            raise RuntimeError('Existing trial is incomplete or differs from this request; use a new outdir: ' + run_dir)
        if Path(run_dir).exists() and any(Path(run_dir).iterdir()):
            raise RuntimeError('Existing trial is incomplete; use a new outdir: ' + run_dir)
        pending.append((i, run_dir))

    if pending:
        llm = make_llm(args.model)
        if isinstance(llm, LMStudio):
            llm.set_trial_options(seed=seeds[pending[0][0]], feedback_level=args.feedback_level)
        os.makedirs(outdir, exist_ok=True)
        log_gen_info(outdir, args, llm)

    for i, run_dir in pending:
        print("[*] Generating %s" % run_dir)
        state = run_once(llm, args.task, prd, args.modeling, run_dir, max_repairs=args.max_repairs,
                         prd_name=args.prd, nth=i, feedback_level=args.feedback_level, seed=seeds[i])
        if state['status'] not in ('passed', 'repair_limit'):
            raise SystemExit(1)

    print("All generations done!")


if __name__ == "__main__":
    main()
