#!/usr/bin/env python3
import os, re, sys, csv, json, time, shlex, shutil, argparse, tempfile, subprocess
from collections import defaultdict

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
BENCHMARK_DIR = os.path.join(ROOT_DIR, "benchmark")
OUTDIR_BASE = os.path.join(ROOT_DIR, "output")

## Plan items not scored as unit tests: task -> {metric id: reason}
EXCLUDED = {
    "37": {"2.3.2": "interactive control (stdin), shell stage",
           "2.3.3": "interactive control (stdin), shell stage"},
}
TIMEOUT = 60  # seconds per item

RUN_DIR = re.compile(r"^(\d+)-(.+)-(direct|modeling)-iter-(\d+)$")
RESULT_NAME = "result.json"


def unit_test_items(task):
    with open(os.path.join(BENCHMARK_DIR, task, "evaluation", "detailed_test_plan.json")) as f:
        plan = json.load(f)
    items = []
    for t in plan:
        metric = t["metric"].split()[0]
        if t["type"] != "unit_test" or metric in EXCLUDED.get(task, {}):
            continue
        items.append((metric, [c["test_command"] for c in t["testcases"]]))
    return items


def short_message(output):
    lines = [l for l in output.splitlines() if l.startswith("E ")]
    return "\n".join((lines or output.splitlines()[-15:])[:10])


def run_item(workspace, test_command):
    args = shlex.split(test_command)
    assert args[0] == "pytest", test_command
    cmd = [sys.executable, "-m", "pytest"] + args[1:] + ["-q", "-p", "no:cacheprovider"]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    start = time.time()
    try:
        p = subprocess.run(cmd, cwd=workspace, env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return "timeout", TIMEOUT, "timeout after %ds" % TIMEOUT
    duration = round(time.time() - start, 2)
    # 0: passed, 1: assertion failed, others (2 interrupted/collection error, 5 no tests): error
    status = {0: "pass", 1: "fail"}.get(p.returncode, "error")
    message = "" if status == "pass" else short_message(p.stdout + p.stderr)
    return status, duration, message


def evaluate_run(run_dir, task, prd, pipeline, nth):
    items = unit_test_items(task)
    result = {"task": task, "prd": prd, "pipeline": pipeline, "iter": nth,
              "items": {}, "excluded": EXCLUDED.get(task, {})}
    src = os.path.join(run_dir, "src")
    with tempfile.TemporaryDirectory(prefix="prdbench-eval-") as workspace:
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(workspace, "src"))
        shutil.copytree(os.path.join(BENCHMARK_DIR, task, "evaluation"),
                        os.path.join(workspace, "evaluation"))
        for metric, commands in items:
            cases = []
            for test_command in commands:
                status, duration, message = run_item(workspace, test_command)
                case = {"node": test_command.split("pytest ", 1)[1], "status": status, "duration": duration}
                if message:
                    case["message"] = message
                cases.append(case)
            # an item passes only if all of its testcases pass
            failed = [c["status"] for c in cases if c["status"] != "pass"]
            result["items"][metric] = {"status": failed[0] if failed else "pass", "cases": cases}
    result["passed"] = sum(v["status"] == "pass" for v in result["items"].values())
    result["total"] = len(items)
    with open(os.path.join(run_dir, RESULT_NAME), "w") as f:
        json.dump(result, f, indent=2)
    return result


def summarize(outdir, results):
    metrics = sorted({m for r in results for m in r["items"]})
    with open(os.path.join(outdir, "summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["task", "prd", "pipeline", "iter", "passed", "total"] + metrics)
        for r in sorted(results, key=lambda r: (r["task"], r["prd"], r["pipeline"], r["iter"])):
            w.writerow([r["task"], r["prd"], r["pipeline"], r["iter"], r["passed"], r["total"]] +
                       [int(r["items"][m]["status"] == "pass") if m in r["items"] else "" for m in metrics])

    groups = defaultdict(list)
    for r in results:
        groups[(r["task"], r["prd"], r["pipeline"])].append(r)
    rate = {k: sum(r["passed"] / r["total"] for r in v) / len(v) for k, v in groups.items()}
    for key in sorted(groups):
        task, prd, pipeline = key
        runs = groups[key]
        line = "%s %s %s: %.1f%% (%d iters)" % (task, prd, pipeline, rate[key] * 100, len(runs))
        base = (task, "vanilla", pipeline)
        if prd != "vanilla" and base in rate:
            line += "  delta vs vanilla: %+.1f%%p" % ((rate[key] - rate[base]) * 100)
        print(line)
        for m in sorted(runs[0]["items"]):
            ok = sum(r["items"][m]["status"] == "pass" for r in runs)
            if ok < len(runs):
                statuses = sorted({r["items"][m]["status"] for r in runs} - {"pass"})
                print("  %-7s %d/%d [%s]" % (m, ok, len(runs), ",".join(statuses)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("outdir", help="output/<model>/<outdir>")
    parser.add_argument("--force", action="store_true", help="re-evaluate runs that have result.json")
    args = parser.parse_args()

    outdir = os.path.join(OUTDIR_BASE, args.model, args.outdir)
    if not os.path.isdir(outdir):
        print("Output directory not found: %s" % outdir)
        exit(1)

    results = []
    for name in sorted(os.listdir(outdir)):
        m = RUN_DIR.match(name)
        run_dir = os.path.join(outdir, name)
        if not m or not os.path.isfile(os.path.join(run_dir, "usage.json")):
            continue
        result_path = os.path.join(run_dir, RESULT_NAME)
        if os.path.isfile(result_path) and not args.force:
            with open(result_path) as f:
                results.append(json.load(f))
            continue
        print("[*] Evaluating %s" % name)
        r = evaluate_run(run_dir, m.group(1), m.group(2), m.group(3), int(m.group(4)))
        print("  passed %d/%d" % (r["passed"], r["total"]))
        results.append(r)

    if not results:
        print("No generated runs in %s" % outdir)
        exit(1)
    print()
    summarize(outdir, results)


if __name__ == "__main__":
    main()
