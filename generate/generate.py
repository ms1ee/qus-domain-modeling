#!/usr/bin/env python3
import os, re, sys, json, time, shutil, argparse, subprocess
from dotenv import load_dotenv
from config import *
from prompt import *
from llm import make_llm

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


def run_once(llm, task, prd, use_modeling, run_dir):
    usage = {}
    modeling_section = ""
    if use_modeling:
        modeling_prompt = MODELING_PROMPT % prd
        print("  [*] Modeling")
        modeling, usage["modeling"] = llm.chat(modeling_prompt)
        write_file(os.path.join(run_dir, "modeling.txt"), modeling)
        model = parse_json(modeling)
        usage["modeling"]["json_ok"] = model is not None
        if model is None:
            # keep the run: pass the raw answer as is and flag it
            print("  [Warning] Domain model is not valid JSON; passing raw text")
            modeling_section = MODELING_SECTION % modeling.strip()
        else:
            write_file(os.path.join(run_dir, "modeling.json"), json.dumps(model, indent=2))
            modeling_section = MODELING_SECTION % json.dumps(model, indent=2)

    codegen_prompt = CODEGEN_PROMPT % (prd, modeling_section, BENCHMARKS[task]["interface"])
    print("  [*] Code generation")
    # modeling: the domain model differs per iteration, so the prompt never repeats
    response, usage["codegen"] = llm.chat(codegen_prompt, cache=not use_modeling)
    write_file(os.path.join(run_dir, "codegen_response.txt"), response)

    files, rejected = extract_files(response)
    for path, content in files.items():
        write_file(os.path.join(run_dir, path), content)
    # provided files (benchmark/<task>/src/, e.g. data) overwrite any generated copy
    provided = os.path.join(BENCHMARK_DIR, task, "src")
    if os.path.isdir(provided):
        shutil.copytree(provided, os.path.join(run_dir, "src"), dirs_exist_ok=True)
    usage["files"] = sorted(files)
    usage["rejected_paths"] = rejected
    print("  [*] Wrote %d file(s) under src/%s"
          % (len(files), ", rejected %s" % rejected if rejected else ""))
    # usage.json marks a finished run
    write_file(os.path.join(run_dir, "usage.json"), json.dumps(usage, indent=2))


def log_gen_info(outdir, args):
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, check=True,
                                capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError:
        commit = "none"
    with open(os.path.join(outdir, "gen.config"), "a") as f:
        f.write("Model: %s %s\n" % (args.model, MODELS[args.model][1]))
        f.write("Effort: %s, Max tokens: %d\n" % (EFFORT, MAX_TOKENS))
        f.write("Task: %s, PRD: %s, Pipeline: %s, Iterations: %d\n"
                % (args.task, args.prd, "modeling" if args.modeling else "direct", args.iters))
        f.write("Start Time: %d\n" % int(time.time()))
        f.write("Commit Hash: %s\n\n" % commit)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model", choices=list(MODELS))
    parser.add_argument("task", choices=list(BENCHMARKS))
    parser.add_argument("prd", help="vanilla or <type>_defect (benchmark/<task>/<prd>_PRD.md)")
    parser.add_argument("iters", type=int)
    parser.add_argument("outdir", help="output/<model>/<outdir>")
    parser.add_argument("--modeling", action="store_true", help="PRD -> Modeling -> Code")
    args = parser.parse_args()

    prd_path = os.path.join(BENCHMARK_DIR, args.task, "%s_PRD.md" % args.prd)
    if not os.path.isfile(prd_path):
        print("PRD not found: %s" % prd_path)
        exit(1)
    with open(prd_path, encoding="utf-8") as f:
        prd = f.read()

    llm = make_llm(args.model)
    outdir = os.path.join(OUTDIR_BASE, args.model, args.outdir)
    os.makedirs(outdir, exist_ok=True)
    log_gen_info(outdir, args)

    pipeline = "modeling" if args.modeling else "direct"
    for i in range(args.iters):
        run_dir = os.path.join(outdir, "%s-%s-%s-iter-%d" % (args.task, args.prd, pipeline, i))
        if os.path.isfile(os.path.join(run_dir, "usage.json")):
            print("[*] Skip %s (done)" % run_dir)
            continue
        print("[*] Generating %s" % run_dir)
        run_once(llm, args.task, prd, args.modeling, run_dir)

    print("All generations done!")


if __name__ == "__main__":
    main()
